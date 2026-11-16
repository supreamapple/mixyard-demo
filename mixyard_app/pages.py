from html import escape

from followups.render import quantity_text


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    body {{ margin:0; background:#F4F6F9; color:#2A3E6C; font-family:'Open Sans',system-ui,sans-serif; }}
    main {{ max-width:32rem; margin:0 auto; padding:24px 16px 48px; }}
    .brand {{ font-family:'Bebas Neue',sans-serif; letter-spacing:.04em; font-size:2rem; line-height:1; }}
    .kicker {{ color:#60CBB1; font-size:11px; letter-spacing:.14em; text-transform:uppercase; font-weight:700; }}
    h1 {{ font-family:'Bebas Neue',sans-serif; letter-spacing:.04em; font-size:2.6rem; margin:8px 0; font-weight:400; }}
    .card {{ background:#fff; border:1px solid rgba(42,62,108,.1); border-radius:16px; padding:16px; }}
    .muted {{ color:#5B6B86; }}
    .row {{ display:flex; justify-content:space-between; gap:12px; padding:8px 0; border-top:1px solid rgba(42,62,108,.08); }}
    label {{ display:block; font-weight:700; font-size:14px; margin-top:14px; }}
    input {{ width:100%; box-sizing:border-box; margin-top:6px; border:1px solid rgba(42,62,108,.15); border-radius:12px; padding:12px; font:inherit; }}
    button {{ margin-top:16px; width:100%; min-height:48px; border:0; border-radius:12px; background:#02AA13; color:#fff; font-weight:700; font-size:16px; }}
    .nza {{ color:#02AA13; }}
  </style>
</head>
<body>
<main>
  <div class="kicker">Specialty Concrete</div>
  <div class="brand">MixYard</div>
  {body}
</main>
</body>
</html>"""


def quote_page(quote, party, shop_name: str, error: str = "") -> str:
    amount = f"${quote.amount_cents / 100:,.2f}"
    signed = quote.status == "signed"
    heading = "Quote signed" if signed else "Review and sign"
    detail = escape(quote.detail)
    who = escape(party.name if party else "")
    lines = f"""
    <h1>{heading}</h1>
    <p class="muted">From {escape(shop_name)} for {who}.</p>
    <section class="card">
      <div class="row"><span>Pour</span><strong>{escape(quantity_text(quote.quantity))} yards · {detail}</strong></div>
      <div class="row"><span>Jobsite</span><strong>{escape(quote.address or "—")}</strong></div>
      <div class="row"><span>Total</span><strong>{amount}</strong></div>
      {"<div class='row'><span>Signed</span><strong>" + escape(quote.signer_name or who) + "</strong></div>" if signed else ""}
    </section>
    """
    if signed:
        lines += "<p>Thank you. The yard has the signature.</p>"
    elif quote.status != "open":
        lines += "<p>This quote is not ready to sign yet.</p>"
    else:
        err = f"<p>{escape(error)}</p>" if error else ""
        lines += f"""
        {err}
        <form method="post">
          <label>Your name<input name="name" required autocomplete="name" value="{escape(party.name if party else "")}" /></label>
          <button type="submit">Sign quote</button>
        </form>
        """
    return _page("Quote · MixYard", lines)


def unsub_page(shop_name: str) -> str:
    body = f"""
    <h1>Unsubscribed</h1>
    <p>You will not get follow-up emails from {escape(shop_name)}. A text from the yard is separate. Reply STOP to those.</p>
    """
    return _page("Unsubscribed · MixYard", body)


def missing_page() -> str:
    return _page("MixYard", "<h1>Not found</h1><p class='muted'>That link is not on this yard.</p>")
