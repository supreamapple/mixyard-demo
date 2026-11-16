# MixYard · Specialty Concrete

Yard ops app for Specialty Concrete (Kelso / Longview). Contacts, tickets, vendors, yard levels, fleet, calendar, quote, and a QuickBooks sandbox pull.

## Open in Cursor

1. File → Clone Git Repository
2. `https://github.com/supreamapple/mixyard-demo`
3. Open the folder. All source is in the root.

## Run

```bash
python3 -m mixyard_app
```

Then open http://localhost:8080. The server binds `0.0.0.0` and `$PORT` (8080 when unset).

## Files

- `index.html` — shell, Tailwind, styles
- `app.js` — full app (board, contacts, vendors, tickets, books, yard, fleet, calendar, quote)
- `sample-contacts.csv` — upload on Contacts
- `sample-receipt-pts.txt` — paste or upload on Vendors

Data stays in the browser (`localStorage` key `mixyard.specialty.v3`) until you hit Reset demo.

## Features in this source

- Contacts with phone, company, notes, jobsites
- Never do business with (red card, Do not book, blocked from new tickets)
- CSV contact upload
- Vendors + receipt catalog (paste or file; pulls company, invoice, total)
- Tickets with last-year jobsite chips
- Yard fill for cement, sand, and rock separately
- Books tab: sandbox QuickBooks connect + pull history

Live Intuit needs a server and Client ID / Secret. Do not put those in this frontend.
