import os
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from followups.catalog import catalog, default_messages, default_settings
from followups.inbound import classify_sms, fictional_phone, sms_href
from followups.models import Job, Party, Quote
from followups.plan import plan
from followups.providers import ResendEmail, TwilioSms
from followups.signature import signature_matches, twilio_signature
from followups.wording import TradeWording, concrete_wording

UTC = timezone.utc
LA = ZoneInfo("America/Los_Angeles")


def aware(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=LA).astimezone(UTC)


def party(**kwargs):
    base = dict(
        id="ct_river",
        name="Dana Ellison",
        email="dana@riverbend.example",
        phone="(360) 555-0142",
        email_opt_out=False,
        sms_opt_out=False,
        do_not_contact=False,
        unsub_token="unsub-river",
    )
    base.update(kwargs)
    return Party(**base)


def quote(**kwargs):
    sent = aware(2026, 11, 14, 10, 0)
    base = dict(
        id="q_viewed",
        party_id="ct_river",
        quantity=7.5,
        detail="4000 PSI",
        address="88 River Rd, Longview, WA 98632",
        amount_cents=148500,
        status="open",
        sent_at=sent,
        viewed_at=sent + timedelta(hours=5),
        signed_at=None,
        token="seedq-river",
        signer_name="",
    )
    base.update(kwargs)
    return Quote(**base)


def job(**kwargs):
    base = dict(
        id="pr_1",
        party_id="ct_river",
        ticket_no="SC-260827-11",
        quantity=7.5,
        address="88 River Rd, Longview, WA 98632",
        scheduled_at=aware(2026, 11, 16, 7, 30),
        status="scheduled",
        completed_at=None,
        notes="",
        source="yard",
    )
    base.update(kwargs)
    return Job(**base)


def settings_on(*keys, review="https://g.page/specialty"):
    wording = concrete_wording()
    settings = default_settings(wording, "Specialty Concrete")
    for key in keys:
        settings.switches[key] = True
    settings.google_review_url = review
    return settings


class CatalogTests(unittest.TestCase):
    def test_every_switch_starts_off(self):
        settings = default_settings(concrete_wording(), "Specialty Concrete")
        self.assertTrue(settings.switches)
        self.assertTrue(all(value is False for value in settings.switches.values()))

    def test_groups_and_concrete_words(self):
        groups = catalog(concrete_wording())
        self.assertEqual([group.title for group in groups], ["Quotes", "Jobs done / reviews", "Reminders", "Texting"])
        blob = " ".join(default_messages(concrete_wording()).values())
        self.assertIn("yards", blob)
        self.assertIn("pour", blob)
        other = TradeWording("visit", "visits", "hours", "estimate")
        other_blob = " ".join(default_messages(other).values())
        self.assertIn("hours", other_blob)
        self.assertIn("visit", other_blob)
        self.assertNotIn("yards", other_blob)

    def test_sms_link_uses_the_message(self):
        href = sms_href("(360) 555-0142", "Hi Dana")
        self.assertTrue(href.startswith("sms:+13605550142?body="))
        self.assertIn("Hi%20Dana", href)


class PlanTests(unittest.TestCase):
    def test_quiet_when_switches_are_off(self):
        found = plan(
            now=aware(2026, 11, 16, 10, 0),
            tz_name="America/Los_Angeles",
            settings=default_settings(concrete_wording(), "Specialty Concrete"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[quote()],
            jobs=[job()],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual(found, [])

    def test_viewed_open_quote_gets_day_2_only_inside_the_window(self):
        before = plan(
            now=aware(2026, 11, 16, 8, 30),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_quote_day_2"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[quote()],
            jobs=[],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual(before, [])
        found = plan(
            now=aware(2026, 11, 16, 9, 15),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_quote_day_2", "email_quote_day_5"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[quote()],
            jobs=[],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual([item.nudge_key for item in found], ["email_quote_day_2"])
        self.assertIn("pour", found[0].body)
        self.assertIn("yards", found[0].body)
        self.assertIn("https://yard.test/q/seedq-river", found[0].body)
        self.assertIn("/u/unsub-river", found[0].body)

    def test_unseen_or_signed_quotes_do_not_nudge(self):
        unseen = quote(viewed_at=None)
        signed = quote(status="signed", signed_at=aware(2026, 11, 15, 12, 0))
        found = plan(
            now=aware(2026, 11, 16, 9, 15),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_quote_day_2"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[unseen, signed],
            jobs=[],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual(found, [])

    def test_sms_quote_needs_the_addon(self):
        off = plan(
            now=aware(2026, 11, 16, 9, 15),
            tz_name="America/Los_Angeles",
            settings=settings_on("sms_quote_day_2"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[quote()],
            jobs=[],
            already=set(),
            base_url="https://yard.test",
        )
        on = plan(
            now=aware(2026, 11, 16, 9, 15),
            tz_name="America/Los_Angeles",
            settings=settings_on("texting_addon", "sms_quote_day_2"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[quote()],
            jobs=[],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual(off, [])
        self.assertEqual([item.nudge_key for item in on], ["sms_quote_day_2"])
        self.assertIn("STOP", on[0].body)

    def test_opt_out_banned_and_dedupe(self):
        moment = aware(2026, 11, 16, 9, 15)
        common = dict(
            now=moment,
            tz_name="America/Los_Angeles",
            settings=settings_on("email_quote_day_2"),
            wording=concrete_wording(),
            quotes=[quote()],
            jobs=[],
            base_url="https://yard.test",
        )
        self.assertEqual(plan(parties=[party(email_opt_out=True)], already=set(), **common), [])
        self.assertEqual(plan(parties=[party(do_not_contact=True)], already=set(), **common), [])
        again = plan(parties=[party()], already={("email_quote_day_2", "quote:q_viewed")}, **common)
        self.assertEqual(again, [])

    def test_reminders_and_review(self):
        morning = plan(
            now=aware(2026, 11, 16, 7, 5),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_morning"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[],
            jobs=[job()],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual([item.nudge_key for item in morning], ["email_morning"])
        too_early = plan(
            now=aware(2026, 11, 16, 6, 30),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_morning"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[],
            jobs=[job()],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual(too_early, [])
        eve = plan(
            now=aware(2026, 11, 16, 16, 15),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_day_before"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[],
            jobs=[job(scheduled_at=aware(2026, 11, 17, 8, 30))],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual([item.nudge_key for item in eve], ["email_day_before"])
        done = job(status="complete", completed_at=aware(2026, 11, 15, 11, 0))
        missing_link = plan(
            now=aware(2026, 11, 16, 9, 0),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_review", review=""),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[],
            jobs=[done],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual(missing_link, [])
        review = plan(
            now=aware(2026, 11, 16, 9, 0),
            tz_name="America/Los_Angeles",
            settings=settings_on("email_review"),
            wording=concrete_wording(),
            parties=[party()],
            quotes=[],
            jobs=[done],
            already=set(),
            base_url="https://yard.test",
        )
        self.assertEqual([item.nudge_key for item in review], ["email_review"])
        self.assertIn("https://g.page/specialty", review[0].body)


class ProviderTests(unittest.TestCase):
    def test_demo_mail_and_text_are_held(self):
        calls = []

        def transport(*args):
            calls.append(args)
            return 200, "{}"

        mail = ResendEmail(api_key="re_test", from_addr="Specialty Concrete <support@themixyard.com>", transport=transport)
        self.assertEqual(mail.send("dana@riverbend.example", "Hi", "Body").status, "stubbed")
        self.assertEqual(mail.from_addr, "Specialty Concrete <support@themixyard.com>")
        held = ResendEmail(api_key="", transport=transport)
        self.assertEqual(held.send("owner@specialtyconcrete.com", "Hi", "Body").status, "stubbed")
        text = TwilioSms(account_sid="ACxxx", auth_token="tok", from_number="+15005550006", transport=transport)
        self.assertEqual(text.send("+13605550142", "Hi").status, "stubbed")
        self.assertEqual(calls, [])

    def test_live_texting_is_refused(self):
        previous = os.environ.get("TWILIO_MODE")
        os.environ["TWILIO_MODE"] = "live"
        try:
            result = TwilioSms(account_sid="ACxxx", auth_token="tok", from_number="+15005550006").send("+13605550199", "Hi")
        finally:
            if previous is None:
                os.environ.pop("TWILIO_MODE", None)
            else:
                os.environ["TWILIO_MODE"] = previous
        self.assertEqual(result.status, "blocked")

    def test_real_email_uses_the_support_sender(self):
        seen = {}

        def transport(method, url, headers, data):
            seen["url"] = url
            seen["headers"] = headers
            seen["data"] = data
            return 200, "{}"

        mail = ResendEmail(api_key="re_test", transport=transport)
        result = mail.send("owner@specialtyconcrete.com", "Your quote is still open", "Hello")
        self.assertEqual(result.status, "sent")
        self.assertIn("support@themixyard.com", seen["data"].decode())
        self.assertTrue(seen["headers"]["Authorization"].startswith("Bearer "))

    def test_signature_round_trip(self):
        params = {"Body": "STOP", "From": "+13605550142"}
        signed = twilio_signature("token", "https://yard.test/api/sms/inbound", params)
        self.assertTrue(signature_matches("token", "https://yard.test/api/sms/inbound", params, signed))
        self.assertFalse(signature_matches("token", "https://yard.test/api/sms/inbound", params, "nope"))

    def test_stop_words(self):
        self.assertEqual(classify_sms(" stop "), "stop")
        self.assertEqual(classify_sms("Can you pour Thursday?"), "reply")
        self.assertTrue(fictional_phone("+1 (360) 555-0142"))
        self.assertFalse(fictional_phone("+13605560142"))


if __name__ == "__main__":
    unittest.main()
