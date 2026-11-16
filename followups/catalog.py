from dataclasses import dataclass

from followups.models import ShopSettings
from followups.wording import TradeWording


@dataclass(frozen=True)
class FollowupItem:
    key: str
    group: str
    label: str
    kind: str
    requires_addon: bool
    has_message: bool


@dataclass(frozen=True)
class FollowupGroup:
    id: str
    title: str
    intro: str
    items: tuple


def default_messages(wording: TradeWording) -> dict:
    job = wording.job_noun
    unit = wording.quantity_unit
    quote = wording.quote_noun
    return {
        "tap_quote": (
            f"Hi {{customer}}, this is {{shop}}. Your {quote} for {{quantity}} {unit} "
            "is ready to look over: {quote_link}"
        ),
        "email_quote_day_2": (
            f"Hi {{customer}}, checking in on the {quote} for {{quantity}} {unit} at {{address}}. "
            f"The {job} is still open if you want to walk through it: {{quote_link}}"
        ),
        "email_quote_day_5": (
            f"Hi {{customer}}, the {quote} for {{quantity}} {unit} at {{address}} is still here. "
            f"Happy to adjust the {job} if the plan changed: {{quote_link}}"
        ),
        "email_quote_day_10": (
            f"Hi {{customer}}, last note from {{shop}} on the open {quote} for the {job} at {{address}}. "
            f"We will close it if we do not hear back: {{quote_link}}"
        ),
        "tap_done": (
            f"Hi {{customer}}, this is {{shop}}. The {job} at {{address}} is finished. Thank you for the work."
        ),
        "email_review": (
            f"Hi {{customer}}, thank you for having {{shop}} out for the {job} at {{address}}. "
            "If it looks right, a short review helps the yard: {review_link}"
        ),
        "tap_upcoming": (
            f"Hi {{customer}}, this is {{shop}}. We are on for the {job} at {{address}} "
            f"({{quantity}} {unit}). Reply if the gate or time changed."
        ),
        "email_day_before": (
            f"Hi {{customer}}, a reminder from {{shop}}: we are set for the {job} tomorrow at {{address}}, "
            f"{{quantity}} {unit}. Reply if anything changed."
        ),
        "email_morning": (
            f"Hi {{customer}}, {{shop}} is on for this morning's {job} at {{address}} ({{quantity}} {unit})."
        ),
        "sms_quote_day_2": (
            f"Hi {{customer}}, your {quote} from {{shop}} for {{quantity}} {unit} is still open: {{quote_link}}"
        ),
        "sms_quote_day_5": (
            f"Hi {{customer}}, the {quote} for the {job} at {{address}} is still open: {{quote_link}}"
        ),
        "sms_quote_day_10": (
            f"Hi {{customer}}, last note on your {quote} from {{shop}}: {{quote_link}}"
        ),
        "sms_review": (
            f"Hi {{customer}}, thanks for the {job} at {{address}}. A review helps {{shop}}: {{review_link}}"
        ),
        "sms_day_before": (
            f"Hi {{customer}}, {{shop}} is set for your {job} tomorrow at {{address}} ({{quantity}} {unit})."
        ),
        "sms_morning": (
            f"Hi {{customer}}, {{shop}} is coming this morning for the {job} at {{address}}."
        ),
        "sms_missed_call": (
            f"Hi {{customer}}, we missed your call at {{shop}}. Text us back and we will get the {job} on the board."
        ),
    }


def email_subjects(wording: TradeWording) -> dict:
    job = wording.job_noun
    quote = wording.quote_noun
    return {
        "email_quote_day_2": f"Your {quote} is still open",
        "email_quote_day_5": f"Checking in on your {quote}",
        "email_quote_day_10": f"Last note on your {quote}",
        "email_review": f"How did the {job} go?",
        "email_day_before": f"Reminder: {job} tomorrow",
        "email_morning": f"Reminder: {job} this morning",
    }


def catalog(wording: TradeWording) -> list:
    job = wording.job_noun
    quote = wording.quote_noun
    items = (
        FollowupItem("tap_quote", "quotes", f"Tap to text an open {quote}", "tap", False, True),
        FollowupItem("email_quote_day_2", "quotes", "Email on day 2", "email", False, True),
        FollowupItem("email_quote_day_5", "quotes", "Email on day 5", "email", False, True),
        FollowupItem("email_quote_day_10", "quotes", "Email on day 10", "email", False, True),
        FollowupItem("tap_done", "done", f"Tap to text when a {job} is done", "tap", False, True),
        FollowupItem("email_review", "done", "Email a review request", "email", False, True),
        FollowupItem("tap_upcoming", "reminders", f"Tap to text an upcoming {job}", "tap", False, True),
        FollowupItem("email_day_before", "reminders", "Email the day before", "email", False, True),
        FollowupItem("email_morning", "reminders", "Email the morning of", "email", False, True),
        FollowupItem("texting_addon", "texting", "Automatic texting", "addon", False, False),
        FollowupItem("sms_missed_call", "texting", "Missed-call text-back", "sms", True, True),
        FollowupItem("sms_quote_day_2", "texting", "Text an open quote on day 2", "sms", True, True),
        FollowupItem("sms_quote_day_5", "texting", "Text an open quote on day 5", "sms", True, True),
        FollowupItem("sms_quote_day_10", "texting", "Text an open quote on day 10", "sms", True, True),
        FollowupItem("sms_review", "texting", "Text a review request when the job is done", "sms", True, True),
        FollowupItem("sms_day_before", "texting", "Text the day before", "sms", True, True),
        FollowupItem("sms_morning", "texting", "Text the morning of", "sms", True, True),
        FollowupItem("two_way", "texting", "Two-way texting on the customer", "inbox", True, False),
    )
    intros = {
        "quotes": f"Open {quote}s the customer has seen and has not signed.",
        "done": f"When a {job} is marked done.",
        "reminders": f"The day before a {job}, and the morning of.",
        "texting": "Automatic texting is a paid add-on and stays in test mode. Nothing texts until this is on.",
    }
    titles = {
        "quotes": "Quotes",
        "done": "Jobs done / reviews",
        "reminders": "Reminders",
        "texting": "Texting",
    }
    groups = []
    for group_id in ("quotes", "done", "reminders", "texting"):
        groups.append(
            FollowupGroup(
                id=group_id,
                title=titles[group_id],
                intro=intros[group_id],
                items=tuple(item for item in items if item.group == group_id),
            )
        )
    return groups


def all_items(wording: TradeWording) -> tuple:
    found = []
    for group in catalog(wording):
        found.extend(group.items)
    return tuple(found)


def default_settings(wording: TradeWording, shop_name: str) -> ShopSettings:
    messages = default_messages(wording)
    switches = {item.key: False for item in all_items(wording)}
    return ShopSettings(
        switches=switches,
        messages=messages,
        google_review_url="",
        forward_to="",
        shop_name=shop_name,
    )


def item_label(wording: TradeWording, key: str) -> str:
    for item in all_items(wording):
        if item.key == key:
            return item.label
    return key
