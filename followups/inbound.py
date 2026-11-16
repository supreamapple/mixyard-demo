import re
from urllib.parse import quote

STOP_WORDS = {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if digits:
        return "+" + digits
    return ""


def fictional_phone(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return len(digits) == 10 and digits[3:6] == "555"


def classify_sms(body: str) -> str:
    token = (body or "").strip().upper()
    if token in STOP_WORDS:
        return "stop"
    return "reply"


def sms_href(phone: str, body: str) -> str:
    number = normalize_phone(phone)
    if not number:
        return ""
    return "sms:" + number + "?body=" + quote(body, safe="")
