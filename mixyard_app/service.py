import os
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from followups.catalog import all_items, catalog, item_label
from followups.inbound import classify_sms, normalize_phone, sms_href
from followups.models import ShopSettings
from followups.plan import message_context, plan
from followups.providers import ResendEmail, SendResult, TwilioSms, test_mode
from followups.render import render_message, with_sms_footer
from followups.wording import concrete_wording
from mixyard_app.db import new_id
from mixyard_app.seed import SHOP

TZ_NAME = "America/Los_Angeles"
STATUS_LABELS = {
    "sent": "Sent",
    "stubbed": "Held",
    "blocked": "Held",
    "failed": "Not sent",
    "opened": "Texted",
    "received": "Received",
}


def public_base() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")


def clean_http_url(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if not (text.startswith("https://") or text.startswith("http://")):
        return ""
    if len(text) > 500 or any(char.isspace() for char in text):
        return ""
    return text


def clean_forward(value: str) -> str:
    text = (value or "").strip()[:40]
    digits = re.sub(r"\D", "", text)
    if not text:
        return ""
    if len(digits) < 10:
        return ""
    return text


def apply_patch(current: ShopSettings, patch: dict) -> ShopSettings:
    wording = concrete_wording()
    known = {item.key for item in all_items(wording)}
    switches = dict(current.switches)
    for key, value in (patch.get("switches") or {}).items():
        if key in known:
            switches[key] = bool(value)
    messages = dict(current.messages)
    for key, value in (patch.get("messages") or {}).items():
        if key in messages and isinstance(value, str):
            messages[key] = value.strip()[:2000]
    review = current.google_review_url
    if "google_review_url" in patch:
        review = clean_http_url(patch.get("google_review_url") or "")
    forward = current.forward_to
    if "forward_to" in patch:
        forward = clean_forward(patch.get("forward_to") or "")
    shop_name = current.shop_name
    if "shop_name" in patch:
        shop_name = (patch.get("shop_name") or "").strip()[:80] or SHOP
    return ShopSettings(
        switches=switches,
        messages=messages,
        google_review_url=review,
        forward_to=forward,
        shop_name=shop_name,
    )


def _sample_preview(settings: ShopSettings, key: str, base_url: str) -> str:
    wording = concrete_wording()
    ctx = {
        "customer": "Dana",
        "shop": settings.shop_name,
        "quantity": "7.5",
        "unit": wording.quantity_unit,
        "job": wording.job_noun,
        "address": "88 River Rd, Longview",
        "quote_link": (base_url.rstrip("/") + "/q/preview") if base_url else "/q/preview",
        "review_link": settings.google_review_url or "your Google review link",
        "when": "tomorrow",
        "ticket": "SC-260827-11",
    }
    return render_message(settings.messages.get(key, ""), ctx)


def followups_view(db, base_url: str) -> dict:
    settings = db.settings()
    wording = concrete_wording()
    addon = bool(settings.switches.get("texting_addon"))
    groups = []
    for group in catalog(wording):
        items = []
        for item in group.items:
            items.append(
                {
                    "key": item.key,
                    "label": item.label,
                    "kind": item.kind,
                    "on": bool(settings.switches.get(item.key)),
                    "locked": bool(item.requires_addon and not addon),
                    "has_message": item.has_message,
                    "body": settings.messages.get(item.key, "") if item.has_message else "",
                    "preview": _sample_preview(settings, item.key, base_url) if item.has_message else "",
                }
            )
        groups.append({"id": group.id, "title": group.title, "intro": group.intro, "items": items})
    return {
        "shop_name": settings.shop_name,
        "google_review_url": settings.google_review_url,
        "forward_to": settings.forward_to,
        "email_ready": bool(os.environ.get("RESEND_API_KEY")),
        "texting_ready": bool(test_mode() and os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_FROM_NUMBER")),
        "test_mode": test_mode(),
        "inbox": bool(addon and settings.switches.get("two_way")),
        "groups": groups,
        "activity": activity(db),
    }


def activity(db, limit=40) -> list:
    names = {party.id: party.name for party in db.parties()}
    wording = concrete_wording()
    rows = []
    for message in db.messages(limit):
        rows.append(
            {
                "id": message["id"],
                "at": message["created_at"].isoformat(),
                "who": names.get(message["party_id"], "Customer"),
                "label": item_label(wording, message["nudge_key"]) if message["nudge_key"] not in {"inbound", "shop_reply", "sms_stop_confirm"} else _special_label(message["nudge_key"]),
                "channel": message["channel"],
                "direction": message["direction"],
                "status": message["status"],
                "status_label": STATUS_LABELS.get(message["status"], message["status"]),
                "body": message["body"],
                "quote_id": message["quote_id"],
                "job_id": message["job_id"],
            }
        )
    return rows


def _special_label(key: str) -> str:
    if key == "inbound":
        return "Customer text"
    if key == "shop_reply":
        return "Shop reply"
    if key == "sms_stop_confirm":
        return "Opt-out confirmation"
    return key


def _iso(value):
    return value.isoformat() if value else ""


def quote_tap(settings, party, quote, base_url):
    if quote.status != "open" or not settings.switches.get("tap_quote"):
        return None, ""
    if party is None or party.do_not_contact or party.sms_opt_out or not normalize_phone(party.phone):
        return None, ""
    wording = concrete_wording()
    ctx = message_context(party, settings, wording, base_url, quote, None)
    body = render_message(settings.messages.get("tap_quote", ""), ctx)
    return sms_href(party.phone, body), body


def job_tap(settings, party, job, base_url):
    if party is None or party.do_not_contact or party.sms_opt_out or not normalize_phone(party.phone):
        return None, "", ""
    if job.status == "cancelled":
        return None, "", ""
    if job.status != "complete" and not job.quantity and not job.address:
        return None, "", ""
    key = "tap_done" if job.status == "complete" else "tap_upcoming"
    if not settings.switches.get(key):
        return None, "", ""
    wording = concrete_wording()
    ctx = message_context(party, settings, wording, base_url, None, job)
    body = render_message(settings.messages.get(key, ""), ctx)
    return sms_href(party.phone, body), key, body


def quote_json(db, quote, base_url: str) -> dict:
    party = db.party(quote.party_id)
    settings = db.settings()
    href, _body = quote_tap(settings, party, quote, base_url)
    if quote.status == "signed":
        badge = "Signed"
    elif quote.status == "draft":
        badge = "Draft"
    elif quote.viewed_at and not quote.signed_at:
        badge = "Viewed, not signed"
    elif quote.sent_at:
        badge = "Sent, not viewed"
    else:
        badge = "Draft"
    return {
        "id": quote.id,
        "contact_id": quote.party_id,
        "contact_name": party.name if party else "",
        "quantity": quote.quantity,
        "detail": quote.detail,
        "address": quote.address,
        "amount_cents": quote.amount_cents,
        "status": quote.status,
        "sent_at": _iso(quote.sent_at),
        "viewed_at": _iso(quote.viewed_at),
        "signed_at": _iso(quote.signed_at),
        "signer_name": quote.signer_name,
        "tap_href": href or "",
        "customer_path": "/q/" + quote.token,
        "badge": badge,
    }


def job_json(db, job, base_url: str) -> dict:
    party = db.party(job.party_id)
    settings = db.settings()
    href, key, _body = job_tap(settings, party, job, base_url)
    return {
        "id": job.id,
        "ticket_no": job.ticket_no,
        "contact_id": job.party_id,
        "contact_name": party.name if party else "",
        "quantity": job.quantity,
        "address": job.address,
        "scheduled_at": _iso(job.scheduled_at),
        "status": job.status,
        "completed_at": _iso(job.completed_at),
        "notes": job.notes,
        "source": job.source,
        "tap_href": href or "",
        "tap_nudge": key,
    }


def contact_json(party) -> dict:
    return {
        "id": party.id,
        "name": party.name,
        "email": party.email,
        "phone": party.phone,
        "email_opt_out": party.email_opt_out,
        "sms_opt_out": party.sms_opt_out,
        "do_not_contact": party.do_not_contact,
    }


def bootstrap(db, base_url: str) -> dict:
    return {
        "followups": followups_view(db, base_url),
        "quotes": [quote_json(db, quote, base_url) for quote in db.quotes()],
        "jobs": [job_json(db, job, base_url) for job in db.jobs()],
        "contacts": [contact_json(party) for party in db.parties()],
    }


def deliver(planned, party, emailer, smser) -> SendResult:
    try:
        if planned.channel == "email":
            return emailer.send(party.email, planned.subject, planned.body)
        if planned.channel == "sms":
            return smser.send(party.phone, planned.body)
    except Exception:
        return SendResult("failed", "send failed")
    return SendResult("failed", "unknown channel")


def run_once(db, now=None, base_url=None, emailer=None, smser=None) -> list:
    moment = now or datetime.now(timezone.utc)
    root = public_base() if base_url is None else base_url
    settings = db.settings()
    wording = concrete_wording()
    parties = db.parties()
    planned = plan(
        now=moment,
        tz_name=TZ_NAME,
        settings=settings,
        wording=wording,
        parties=parties,
        quotes=db.quotes(),
        jobs=db.jobs(),
        already=db.done_pairs(),
        base_url=root,
    )
    by_id = {party.id: party for party in parties}
    mail = emailer or ResendEmail()
    texting = smser or TwilioSms()
    sent = []
    for item in planned:
        party = by_id[item.party_id]
        result = deliver(item, party, mail, texting)
        db.add_message(
            nudge_key=item.nudge_key,
            channel=item.channel,
            direction="out",
            subject_key=item.subject_key,
            party_id=item.party_id,
            quote_id=item.quote_id,
            job_id=item.job_id,
            subject=item.subject,
            body=item.body,
            status=result.status,
            created_at=moment,
        )
        sent.append({"nudge": item.nudge_key, "status": result.status, "party_id": item.party_id})
    return sent


def sync_yard(db, payload: dict, now: datetime):
    for contact in payload.get("contacts") or []:
        phones = contact.get("phones") or []
        phone = ""
        if phones and isinstance(phones, list):
            phone = (phones[0] or {}).get("number") or ""
        elif contact.get("phone"):
            phone = contact.get("phone") or ""
        db.upsert_party(
            {
                "id": contact.get("id"),
                "name": contact.get("name") or "Customer",
                "email": contact.get("email") or "",
                "phone": phone,
                "do_not_contact": bool(contact.get("banned") or contact.get("do_not_contact")),
            }
        )
    for pour in payload.get("pours") or []:
        scheduled = pour.get("scheduledAt") or pour.get("scheduled_at")
        try:
            when = datetime.fromisoformat(scheduled) if scheduled else now
        except ValueError:
            when = now
        if when.tzinfo is None:
            when = when.replace(tzinfo=ZoneInfo(TZ_NAME))
        db.upsert_job(
            {
                "id": pour.get("id"),
                "party_id": pour.get("contactId") or pour.get("contact_id") or "",
                "ticket_no": pour.get("ticketNo") or pour.get("ticket_no") or "",
                "quantity": pour.get("yards") if pour.get("yards") is not None else pour.get("quantity") or 0,
                "address": pour.get("address") or "",
                "scheduled_at": when,
                "status": pour.get("status") or "scheduled",
                "completed_at": pour.get("completedAt") or pour.get("completed_at"),
                "notes": pour.get("notes") or "",
                "source": "yard",
            },
            now,
        )


def record_tap(db, nudge: str, quote_id: str, job_id: str, now: datetime, base_url: str):
    settings = db.settings()
    if nudge not in {"tap_quote", "tap_done", "tap_upcoming"} or not settings.switches.get(nudge):
        return None
    party = None
    body = ""
    subject_key = ""
    if quote_id:
        quote = db.quote(quote_id)
        if quote is None:
            return None
        party = db.party(quote.party_id)
        href, body = quote_tap(settings, party, quote, base_url)
        if not href or nudge != "tap_quote":
            return None
        subject_key = "tap:" + quote_id + ":" + new_id("t")
        party_id = quote.party_id
    else:
        job = db.job(job_id)
        if job is None:
            return None
        party = db.party(job.party_id)
        href, key, body = job_tap(settings, party, job, base_url)
        if not href or key != nudge:
            return None
        subject_key = "tap:" + job_id + ":" + new_id("t")
        party_id = job.party_id
        quote_id = ""
    return db.add_message(
        nudge_key=nudge,
        channel="tap",
        direction="out",
        subject_key=subject_key,
        party_id=party_id,
        quote_id=quote_id or "",
        job_id=job_id or "",
        body=body,
        status="opened",
        created_at=now,
    )


def ensure_caller(db, phone: str):
    party = db.party_by_phone(phone)
    if party:
        return party
    number = normalize_phone(phone)
    last4 = re.sub(r"\D", "", number)[-4:] or "call"
    return db.create_party("Caller " + last4, number)


def on_inbound_sms(db, phone: str, body: str, now: datetime, smser=None):
    text = (body or "").strip()[:1000]
    if not text or not normalize_phone(phone):
        return {"error": "A phone number and a message are required."}
    party = ensure_caller(db, phone)
    kind = classify_sms(text)
    if kind == "stop":
        db.add_message(
            nudge_key="inbound",
            channel="sms",
            direction="in",
            subject_key="in:" + new_id("in"),
            party_id=party.id,
            body=text,
            status="received",
            created_at=now,
        )
        db.set_sms_opt_out(party.id, True)
        settings = db.settings()
        confirm = f"You are opted out and will not get texts from {settings.shop_name}."
        sender = smser or TwilioSms()
        result = sender.send(party.phone, confirm)
        db.add_message(
            nudge_key="sms_stop_confirm",
            channel="sms",
            direction="out",
            subject_key="stop:" + party.id,
            party_id=party.id,
            body=confirm,
            status=result.status,
            created_at=now,
        )
        return {"action": "stop", "party_id": party.id}
    if party.do_not_contact:
        db.add_message(
            nudge_key="inbound",
            channel="sms",
            direction="in",
            subject_key="in:" + new_id("in"),
            party_id=party.id,
            body=text,
            status="received",
            created_at=now,
        )
        return {"action": "logged", "party_id": party.id}
    day = now.astimezone(ZoneInfo(TZ_NAME))
    job = db.upsert_job(
        {
            "id": new_id("pr"),
            "party_id": party.id,
            "ticket_no": "SC-" + day.strftime("%y%m%d") + "-" + new_id("t")[-2:],
            "quantity": 0,
            "address": "",
            "scheduled_at": now,
            "status": "scheduled",
            "notes": "Text from " + party.name + ": " + text,
            "source": "text",
        },
        now,
    )
    db.add_message(
        nudge_key="inbound",
        channel="sms",
        direction="in",
        subject_key="in:" + new_id("in"),
        party_id=party.id,
        job_id=job.id,
        body=text,
        status="received",
        created_at=now,
    )
    return {"action": "ticket", "party_id": party.id, "job_id": job.id}


def on_missed_call(db, phone: str, now: datetime, base_url: str, smser=None):
    if not normalize_phone(phone):
        return {"error": "A phone number is required."}
    party = ensure_caller(db, phone)
    call = db.add_call(party.id, now, "missed", "")
    settings = db.settings()
    if not (settings.switches.get("texting_addon") and settings.switches.get("sms_missed_call")):
        return {"texted": False, "party_id": party.id}
    if party.do_not_contact or party.sms_opt_out:
        return {"texted": False, "party_id": party.id}
    wording = concrete_wording()
    ctx = message_context(party, settings, wording, base_url, None, None)
    body = with_sms_footer(render_message(settings.messages.get("sms_missed_call", ""), ctx))
    sender = smser or TwilioSms()
    result = sender.send(party.phone, body)
    db.add_message(
        nudge_key="sms_missed_call",
        channel="sms",
        direction="out",
        subject_key="call:" + call["id"],
        party_id=party.id,
        body=body,
        status=result.status,
        created_at=now,
    )
    return {"texted": True, "status": result.status, "party_id": party.id}


def shop_reply(db, party_id: str, text: str, now: datetime, smser=None):
    settings = db.settings()
    if not (settings.switches.get("texting_addon") and settings.switches.get("two_way")):
        return {"error": "Two-way texting is off.", "status": 403}
    party = db.party(party_id)
    if party is None:
        return {"error": "No customer.", "status": 404}
    if party.sms_opt_out:
        return {"error": "This customer opted out of texts.", "status": 409}
    body = (text or "").strip()[:1000]
    if not body:
        return {"error": "Write a message first.", "status": 400}
    sender = smser or TwilioSms()
    result = sender.send(party.phone, body)
    db.add_message(
        nudge_key="shop_reply",
        channel="sms",
        direction="out",
        subject_key="reply:" + new_id("r"),
        party_id=party.id,
        body=body,
        status=result.status,
        created_at=now,
    )
    return {"status": 200, "send_status": result.status}


def thread_for(db, party_id: str) -> dict:
    party = db.party(party_id)
    if party is None:
        return {}
    settings = db.settings()
    items = []
    for message in db.messages_for(party_id=party_id):
        items.append(
            {
                "kind": "message",
                "at": message["created_at"].isoformat(),
                "direction": message["direction"],
                "body": message["body"],
                "status": message["status"],
                "status_label": STATUS_LABELS.get(message["status"], message["status"]),
                "channel": message["channel"],
            }
        )
    for call in db.calls_for(party_id):
        items.append(
            {
                "kind": "call",
                "at": call["created_at"].isoformat(),
                "direction": "in",
                "body": "Missed call",
                "status": "received",
                "status_label": "Missed call",
                "channel": "call",
            }
        )
    items.sort(key=lambda item: item["at"])
    return {
        "contact_id": party.id,
        "sms_opt_out": party.sms_opt_out,
        "email_opt_out": party.email_opt_out,
        "inbox": bool(settings.switches.get("texting_addon") and settings.switches.get("two_way")),
        "items": items,
    }


def job_messages(db, job_id: str) -> list:
    wording = concrete_wording()
    rows = []
    for message in db.messages_for(job_id=job_id):
        label = item_label(wording, message["nudge_key"])
        if message["nudge_key"] in {"inbound", "shop_reply", "sms_stop_confirm"}:
            label = _special_label(message["nudge_key"])
        rows.append(
            {
                "id": message["id"],
                "at": message["created_at"].isoformat(),
                "label": label,
                "body": message["body"],
                "status": message["status"],
                "status_label": STATUS_LABELS.get(message["status"], message["status"]),
                "channel": message["channel"],
            }
        )
    return rows
