import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone

from followups.catalog import default_settings
from followups.inbound import normalize_phone
from followups.models import Job, Party, Quote, ShopSettings
from followups.wording import concrete_wording
from mixyard_app.seed import SHOP, seed_world

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parties (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL DEFAULT '',
  email_opt_out INTEGER NOT NULL DEFAULT 0,
  sms_opt_out INTEGER NOT NULL DEFAULT 0,
  do_not_contact INTEGER NOT NULL DEFAULT 0,
  unsub_token TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quotes (
  id TEXT PRIMARY KEY,
  party_id TEXT NOT NULL,
  quantity REAL NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  address TEXT NOT NULL DEFAULT '',
  amount_cents INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  sent_at TEXT,
  viewed_at TEXT,
  signed_at TEXT,
  token TEXT NOT NULL UNIQUE,
  signer_name TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  party_id TEXT NOT NULL,
  ticket_no TEXT NOT NULL,
  quantity REAL NOT NULL,
  address TEXT NOT NULL DEFAULT '',
  scheduled_at TEXT NOT NULL,
  status TEXT NOT NULL,
  completed_at TEXT,
  notes TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'yard'
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  nudge_key TEXT NOT NULL,
  channel TEXT NOT NULL,
  direction TEXT NOT NULL,
  subject_key TEXT NOT NULL DEFAULT '',
  party_id TEXT NOT NULL,
  quote_id TEXT NOT NULL DEFAULT '',
  job_id TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calls (
  id TEXT PRIMARY KEY,
  party_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT ''
);
"""


def dump_dt(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def load_dt(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def new_id(prefix: str) -> str:
    return prefix + "_" + secrets.token_hex(4)


class Database:
    def __init__(self, path: str, now=None):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        if self._conn.execute("SELECT 1 FROM settings WHERE id = 1").fetchone() is None:
            self.seed(now or datetime.now(timezone.utc))

    def close(self):
        with self._lock:
            self._conn.close()

    def seed(self, now: datetime):
        world = seed_world(now)
        with self._lock:
            self._write_settings(world["settings"])
            for party in world["parties"]:
                self._conn.execute(
                    """INSERT INTO parties
                    (id, name, email, phone, email_opt_out, sms_opt_out, do_not_contact, unsub_token)
                    VALUES (:id, :name, :email, :phone, :email_opt_out, :sms_opt_out, :do_not_contact, :unsub_token)""",
                    party,
                )
            for quote in world["quotes"]:
                self._insert_quote(quote)
            for job in world["jobs"]:
                self._insert_job(job)
            self._conn.commit()

    def reset(self, now=None):
        with self._lock:
            for table in ("messages", "calls", "quotes", "jobs", "parties", "settings"):
                self._conn.execute(f"DELETE FROM {table}")
            self._conn.commit()
        self.seed(now or datetime.now(timezone.utc))

    def _write_settings(self, settings: ShopSettings):
        payload = json.dumps(
            {
                "switches": settings.switches,
                "messages": settings.messages,
                "google_review_url": settings.google_review_url,
                "forward_to": settings.forward_to,
                "shop_name": settings.shop_name,
            }
        )
        self._conn.execute(
            "INSERT INTO settings (id, json) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET json = excluded.json",
            (payload,),
        )

    def _insert_quote(self, quote: dict):
        row = dict(quote)
        row["sent_at"] = dump_dt(row["sent_at"])
        row["viewed_at"] = dump_dt(row["viewed_at"])
        row["signed_at"] = dump_dt(row["signed_at"])
        self._conn.execute(
            """INSERT INTO quotes
            (id, party_id, quantity, detail, address, amount_cents, status, sent_at, viewed_at, signed_at, token, signer_name)
            VALUES (:id, :party_id, :quantity, :detail, :address, :amount_cents, :status, :sent_at, :viewed_at, :signed_at, :token, :signer_name)""",
            row,
        )

    def _insert_job(self, job: dict):
        row = dict(job)
        row["scheduled_at"] = dump_dt(row["scheduled_at"])
        row["completed_at"] = dump_dt(row["completed_at"])
        self._conn.execute(
            """INSERT INTO jobs
            (id, party_id, ticket_no, quantity, address, scheduled_at, status, completed_at, notes, source)
            VALUES (:id, :party_id, :ticket_no, :quantity, :address, :scheduled_at, :status, :completed_at, :notes, :source)""",
            row,
        )

    def settings(self) -> ShopSettings:
        wording = concrete_wording()
        base = default_settings(wording, SHOP)
        with self._lock:
            row = self._conn.execute("SELECT json FROM settings WHERE id = 1").fetchone()
        saved = json.loads(row["json"]) if row else {}
        switches = dict(base.switches)
        switches.update({key: bool(value) for key, value in (saved.get("switches") or {}).items() if key in switches})
        messages = dict(base.messages)
        for key, value in (saved.get("messages") or {}).items():
            if key in messages and isinstance(value, str):
                messages[key] = value
        return ShopSettings(
            switches=switches,
            messages=messages,
            google_review_url=saved.get("google_review_url") or "",
            forward_to=saved.get("forward_to") or "",
            shop_name=(saved.get("shop_name") or SHOP),
        )

    def save_settings(self, settings: ShopSettings):
        with self._lock:
            self._write_settings(settings)
            self._conn.commit()

    def _party(self, row) -> Party:
        return Party(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            email_opt_out=bool(row["email_opt_out"]),
            sms_opt_out=bool(row["sms_opt_out"]),
            do_not_contact=bool(row["do_not_contact"]),
            unsub_token=row["unsub_token"],
        )

    def _quote(self, row) -> Quote:
        return Quote(
            id=row["id"],
            party_id=row["party_id"],
            quantity=row["quantity"],
            detail=row["detail"],
            address=row["address"],
            amount_cents=row["amount_cents"],
            status=row["status"],
            sent_at=load_dt(row["sent_at"]),
            viewed_at=load_dt(row["viewed_at"]),
            signed_at=load_dt(row["signed_at"]),
            token=row["token"],
            signer_name=row["signer_name"],
        )

    def _job(self, row) -> Job:
        return Job(
            id=row["id"],
            party_id=row["party_id"],
            ticket_no=row["ticket_no"],
            quantity=row["quantity"],
            address=row["address"],
            scheduled_at=load_dt(row["scheduled_at"]),
            status=row["status"],
            completed_at=load_dt(row["completed_at"]),
            notes=row["notes"],
            source=row["source"],
        )

    def parties(self) -> list:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM parties ORDER BY name").fetchall()
        return [self._party(row) for row in rows]

    def party(self, party_id: str):
        with self._lock:
            row = self._conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone()
        return self._party(row) if row else None

    def party_by_unsub(self, token: str):
        with self._lock:
            row = self._conn.execute("SELECT * FROM parties WHERE unsub_token = ?", (token,)).fetchone()
        return self._party(row) if row else None

    def party_by_phone(self, phone: str):
        target = normalize_phone(phone)
        if not target:
            return None
        for party in self.parties():
            if normalize_phone(party.phone) == target:
                return party
        return None

    def quotes(self) -> list:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM quotes ORDER BY COALESCE(sent_at, id) DESC").fetchall()
        return [self._quote(row) for row in rows]

    def quote(self, quote_id: str):
        with self._lock:
            row = self._conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
        return self._quote(row) if row else None

    def quote_by_token(self, token: str):
        with self._lock:
            row = self._conn.execute("SELECT * FROM quotes WHERE token = ?", (token,)).fetchone()
        return self._quote(row) if row else None

    def jobs(self) -> list:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM jobs ORDER BY scheduled_at").fetchall()
        return [self._job(row) for row in rows]

    def job(self, job_id: str):
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job(row) if row else None

    def create_party(self, name: str, phone: str, email: str = "") -> Party:
        party_id = new_id("ct")
        token = secrets.token_urlsafe(12)
        with self._lock:
            self._conn.execute(
                """INSERT INTO parties
                (id, name, email, phone, email_opt_out, sms_opt_out, do_not_contact, unsub_token)
                VALUES (?, ?, ?, ?, 0, 0, 0, ?)""",
                (party_id, name, email, phone, token),
            )
            self._conn.commit()
        return self.party(party_id)

    def upsert_party(self, incoming: dict):
        existing = self.party(incoming["id"]) if incoming.get("id") else None
        if existing is None:
            party_id = incoming.get("id") or new_id("ct")
            with self._lock:
                self._conn.execute(
                    """INSERT INTO parties
                    (id, name, email, phone, email_opt_out, sms_opt_out, do_not_contact, unsub_token)
                    VALUES (?, ?, ?, ?, 0, 0, ?, ?)""",
                    (
                        party_id,
                        incoming.get("name") or "Customer",
                        incoming.get("email") or "",
                        incoming.get("phone") or "",
                        1 if incoming.get("do_not_contact") else 0,
                        secrets.token_urlsafe(12),
                    ),
                )
                self._conn.commit()
            return self.party(party_id)
        email = (incoming.get("email") or "").strip() or existing.email
        phone = (incoming.get("phone") or "").strip() or existing.phone
        with self._lock:
            self._conn.execute(
                "UPDATE parties SET name = ?, email = ?, phone = ?, do_not_contact = ? WHERE id = ?",
                (
                    incoming.get("name") or existing.name,
                    email,
                    phone,
                    1 if incoming.get("do_not_contact") else 0,
                    existing.id,
                ),
            )
            self._conn.commit()
        return self.party(existing.id)

    def set_sms_opt_out(self, party_id: str, opted_out: bool):
        with self._lock:
            self._conn.execute("UPDATE parties SET sms_opt_out = ? WHERE id = ?", (1 if opted_out else 0, party_id))
            self._conn.commit()

    def set_email_opt_out(self, party_id: str, opted_out: bool):
        with self._lock:
            self._conn.execute("UPDATE parties SET email_opt_out = ? WHERE id = ?", (1 if opted_out else 0, party_id))
            self._conn.commit()

    def add_quote(self, party_id: str, quantity: float, detail: str, address: str, amount_cents: int) -> Quote:
        quote_id = new_id("q")
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._insert_quote(
                {
                    "id": quote_id,
                    "party_id": party_id,
                    "quantity": quantity,
                    "detail": detail,
                    "address": address,
                    "amount_cents": amount_cents,
                    "status": "draft",
                    "sent_at": None,
                    "viewed_at": None,
                    "signed_at": None,
                    "token": token,
                    "signer_name": "",
                }
            )
            self._conn.commit()
        return self.quote(quote_id)

    def mark_sent(self, quote_id: str, now: datetime) -> Quote | None:
        quote = self.quote(quote_id)
        if quote is None or quote.status == "signed":
            return quote
        sent_at = quote.sent_at or now
        with self._lock:
            self._conn.execute(
                "UPDATE quotes SET status = 'open', sent_at = ? WHERE id = ?",
                (dump_dt(sent_at), quote_id),
            )
            self._conn.commit()
        return self.quote(quote_id)

    def mark_viewed(self, quote_id: str, now: datetime):
        quote = self.quote(quote_id)
        if quote is None or quote.status != "open" or quote.viewed_at is not None:
            return quote
        with self._lock:
            self._conn.execute("UPDATE quotes SET viewed_at = ? WHERE id = ?", (dump_dt(now), quote_id))
            self._conn.commit()
        return self.quote(quote_id)

    def mark_signed(self, quote_id: str, name: str, now: datetime):
        quote = self.quote(quote_id)
        if quote is None or quote.status != "open":
            return quote
        with self._lock:
            self._conn.execute(
                "UPDATE quotes SET status = 'signed', signed_at = ?, signer_name = ? WHERE id = ?",
                (dump_dt(now), name.strip()[:120], quote_id),
            )
            self._conn.commit()
        return self.quote(quote_id)

    def upsert_job(self, incoming: dict, now: datetime):
        existing = self.job(incoming["id"]) if incoming.get("id") else None
        status = incoming.get("status") or "scheduled"
        completed = load_dt(incoming["completed_at"]) if isinstance(incoming.get("completed_at"), str) else incoming.get("completed_at")
        if status == "complete" and completed is None:
            completed = existing.completed_at if existing and existing.completed_at else now
        if status != "complete":
            completed = existing.completed_at if existing else None
        scheduled = incoming.get("scheduled_at") or (existing.scheduled_at if existing else now)
        row = {
            "id": incoming.get("id") or new_id("pr"),
            "party_id": incoming.get("party_id") or (existing.party_id if existing else ""),
            "ticket_no": incoming.get("ticket_no") or (existing.ticket_no if existing else new_id("SC")),
            "quantity": float(incoming.get("quantity") if incoming.get("quantity") is not None else (existing.quantity if existing else 0)),
            "address": incoming.get("address") if incoming.get("address") is not None else (existing.address if existing else ""),
            "scheduled_at": scheduled,
            "status": status,
            "completed_at": completed,
            "notes": incoming.get("notes") if incoming.get("notes") is not None else (existing.notes if existing else ""),
            "source": incoming.get("source") or (existing.source if existing else "yard"),
        }
        with self._lock:
            if existing:
                self._conn.execute(
                    """UPDATE jobs SET party_id = ?, ticket_no = ?, quantity = ?, address = ?, scheduled_at = ?,
                    status = ?, completed_at = ?, notes = ?, source = ? WHERE id = ?""",
                    (
                        row["party_id"],
                        row["ticket_no"],
                        row["quantity"],
                        row["address"],
                        dump_dt(row["scheduled_at"]),
                        row["status"],
                        dump_dt(row["completed_at"]),
                        row["notes"],
                        row["source"],
                        row["id"],
                    ),
                )
            else:
                self._insert_job(row)
            self._conn.commit()
        return self.job(row["id"])

    def add_message(self, **fields) -> dict:
        message_id = fields.get("id") or new_id("msg")
        created = fields.get("created_at") or datetime.now(timezone.utc)
        row = {
            "id": message_id,
            "nudge_key": fields.get("nudge_key") or "",
            "channel": fields.get("channel") or "",
            "direction": fields.get("direction") or "out",
            "subject_key": fields.get("subject_key") or "",
            "party_id": fields.get("party_id") or "",
            "quote_id": fields.get("quote_id") or "",
            "job_id": fields.get("job_id") or "",
            "subject": fields.get("subject") or "",
            "body": fields.get("body") or "",
            "status": fields.get("status") or "stubbed",
            "created_at": dump_dt(created),
        }
        with self._lock:
            self._conn.execute(
                """INSERT INTO messages
                (id, nudge_key, channel, direction, subject_key, party_id, quote_id, job_id, subject, body, status, created_at)
                VALUES (:id, :nudge_key, :channel, :direction, :subject_key, :party_id, :quote_id, :job_id, :subject, :body, :status, :created_at)""",
                row,
            )
            self._conn.commit()
        row["created_at"] = load_dt(row["created_at"])
        return row

    def messages(self, limit=50) -> list:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._message(row) for row in rows]

    def messages_for(self, *, job_id="", party_id="") -> list:
        with self._lock:
            if job_id:
                rows = self._conn.execute(
                    "SELECT * FROM messages WHERE job_id = ? ORDER BY created_at",
                    (job_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM messages WHERE party_id = ? ORDER BY created_at",
                    (party_id,),
                ).fetchall()
        return [self._message(row) for row in rows]

    def _message(self, row) -> dict:
        item = dict(row)
        item["created_at"] = load_dt(item["created_at"])
        return item

    def done_pairs(self) -> set:
        with self._lock:
            rows = self._conn.execute(
                "SELECT nudge_key, subject_key FROM messages WHERE status IN ('sent', 'stubbed', 'blocked', 'opened') AND subject_key != ''"
            ).fetchall()
        return {(row["nudge_key"], row["subject_key"]) for row in rows}

    def add_call(self, party_id: str, now: datetime, kind: str, note: str) -> dict:
        call_id = new_id("call")
        with self._lock:
            self._conn.execute(
                "INSERT INTO calls (id, party_id, created_at, kind, note) VALUES (?, ?, ?, ?, ?)",
                (call_id, party_id, dump_dt(now), kind, note),
            )
            self._conn.commit()
        return {"id": call_id, "party_id": party_id, "created_at": now, "kind": kind, "note": note}

    def calls_for(self, party_id: str) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM calls WHERE party_id = ? ORDER BY created_at",
                (party_id,),
            ).fetchall()
        found = []
        for row in rows:
            item = dict(row)
            item["created_at"] = load_dt(item["created_at"])
            found.append(item)
        return found
