import base64
import hmac
from hashlib import sha1


def twilio_signature(auth_token: str, url: str, params: dict) -> str:
    payload = url + "".join(key + params[key] for key in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def signature_matches(auth_token: str, url: str, params: dict, offered: str) -> bool:
    if not auth_token or not offered:
        return False
    expected = twilio_signature(auth_token, url, params)
    return hmac.compare_digest(expected, offered)
