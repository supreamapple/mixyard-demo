from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from followups.catalog import email_subjects
from followups.inbound import normalize_phone
from followups.models import Job, Party, Planned, Quote, ShopSettings
from followups.render import first_name, quantity_text, render_message, with_email_footer, with_sms_footer
from followups.wording import TradeWording

QUOTE_STEPS = (
    ("email_quote_day_2", "sms_quote_day_2", 2, 5),
    ("email_quote_day_5", "sms_quote_day_5", 5, 10),
    ("email_quote_day_10", "sms_quote_day_10", 10, 12),
)
REVIEW_KEYS = ("email_review", "sms_review")
REMINDER_KEYS = (
    ("email_day_before", "sms_day_before", -1, 16, 20),
    ("email_morning", "sms_morning", 0, 7, 11),
)
OPEN_JOB = {"scheduled", "en_route", "pouring"}
HANDLED = {"sent", "stubbed", "blocked", "opened"}


def _local(moment: datetime, tz: ZoneInfo) -> datetime:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(tz)


def quote_window(sent_at: datetime, now: datetime, tz: ZoneInfo, start_day: int, end_day: int) -> bool:
    sent_local = _local(sent_at, tz)
    start_date = (sent_local + timedelta(days=start_day)).date()
    end_date = (sent_local + timedelta(days=end_day)).date()
    start = datetime(start_date.year, start_date.month, start_date.day, 9, 0, tzinfo=tz)
    end = datetime(end_date.year, end_date.month, end_date.day, 9, 0, tzinfo=tz)
    current = _local(now, tz)
    return start <= current < end


def reminder_window(scheduled_at: datetime, now: datetime, tz: ZoneInfo, day_delta: int, start_hour: int, end_hour: int) -> bool:
    when = _local(scheduled_at, tz)
    target = (when + timedelta(days=day_delta)).date()
    current = _local(now, tz)
    return current.date() == target and start_hour <= current.hour < end_hour


def message_context(party: Party, settings: ShopSettings, wording: TradeWording, base_url: str, quote: Quote | None, job: Job | None) -> dict:
    root = (base_url or "").rstrip("/")
    review = settings.google_review_url
    when = ""
    ticket = ""
    quantity = ""
    address = ""
    link = ""
    if quote is not None:
        quantity = quantity_text(quote.quantity)
        address = quote.address
        link = f"{root}/q/{quote.token}" if root else f"/q/{quote.token}"
    if job is not None:
        quantity = quantity or quantity_text(job.quantity)
        address = address or job.address
        ticket = job.ticket_no
        local_when = _local(job.scheduled_at, ZoneInfo("UTC"))
        when = local_when.strftime("%b ") + str(local_when.day)
    unsub = f"{root}/u/{party.unsub_token}" if root else f"/u/{party.unsub_token}"
    return {
        "customer": first_name(party.name),
        "shop": settings.shop_name,
        "quantity": quantity,
        "unit": wording.quantity_unit,
        "job": wording.job_noun,
        "address": address or "the jobsite",
        "quote_link": link,
        "review_link": review,
        "when": when,
        "ticket": ticket,
        "unsub_url": unsub,
    }


def _eligible(party: Party, channel: str) -> bool:
    if party.do_not_contact:
        return False
    if channel == "email":
        return bool((party.email or "").strip()) and not party.email_opt_out
    if channel == "sms":
        return bool(normalize_phone(party.phone)) and not party.sms_opt_out
    return False


def _append(out, settings, wording, party, key, channel, subject_key, ctx, already, quote_id="", job_id=""):
    if not settings.switches.get(key):
        return
    if channel == "sms" and not settings.switches.get("texting_addon"):
        return
    if (key, subject_key) in already:
        return
    if key in REVIEW_KEYS and not settings.google_review_url:
        return
    if not _eligible(party, channel):
        return
    template = settings.messages.get(key) or ""
    body = render_message(template, ctx)
    subject = ""
    if channel == "email":
        subject = render_message(email_subjects(wording).get(key, "A note from {shop}"), ctx)
        body = with_email_footer(body, ctx.get("unsub_url") or "")
    elif channel == "sms":
        body = with_sms_footer(body)
    out.append(
        Planned(
            nudge_key=key,
            channel=channel,
            subject_key=subject_key,
            party_id=party.id,
            quote_id=quote_id,
            job_id=job_id,
            subject=subject,
            body=body,
        )
    )


def plan(now, tz_name, settings, wording, parties, quotes, jobs, already, base_url) -> list:
    tz = ZoneInfo(tz_name)
    by_id = {party.id: party for party in parties}
    found = []
    for quote in quotes:
        party = by_id.get(quote.party_id)
        if party is None or quote.status != "open" or quote.sent_at is None or quote.viewed_at is None or quote.signed_at is not None:
            continue
        ctx = message_context(party, settings, wording, base_url, quote, None)
        subject_key = "quote:" + quote.id
        for email_key, sms_key, start_day, end_day in QUOTE_STEPS:
            if not quote_window(quote.sent_at, now, tz, start_day, end_day):
                continue
            _append(found, settings, wording, party, email_key, "email", subject_key, ctx, already, quote_id=quote.id)
            _append(found, settings, wording, party, sms_key, "sms", subject_key, ctx, already, quote_id=quote.id)
    for job in jobs:
        party = by_id.get(job.party_id)
        if party is None:
            continue
        ctx = message_context(party, settings, wording, base_url, None, job)
        subject_key = "job:" + job.id
        if job.status in OPEN_JOB:
            for email_key, sms_key, delta, start_hour, end_hour in REMINDER_KEYS:
                if not reminder_window(job.scheduled_at, now, tz, delta, start_hour, end_hour):
                    continue
                _append(found, settings, wording, party, email_key, "email", subject_key, ctx, already, job_id=job.id)
                _append(found, settings, wording, party, sms_key, "sms", subject_key, ctx, already, job_id=job.id)
        if job.status == "complete" and job.completed_at is not None:
            end = job.completed_at + timedelta(days=7)
            if job.completed_at <= now < end:
                for key in REVIEW_KEYS:
                    channel = "email" if key.startswith("email") else "sms"
                    _append(found, settings, wording, party, key, channel, subject_key, ctx, already, job_id=job.id)
    return found


def handled_status(status: str) -> bool:
    return status in HANDLED
