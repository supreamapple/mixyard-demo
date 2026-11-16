from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from followups.catalog import default_settings
from followups.wording import concrete_wording

TZ = ZoneInfo("America/Los_Angeles")
SHOP = "Specialty Concrete"


def _at(now: datetime, days: int, hour: int, minute: int) -> datetime:
    local = now.astimezone(TZ)
    day = (local + timedelta(days=days)).date()
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ).astimezone(now.tzinfo)


def seed_world(now: datetime) -> dict:
    wording = concrete_wording()
    settings = default_settings(wording, SHOP)
    parties = [
        {
            "id": "ct_river",
            "name": "Dana Ellison",
            "email": "dana@riverbend.example",
            "phone": "(360) 555-0142",
            "email_opt_out": 0,
            "sms_opt_out": 0,
            "do_not_contact": 0,
            "unsub_token": "unsub-river",
        },
        {
            "id": "ct_cedar",
            "name": "Tom Bricker",
            "email": "tom@bricker.example",
            "phone": "(360) 555-0198",
            "email_opt_out": 0,
            "sms_opt_out": 0,
            "do_not_contact": 0,
            "unsub_token": "unsub-cedar",
        },
        {
            "id": "ct_patel",
            "name": "Priya Patel",
            "email": "priya@patel.example",
            "phone": "(360) 555-0117",
            "email_opt_out": 0,
            "sms_opt_out": 0,
            "do_not_contact": 0,
            "unsub_token": "unsub-patel",
        },
        {
            "id": "ct_bad",
            "name": "Skip Pay Co",
            "email": "skip@skippay.example",
            "phone": "(360) 555-0000",
            "email_opt_out": 0,
            "sms_opt_out": 0,
            "do_not_contact": 1,
            "unsub_token": "unsub-bad",
        },
    ]
    quotes = [
        {
            "id": "q_viewed",
            "party_id": "ct_river",
            "quantity": 7.5,
            "detail": "4000 PSI",
            "address": "88 River Rd, Longview, WA 98632",
            "amount_cents": 148500,
            "status": "open",
            "sent_at": _at(now, -2, 10, 0),
            "viewed_at": _at(now, -2, 15, 0),
            "signed_at": None,
            "token": "seedq-river",
            "signer_name": "",
        },
        {
            "id": "q_fresh",
            "party_id": "ct_cedar",
            "quantity": 4,
            "detail": "3500 PSI",
            "address": "1847 Cedar Ave, Longview, WA 98632",
            "amount_cents": 75200,
            "status": "open",
            "sent_at": now - timedelta(hours=1),
            "viewed_at": None,
            "signed_at": None,
            "token": "seedq-cedar",
            "signer_name": "",
        },
        {
            "id": "q_signed",
            "party_id": "ct_patel",
            "quantity": 2.5,
            "detail": "3000 PSI",
            "address": "912 17th Ave, Longview, WA 98632",
            "amount_cents": 44500,
            "status": "signed",
            "sent_at": _at(now, -12, 9, 0),
            "viewed_at": _at(now, -11, 18, 0),
            "signed_at": _at(now, -10, 11, 0),
            "token": "seedq-patel",
            "signer_name": "Priya Patel",
        },
    ]
    jobs = [
        {
            "id": "pr_1",
            "party_id": "ct_river",
            "ticket_no": "SC-260827-11",
            "quantity": 7.5,
            "address": "88 River Rd, Longview, WA 98632",
            "scheduled_at": _at(now, 0, 7, 30),
            "status": "en_route",
            "completed_at": None,
            "notes": "Footings + stem. Gate code 4412.",
            "source": "yard",
        },
        {
            "id": "pr_2",
            "party_id": "ct_cedar",
            "ticket_no": "SC-260827-12",
            "quantity": 4,
            "address": "1847 Cedar Ave, Longview, WA 98632",
            "scheduled_at": _at(now, 0, 10, 0),
            "status": "scheduled",
            "completed_at": None,
            "notes": "",
            "source": "yard",
        },
        {
            "id": "pr_3",
            "party_id": "ct_patel",
            "ticket_no": "SC-260827-13",
            "quantity": 2.5,
            "address": "912 17th Ave, Longview, WA 98632",
            "scheduled_at": _at(now, 0, 13, 30),
            "status": "scheduled",
            "completed_at": None,
            "notes": "Call on approach — dog in yard.",
            "source": "yard",
        },
        {
            "id": "pr_done",
            "party_id": "ct_patel",
            "ticket_no": "SC-done-01",
            "quantity": 2.5,
            "address": "912 17th Ave, Longview, WA 98632",
            "scheduled_at": _at(now, -1, 9, 0),
            "status": "complete",
            "completed_at": _at(now, -1, 11, 0),
            "notes": "Driveway poured and finished.",
            "source": "yard",
        },
        {
            "id": "pr_next",
            "party_id": "ct_river",
            "ticket_no": "SC-next-01",
            "quantity": 6,
            "address": "410 Industrial Way, Kelso, WA 98626",
            "scheduled_at": _at(now, 1, 8, 30),
            "status": "scheduled",
            "completed_at": None,
            "notes": "Shop slab.",
            "source": "yard",
        },
    ]
    return {"settings": settings, "parties": parties, "quotes": quotes, "jobs": jobs}
