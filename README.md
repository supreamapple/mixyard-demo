# MixYard · Specialty Concrete

Open `index.html` or the Vercel URL. Sample files:
- `sample-contacts.csv` — upload on Contacts
- `sample-receipt-pts.txt` — upload on Vendors or Fleet

## Everything Claude Code (Cursor)

Opening this repo in Cursor loads the [Everything Claude Code](https://github.com/affaan-m/ECC) (ECC) Cursor adapter from `.cursor/` (rules, skills, agents, and commands).

- Credit: Affaan Mustafa / ECC, MIT License. Official source only: https://github.com/affaan-m/ECC
- Installed with the official installer: `./install.sh --profile minimal --target cursor --no-hooks`
- Revision: ECC v2.2.2 (`e482e579415fde18357cafce70f177ae19fd7f03`)
- Hooks are off. The minimal profile does not ship the hooks-runtime and hook scripts Cursor hooks need, so the install uses `--no-hooks` and does not write a Cursor hooks runtime.
- Only the project adapter is installed under `.cursor/`. The ECC monorepo is not vendored here.

### Update

Shallow-clone the official repo, then re-run the installer with this repository as the working directory:

```bash
git clone --depth 1 https://github.com/affaan-m/ECC.git /tmp/ecc-src
/tmp/ecc-src/install.sh --profile minimal --target cursor --no-hooks
rm -rf /tmp/ecc-src
```

Do not commit the temporary clone or its `node_modules`.
