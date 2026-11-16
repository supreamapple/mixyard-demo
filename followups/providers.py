import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from followups.inbound import fictional_phone

DEFAULT_FROM = "Specialty Concrete <support@themixyard.com>"


@dataclass(frozen=True)
class SendResult:
    status: str
    detail: str


def test_mode() -> bool:
    return os.environ.get("TWILIO_MODE", "test").strip().lower() == "test"


def _urlopen(method, url, headers, data, timeout=10):
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def demo_email(address: str) -> bool:
    host = (address or "").split("@")[-1].lower()
    return host == "example" or host.endswith(".example") or host == "example.com" or host.endswith(".test")


class ResendEmail:
    def __init__(self, api_key=None, from_addr=None, transport=None):
        self.api_key = api_key if api_key is not None else os.environ.get("RESEND_API_KEY", "")
        self.from_addr = from_addr or os.environ.get("RESEND_FROM") or DEFAULT_FROM
        self.transport = transport or _urlopen

    def send(self, to_addr: str, subject: str, body: str) -> SendResult:
        if not (to_addr or "").strip():
            return SendResult("failed", "no email")
        if demo_email(to_addr):
            return SendResult("stubbed", "demo address")
        if not self.api_key:
            return SendResult("stubbed", "mail key not set")
        payload = json.dumps({"from": self.from_addr, "to": [to_addr], "subject": subject, "text": body}).encode()
        status, _text = self.transport(
            "POST",
            "https://api.resend.com/emails",
            {"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
            payload,
        )
        if 200 <= status < 300:
            return SendResult("sent", "email sent")
        return SendResult("failed", "mail rejected the message")


class TwilioSms:
    """Test mode only. Live sending is refused. No phone number is stored in code."""

    def __init__(self, account_sid=None, auth_token=None, from_number=None, transport=None):
        self.account_sid = account_sid if account_sid is not None else os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = auth_token if auth_token is not None else os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.from_number = from_number if from_number is not None else os.environ.get("TWILIO_FROM_NUMBER", "")
        self.transport = transport or _urlopen

    def send(self, to_number: str, body: str) -> SendResult:
        if not test_mode():
            return SendResult("blocked", "test mode only")
        if fictional_phone(to_number):
            return SendResult("stubbed", "demo number")
        if not (self.account_sid and self.auth_token and self.from_number):
            return SendResult("stubbed", "texting keys not set")
        form = urllib.parse.urlencode({"To": to_number, "From": self.from_number, "Body": body}).encode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        status, _text = self.transport(
            "POST",
            url,
            {"Authorization": _basic(self.account_sid, self.auth_token), "Content-Type": "application/x-www-form-urlencoded"},
            form,
        )
        if 200 <= status < 300:
            return SendResult("sent", "text sent")
        return SendResult("failed", "texting rejected the message")


def _basic(account_sid: str, auth_token: str) -> str:
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    return "Basic " + token
