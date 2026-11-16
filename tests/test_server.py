import json
import os
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timezone
from urllib.error import HTTPError

from followups.signature import twilio_signature
from mixyard_app.db import Database
from mixyard_app.server import make_server
from mixyard_app.service import job_tap, run_once

UTC = timezone.utc


class ServerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "yard.db"), now=datetime(2026, 11, 16, 16, 0, tzinfo=UTC))
        self.httpd = make_server(self.db, port=0)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.db.close()
        self.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req) as response:
                raw = response.read().decode()
                return response.status, json.loads(raw) if raw else {}
        except HTTPError as error:
            raw = error.read().decode()
            return error.code, json.loads(raw) if raw else {}

    def test_health_and_switches_default_off(self):
        status, health = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health, {"ok": True})
        status, view = self.request("GET", "/api/followups")
        self.assertEqual(status, 200)
        self.assertEqual([group["title"] for group in view["groups"]], ["Quotes", "Jobs done / reviews", "Reminders", "Texting"])
        self.assertTrue(all(item["on"] is False for group in view["groups"] for item in group["items"]))
        self.assertEqual(view["activity"], [])
        status, page = self._raw("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"MixYard", page)

    def test_settings_round_trip_and_held_email(self):
        status, view = self.request("PUT", "/api/followups", {"switches": {"email_quote_day_2": True}, "google_review_url": "javascript:alert(1)"})
        self.assertEqual(status, 200)
        day2 = next(item for item in view["groups"][0]["items"] if item["key"] == "email_quote_day_2")
        self.assertTrue(day2["on"])
        self.assertEqual(view["google_review_url"], "")
        sent = run_once(self.db, now=datetime(2026, 11, 16, 18, 0, tzinfo=UTC), base_url=self.base)
        self.assertEqual(sent, [{"nudge": "email_quote_day_2", "status": "stubbed", "party_id": "ct_river"}])
        again = run_once(self.db, now=datetime(2026, 11, 16, 18, 30, tzinfo=UTC), base_url=self.base)
        self.assertEqual(again, [])
        status, view = self.request("GET", "/api/followups")
        self.assertEqual(view["activity"][0]["status_label"], "Held")
        self.assertIn("pour", view["activity"][0]["body"])

    def test_quote_view_and_sign(self):
        status, html = self._raw("GET", "/q/seedq-cedar?preview=1")
        self.assertEqual(status, 200)
        self.assertIn("4 yards", html.decode())
        quote = self.db.quote("q_fresh")
        self.assertIsNone(quote.viewed_at)
        status, html = self._raw("GET", "/q/seedq-cedar")
        self.assertIn("Sign quote", html.decode())
        self.assertIsNotNone(self.db.quote("q_fresh").viewed_at)
        status, html = self._raw("POST", "/q/seedq-cedar", b"name=Tom%20Bricker", "application/x-www-form-urlencoded")
        self.assertIn("Quote signed", html.decode())
        self.assertEqual(self.db.quote("q_fresh").status, "signed")
        status, html = self._raw("GET", "/u/unsub-cedar")
        self.assertIn("Unsubscribed", html.decode())
        self.assertTrue(self.db.party("ct_cedar").email_opt_out)

    def test_stop_and_reply_and_missed_call(self):
        self.request("PUT", "/api/followups", {"switches": {"texting_addon": True, "sms_missed_call": True, "two_way": True}})
        status, stopped = self.request(
            "POST",
            "/api/sms/inbound",
            {"from": "(360) 555-0142", "body": "STOP"},
            {"X-Mixyard-Test": "1"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(stopped["action"], "stop")
        self.assertTrue(self.db.party("ct_river").sms_opt_out)
        self.assertFalse(any(job.source == "text" for job in self.db.jobs()))
        status, missed = self.request(
            "POST",
            "/api/voice/missed",
            {"from": "(360) 555-0198"},
            {"X-Mixyard-Test": "1"},
        )
        self.assertEqual(missed["texted"], True)
        self.assertEqual(missed["status"], "stubbed")
        status, reply = self.request(
            "POST",
            "/api/sms/inbound",
            {"from": "(360) 555-0198", "body": "Can you pour Thursday?"},
            {"X-Mixyard-Test": "1"},
        )
        self.assertEqual(reply["action"], "ticket")
        created = self.db.job(reply["job_id"])
        self.assertEqual(created.source, "text")
        self.assertIn("Thursday", created.notes)
        logged = self.db.messages_for(job_id=reply["job_id"])
        self.assertTrue(any("Thursday" in message["body"] for message in logged))
        status, denied = self.request("POST", "/api/sms/inbound", {"from": "(360) 555-0198", "body": "Hello"})
        self.assertEqual(status, 403)
        thread = self.request("GET", "/api/contacts/ct_cedar/thread")[1]
        kinds = [item["kind"] for item in thread["items"]]
        self.assertIn("call", kinds)
        self.assertIn("message", kinds)
        status, sent = self.request("POST", "/api/contacts/ct_cedar/reply", {"text": "Thursday works."})
        self.assertEqual(status, 200)
        self.assertEqual(sent["send_status"], "stubbed")
        self.db.set_sms_opt_out("ct_river", True)
        status, blocked = self.request("POST", "/api/contacts/ct_river/reply", {"text": "Hi"})
        self.assertEqual(status, 409)

    def test_form_webhook_checks_signature(self):
        previous = os.environ.get("TWILIO_AUTH_TOKEN")
        os.environ["TWILIO_AUTH_TOKEN"] = "token"
        try:
            url = self.base + "/api/sms/inbound"
            params = {"From": "+13605550198", "Body": "See you at the pour"}
            signed = twilio_signature("token", url, params)
            raw = "From=%2B13605550198&Body=See%20you%20at%20the%20pour".encode()
            status, payload = self._raw(
                "POST",
                "/api/sms/inbound",
                raw,
                "application/x-www-form-urlencoded",
                {"X-Twilio-Signature": signed},
            )
        finally:
            if previous is None:
                os.environ.pop("TWILIO_AUTH_TOKEN", None)
            else:
                os.environ["TWILIO_AUTH_TOKEN"] = previous
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["action"], "ticket")
        status, _payload = self._raw("POST", "/api/sms/inbound", b"Body=Hi&From=%2B13605550198", "application/x-www-form-urlencoded")
        self.assertEqual(status, 403)

    def test_sync_keeps_opt_out_and_complete_time(self):
        self.db.set_email_opt_out("ct_river", True)
        done = next(job for job in self.db.jobs() if job.id == "pr_done")
        self.request(
            "POST",
            "/api/jobs/sync",
            {
                "contacts": [{"id": "ct_river", "name": "Dana Ellison", "email": "", "phones": [{"number": "(360) 555-0142"}], "banned": False}],
                "pours": [
                    {
                        "id": "pr_done",
                        "contactId": "ct_patel",
                        "ticketNo": done.ticket_no,
                        "yards": 2.5,
                        "address": done.address,
                        "scheduledAt": done.scheduled_at.isoformat(),
                        "status": "complete",
                        "notes": done.notes,
                    }
                ],
            },
        )
        self.assertTrue(self.db.party("ct_river").email_opt_out)
        self.assertEqual(self.db.party("ct_river").email, "dana@riverbend.example")
        self.assertIsNotNone(self.db.job("pr_done").completed_at)

    def test_text_ticket_has_no_pour_text(self):
        settings = self.db.settings()
        settings.switches["tap_upcoming"] = True
        self.db.save_settings(settings)
        moment = datetime(2026, 11, 16, 16, 0, tzinfo=UTC)
        job = self.db.upsert_job(
            {
                "id": "pr_text",
                "party_id": "ct_cedar",
                "ticket_no": "SC-text",
                "quantity": 0,
                "address": "",
                "scheduled_at": moment,
                "status": "scheduled",
                "notes": "Text from the customer",
                "source": "text",
            },
            moment,
        )
        href, _key, _body = job_tap(self.db.settings(), self.db.party("ct_cedar"), job, self.base)
        self.assertIsNone(href)

    def _raw(self, method, path, body=None, content_type=None, headers=None):
        req = urllib.request.Request(self.base + path, data=body, method=method)
        if content_type:
            req.add_header("Content-Type", content_type)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()


if __name__ == "__main__":
    unittest.main()
