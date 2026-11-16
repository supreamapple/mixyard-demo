"""Trade-neutral customer follow-ups.

Pass a TradeWording. Mix Yard uses pour and yards. Another trade passes its own
words and reuses the planner, templates, opt-out rules, and send gate.
"""

from followups.catalog import catalog, default_messages, default_settings
from followups.inbound import classify_sms, fictional_phone, normalize_phone
from followups.plan import plan
from followups.wording import TradeWording, concrete_wording

__all__ = [
    "TradeWording",
    "catalog",
    "classify_sms",
    "concrete_wording",
    "default_messages",
    "default_settings",
    "fictional_phone",
    "normalize_phone",
    "plan",
]
