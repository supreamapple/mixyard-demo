import json
import os
import threading
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from followups.providers import test_mode
from followups.signature import signature_matches
from mixyard_app.db import Database
from mixyard_app.pages import missing_page, quote_page, unsub_page
from mixyard_app.service import (
    apply_patch,
    bootstrap,
    followups_view,
    job_messages,
    on_inbound_sms,
    on_missed_call,
    public_base,
    quote_json,
    record_tap,
    run_once,
    shop_reply,
    sync_yard,
    thread_for,
)

ROOT = Path(__file__).resolve().parents[1]
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/followups.js": ("followups.js", "text/javascript; charset=utf-8"),
    "/sample-contacts.csv": ("sample-contacts.csv", "text/csv; charset=utf-8"),
    "/sample-receipt-pts.txt": ("sample-receipt-pts.txt", "text/plain; charset=utf-8"),
}


def request_base(handler) -> str:
    configured = public_base()
    if configured:
        return configured
    host = handler.headers.get("Host") or "127.0.0.1"
    proto = "https" if handler.headers.get("X-Forwarded-Proto") == "https" else "http"
    return proto + "://" + host


class Handler(BaseHTTPRequestHandler):
    server_version = "MixYard"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def _route(self, method: str):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if method == "GET" and path in STATIC:
                self._static(path)
                return
            if method == "GET" and path == "/api/health":
                self._json(200, {"ok": True})
                return
            if method == "GET" and path == "/api/bootstrap":
                self._json(200, bootstrap(self.server.db, request_base(self)))
                return
            if method == "GET" and path == "/api/followups":
                self._json(200, followups_view(self.server.db, request_base(self)))
                return
            if method == "PUT" and path == "/api/followups":
                patch = self._read_json()
                current = self.server.db.settings()
                self.server.db.save_settings(apply_patch(current, patch))
                self._json(200, followups_view(self.server.db, request_base(self)))
                return
            if method == "POST" and path == "/api/followups/run":
                sent = run_once(self.server.db, base_url=request_base(self))
                self._json(200, {"sent": sent})
                return
            if method == "POST" and path == "/api/followups/tapped":
                body = self._read_json()
                row = record_tap(
                    self.server.db,
                    body.get("nudge") or "",
                    body.get("quote_id") or "",
                    body.get("job_id") or "",
                    datetime.now(timezone.utc),
                    request_base(self),
                )
                if row is None:
                    self._json(403, {"error": "That text is off."})
                    return
                self._json(200, {"ok": True})
                return
            if method == "GET" and path == "/api/quotes":
                base = request_base(self)
                self._json(200, {"quotes": [quote_json(self.server.db, quote, base) for quote in self.server.db.quotes()]})
                return
            if method == "POST" and path == "/api/quotes":
                self._create_quote()
                return
            if method == "POST" and path.startswith("/api/quotes/") and path.endswith("/send"):
                quote_id = path[len("/api/quotes/") : -len("/send")].strip("/")
                quote = self.server.db.mark_sent(quote_id, datetime.now(timezone.utc))
                if quote is None:
                    self._json(404, {"error": "No quote."})
                    return
                self._json(200, quote_json(self.server.db, quote, request_base(self)))
                return
            if method == "POST" and path == "/api/jobs/sync":
                sync_yard(self.server.db, self._read_json(), datetime.now(timezone.utc))
                self._json(200, {"ok": True})
                return
            if method == "GET" and path.startswith("/api/jobs/") and path.endswith("/messages"):
                job_id = path[len("/api/jobs/") : -len("/messages")].strip("/")
                if self.server.db.job(job_id) is None:
                    self._json(404, {"error": "No ticket."})
                    return
                self._json(200, {"messages": job_messages(self.server.db, job_id)})
                return
            if method == "GET" and path.startswith("/api/contacts/") and path.endswith("/thread"):
                party_id = path[len("/api/contacts/") : -len("/thread")].strip("/")
                payload = thread_for(self.server.db, party_id)
                if not payload:
                    self._json(404, {"error": "No customer."})
                    return
                self._json(200, payload)
                return
            if method == "POST" and path.startswith("/api/contacts/") and path.endswith("/reply"):
                party_id = path[len("/api/contacts/") : -len("/reply")].strip("/")
                result = shop_reply(self.server.db, party_id, (self._read_json() or {}).get("text") or "", datetime.now(timezone.utc))
                code = result.pop("status", 200)
                self._json(code, result)
                return
            if method == "POST" and path == "/api/sms/inbound":
                self._inbound("sms")
                return
            if method == "POST" and path == "/api/voice/missed":
                self._inbound("voice")
                return
            if method == "POST" and path == "/api/reset":
                self.server.db.reset()
                self._json(200, {"ok": True})
                return
            if path.startswith("/q/"):
                self._quote_link(method, path[3:], query)
                return
            if method == "GET" and path.startswith("/u/"):
                party = self.server.db.party_by_unsub(path[3:])
                if party is None:
                    self._html(404, missing_page())
                    return
                self.server.db.set_email_opt_out(party.id, True)
                self._html(200, unsub_page(self.server.db.settings().shop_name))
                return
            self._json(404, {"error": "Not found."})
        except Exception:
            traceback.print_exc()
            self._json(500, {"error": "Something went wrong."})

    def _create_quote(self):
        body = self._read_json()
        party = self.server.db.party(body.get("contact_id") or "")
        if party is None:
            self._json(400, {"error": "Pick a customer."})
            return
        try:
            quantity = float(body.get("quantity") or 0)
            amount = float(body.get("amount") or 0)
        except (TypeError, ValueError):
            self._json(400, {"error": "Quantity needs to be a number."})
            return
        if quantity <= 0:
            self._json(400, {"error": "Add the yards."})
            return
        quote = self.server.db.add_quote(
            party.id,
            quantity,
            str(body.get("detail") or "")[:40],
            str(body.get("address") or "")[:200],
            int(round(amount * 100)),
        )
        self._json(200, quote_json(self.server.db, quote, request_base(self)))

    def _quote_link(self, method: str, token: str, query: dict):
        quote = self.server.db.quote_by_token(token)
        if quote is None:
            self._html(404, missing_page())
            return
        preview = (query.get("preview") or ["0"])[0] == "1"
        now = datetime.now(timezone.utc)
        if method == "GET" and not preview:
            quote = self.server.db.mark_viewed(quote.id, now)
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            form = parse_qs(raw)
            name = (form.get("name") or [""])[0].strip()
            if quote.status == "open" and not name:
                party = self.server.db.party(quote.party_id)
                self._html(400, quote_page(quote, party, self.server.db.settings().shop_name, "Add your name to sign."))
                return
            if quote.status == "open":
                quote = self.server.db.mark_signed(quote.id, name, now)
        party = self.server.db.party(quote.party_id)
        self._html(200, quote_page(quote, party, self.server.db.settings().shop_name))

    def _inbound(self, kind: str):
        if not test_mode():
            self._json(403, {"error": "Texting is in test mode only."})
            return
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type == "application/json":
            if self.headers.get("X-Mixyard-Test") != "1":
                self._json(403, {"error": "Test calls need the test header."})
                return
            payload = self._read_json()
            phone = payload.get("from") or payload.get("From") or ""
            if kind == "sms":
                result = on_inbound_sms(self.server.db, phone, payload.get("body") or payload.get("Body") or "", datetime.now(timezone.utc))
            else:
                result = on_missed_call(self.server.db, phone, datetime.now(timezone.utc), request_base(self))
            code = 400 if result.get("error") else 200
            self._json(code, result)
            return
        form = self._read_form()
        token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        if token:
            url = request_base(self) + self.path
            offered = self.headers.get("X-Twilio-Signature") or ""
            if not signature_matches(token, url, form, offered):
                self._json(403, {"error": "Signature was not accepted."})
                return
        elif self.headers.get("X-Mixyard-Test") != "1":
            self._json(403, {"error": "Test calls need the test header."})
            return
        phone = form.get("From") or form.get("from") or ""
        if kind == "sms":
            result = on_inbound_sms(self.server.db, phone, form.get("Body") or "", datetime.now(timezone.utc))
        else:
            result = on_missed_call(self.server.db, phone, datetime.now(timezone.utc), request_base(self))
        code = 400 if result.get("error") else 200
        self._json(code, result)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("expected an object")
        return data

    def _read_form(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        parsed = parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def _static(self, path: str):
        name, content_type = STATIC[path]
        file_path = ROOT / name
        if not file_path.is_file():
            self._json(404, {"error": "Not found."})
            return
        payload = file_path.read_bytes()
        self._bytes(200, payload, content_type)

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self._bytes(code, body, "application/json; charset=utf-8")

    def _html(self, code: int, html: str):
        self._bytes(code, html.encode("utf-8"), "text/html; charset=utf-8")

    def _bytes(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def start_scheduler(db: Database, stop: threading.Event | None = None) -> threading.Event:
    flag = stop or threading.Event()
    interval = max(30, int(os.environ.get("FOLLOWUP_INTERVAL_SECONDS", "180") or "180"))

    def loop():
        while not flag.wait(interval):
            try:
                run_once(db)
            except Exception:
                traceback.print_exc()

    threading.Thread(target=loop, name="followups", daemon=True).start()
    return flag


def make_server(db: Database, host: str = "127.0.0.1", port: int = 0, scheduler: bool = False):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.db = db
    if scheduler:
        httpd.followup_stop = start_scheduler(db)
    return httpd


def main():
    path = os.environ.get("MIXYARD_DB", "data/mixyard.db")
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    db = Database(path)
    port = int(os.environ.get("PORT", "8080"))
    httpd = make_server(db, host="0.0.0.0", port=port, scheduler=True)
    httpd.serve_forever()
