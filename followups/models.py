from dataclasses import dataclass
from datetime import datetime


@dataclass
class Party:
    id: str
    name: str
    email: str
    phone: str
    email_opt_out: bool
    sms_opt_out: bool
    do_not_contact: bool
    unsub_token: str


@dataclass
class Quote:
    id: str
    party_id: str
    quantity: float
    detail: str
    address: str
    amount_cents: int
    status: str
    sent_at: datetime | None
    viewed_at: datetime | None
    signed_at: datetime | None
    token: str
    signer_name: str


@dataclass
class Job:
    id: str
    party_id: str
    ticket_no: str
    quantity: float
    address: str
    scheduled_at: datetime
    status: str
    completed_at: datetime | None
    notes: str
    source: str


@dataclass
class ShopSettings:
    switches: dict
    messages: dict
    google_review_url: str
    forward_to: str
    shop_name: str


@dataclass(frozen=True)
class Planned:
    nudge_key: str
    channel: str
    subject_key: str
    party_id: str
    quote_id: str
    job_id: str
    subject: str
    body: str
