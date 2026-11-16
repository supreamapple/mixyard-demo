import re

TOKEN = re.compile(r"\{([a-z_]+)\}")


def render_message(template: str, ctx: dict) -> str:
    def sub(match):
        key = match.group(1)
        value = ctx.get(key)
        if value is None or value == "":
            return match.group(0)
        return str(value)

    return TOKEN.sub(sub, template or "")


def first_name(name: str) -> str:
    parts = (name or "").split()
    return parts[0] if parts else "there"


def quantity_text(value) -> str:
    number = float(value or 0)
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


def with_email_footer(body: str, unsub_url: str) -> str:
    if unsub_url and unsub_url in body:
        return body
    line = "If you would rather not get these emails, use this link: " + unsub_url
    return (body or "").rstrip() + "\n\n" + line


def with_sms_footer(body: str) -> str:
    if "stop" in (body or "").lower():
        return body
    return (body or "").rstrip() + "\nReply STOP to opt out."
