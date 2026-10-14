const KEY = 'mixyard.specialty.v3';
const TZ = 'America/Los_Angeles';
const $ = (sel, el = document) => el.querySelector(sel);
const uid = (p = 'id') => p + '_' + Math.random().toString(36).slice(2, 8);
const nowIso = () => new Date().toISOString();
const go = (h) => { location.hash = h.startsWith('#') ? h.slice(1) : h; };
function fmtTime(iso) { return new Date(iso).toLocaleTimeString('en-US', { timeZone: TZ, hour: 'numeric', minute: '2-digit' }); }
function fmtDate(iso) { return new Date(iso).toLocaleDateString('en-US', { timeZone: TZ, weekday: 'short', month: 'short', day: 'numeric' }); }
function isToday(iso) { return new Date(iso).toLocaleDateString('en-CA', { timeZone: TZ }) === new Date().toLocaleDateString('en-CA', { timeZone: TZ }); }
function withinYear(iso) { return Date.now() - new Date(iso).getTime() <= 365 * 24 * 3600 * 1000; }
function addr(s) { return [s.line1, s.line2, [s.city, s.state].filter(Boolean).join(', '), s.zip].filter(Boolean).join(', '); }
function escapeHtml(s) { return String(s ?? '').replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>'); }
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, '"'); }
function money(n) { return Number.isFinite(+n) ? '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'; }
const STATUS = { scheduled: 'Scheduled', en_route: 'En route', pouring: 'Pouring', complete: 'Complete', cancelled: 'Cancelled' };
const SCLASS = { scheduled: 'bg-navy/10 text-navy', en_route: 'bg-amber-100 text-amber-800', pouring: 'bg-kelly/15 text-kelly', complete: 'bg-mint/25 text-navy', cancelled: 'bg-rose-100 text-rose-700' };

function seed() {
  const at = (h, m) => { const d = new Date(); d.setHours(h, m, 0, 0); return d.toISOString(); };
  return {
    contacts: [
      { id: 'ct_river', name: 'Dana Ellison', company: 'River Bend Homes', phones: [{ id: 'ph1', label: 'Mobile', number: '(360) 555-0142' }], notes: 'Prefers morning pours. Gate code 4412.', banned: false, createdAt: '2026-02-11T16:00:00.000Z' },
      { id: 'ct_cedar', name: 'Tom Bricker', company: 'Bricker Construction', phones: [{ id: 'ph3', label: 'Mobile', number: '(360) 555-0198' }], notes: 'Usually prevailing wage on city work.', banned: false, createdAt: '2025-11-02T16:00:00.000Z' },
      { id: 'ct_patel', name: 'Priya Patel', company: '', phones: [{ id: 'ph4', label: 'Home', number: '(360) 555-0117' }], notes: 'Residential. Dog in backyard.', banned: false, createdAt: '2026-04-03T16:00:00.000Z' },
      { id: 'ct_bad', name: 'Skip Pay Co', company: 'Skip Pay Co', phones: [{ id: 'ph9', label: 'Office', number: '(360) 555-0000' }], notes: 'Unpaid 2025. Do not book.', banned: true, createdAt: '2025-03-01T16:00:00.000Z' }
    ],
    jobsites: [
      { id: 'js_river1', contactId: 'ct_river', label: 'River lot 12', line1: '88 River Rd', line2: '', city: 'Longview', state: 'WA', zip: '98632', lastUsedAt: at(7, 30) },
      { id: 'js_river2', contactId: 'ct_river', label: 'Shop slab', line1: '410 Industrial Way', line2: 'Bldg C', city: 'Kelso', state: 'WA', zip: '98626', lastUsedAt: '2026-06-18T16:00:00.000Z' },
      { id: 'js_cedar1', contactId: 'ct_cedar', label: 'Cedar Ave duplex', line1: '1847 Cedar Ave', line2: '', city: 'Longview', state: 'WA', zip: '98632', lastUsedAt: at(10, 0) },
      { id: 'js_patel1', contactId: 'ct_patel', label: 'Home driveway', line1: '912 17th Ave', line2: '', city: 'Longview', state: 'WA', zip: '98632', lastUsedAt: '2026-07-22T16:00:00.000Z' }
    ],
    pours: [
      { id: 'pr_1', ticketNo: 'SC-260827-11', contactId: 'ct_river', jobsiteId: 'js_river1', address: '88 River Rd, Longview, WA 98632', truckId: 'trk_1', driverId: 'drv_mike', yards: 7.5, psi: 4000, scheduledAt: at(7, 30), status: 'en_route', notes: 'Footings + stem. Gate code 4412.' },
      { id: 'pr_2', ticketNo: 'SC-260827-12', contactId: 'ct_cedar', jobsiteId: 'js_cedar1', address: '1847 Cedar Ave, Longview, WA 98632', truckId: 'trk_2', driverId: 'drv_jess', yards: 4, psi: 3500, scheduledAt: at(10, 0), status: 'scheduled', notes: '' },
      { id: 'pr_3', ticketNo: 'SC-260827-13', contactId: 'ct_patel', jobsiteId: 'js_patel1', address: '912 17th Ave, Longview, WA 98632', truckId: 'trk_3', driverId: 'drv_cole', yards: 2.5, psi: 3000, scheduledAt: at(13, 30), status: 'scheduled', notes: 'Call on approach — dog in yard.' }
    ],
    trucks: [
      { id: 'trk_1', name: 'Volumetric 1', unit: 'V-1', defaultDriverId: 'drv_mike' },
      { id: 'trk_2', name: 'Volumetric 2', unit: 'V-2', defaultDriverId: 'drv_jess' },
      { id: 'trk_3', name: 'Volumetric 3', unit: 'V-3', defaultDriverId: 'drv_cole' }
    ],
    drivers: [{ id: 'drv_mike', name: 'Mike Harlan' }, { id: 'drv_jess', name: 'Jess Ortega' }, { id: 'drv_cole', name: 'Cole Vitus' }],
    materials: [
      { kind: 'cement', label: 'Cement', unit: 'sacks', yardQty: 180, capacity: 240, qtyPerYard: 6 },
      { kind: 'sand', label: 'Sand', unit: 't', yardQty: 40, capacity: 200, qtyPerYard: 0.45 },
      { kind: 'rock', label: 'Rock', unit: 't', yardQty: 95, capacity: 220, qtyPerYard: 0.85 }
    ],
    mixPrices: { 2500: 168, 3000: 178, 3500: 188, 4000: 198, 4500: 214, 5000: 228 },
    vendors: [
      { id: 'vn_pts', name: 'Pacific Truck Service', phone: '(360) 577-4100', notes: 'Mack / volumetric service.' },
      { id: 'vn_rh', name: 'River Hydraulics', phone: '(360) 425-8802', notes: 'PTO and chute hydraulics.' },
      { id: 'vn_cci', name: 'Cowlitz Commercial Inspection', phone: '(360) 577-2218', notes: 'DOT / annuals.' }
    ],
    receipts: [
      { id: 'rc_1', vendorId: 'vn_pts', truckId: 'trk_1', title: 'V-1 90-day service', date: '2026-08-12', amount: 1840.22, invoice: 'PTS-88421', notes: 'Oil, filters, chute bushings.', text: 'PACIFIC TRUCK SERVICE\nInvoice PTS-88421\nUnit V-1\nTotal $1,840.22' }
    ],
    qbo: { connected: false, companyName: '', realmId: '', lastPullAt: '', log: [] },
    qboInvoices: []
  };
}
function load() {
  try {
    const r = JSON.parse(localStorage.getItem(KEY) || '');
    if (r && r.contacts && r.pours) return r;
  } catch (e) {}
  return seed();
}
let S = load();
function persist() { localStorage.setItem(KEY, JSON.stringify(S)); render(); }
function resetDemo() { S = seed(); persist(); }
function contactBy(id) { return S.contacts.find((c) => c.id === id); }
function vendorBy(id) { return S.vendors.find((v) => v.id === id); }
function truckBy(id) { return S.trucks.find((t) => t.id === id); }
function driverBy(id) { return S.drivers.find((d) => d.id === id); }

function saveContact(c) {
  const existing = c.id && S.contacts.find((x) => x.id === c.id);
  const row = {
    id: existing ? existing.id : uid('ct'),
    name: (c.name || '').trim(),
    company: (c.company || '').trim(),
    phones: (c.phones || []).filter((p) => p.number && p.number.trim()),
    notes: (c.notes || '').trim(),
    banned: !!c.banned,
    createdAt: existing ? existing.createdAt : nowIso()
  };
  S.contacts = existing ? S.contacts.map((x) => x.id === row.id ? row : x) : [row, ...S.contacts];
  persist(); return row;
}
function deleteContact(id) {
  S.contacts = S.contacts.filter((c) => c.id !== id);
  S.jobsites = S.jobsites.filter((j) => j.contactId !== id);
  persist();
}
function saveJobsite(j) {
  const row = { id: j.id || uid('js'), contactId: j.contactId, label: (j.label || '').trim(), line1: (j.line1 || '').trim(), line2: (j.line2 || '').trim(), city: (j.city || '').trim(), state: (j.state || 'WA').trim(), zip: (j.zip || '').trim(), lastUsedAt: j.lastUsedAt || nowIso() };
  S.jobsites = j.id ? S.jobsites.map((x) => x.id === j.id ? row : x) : [row, ...S.jobsites];
  persist(); return row;
}
function recentSites(cid) { return S.jobsites.filter((j) => j.contactId === cid && withinYear(j.lastUsedAt)).sort((a, b) => +new Date(b.lastUsedAt) - +new Date(a.lastUsedAt)); }
function saveVendor(v) {
  const existing = v.id && S.vendors.find((x) => x.id === v.id);
  const row = { id: existing ? existing.id : uid('vn'), name: v.name.trim(), phone: (v.phone || '').trim(), notes: (v.notes || '').trim() };
  S.vendors = existing ? S.vendors.map((x) => x.id === row.id ? row : x) : [row, ...S.vendors];
  persist(); return row;
}
function findOrCreateVendor(name) {
  const n = (name || '').trim();
  if (!n) return null;
  const hit = S.vendors.find((v) => v.name.toLowerCase() === n.toLowerCase());
  if (hit) return hit;
  return saveVendor({ name: n, phone: '', notes: 'Added from an upload.' });
}
function saveReceipt(r) {
  const row = { id: r.id || uid('rc'), vendorId: r.vendorId || '', truckId: r.truckId || '', title: (r.title || '').trim() || 'Service receipt', date: r.date || new Date().toLocaleDateString('en-CA'), amount: r.amount === '' || r.amount == null ? null : Number(r.amount), invoice: (r.invoice || '').trim(), notes: (r.notes || '').trim(), text: r.text || '' };
  S.receipts = r.id ? S.receipts.map((x) => x.id === r.id ? row : x) : [row, ...S.receipts];
  persist(); return row;
}
function fillYard(kind) { S.materials = S.materials.map((m) => (!kind || m.kind === kind) ? { ...m, yardQty: m.capacity } : m); persist(); }
function savePour(input) {
  const existing = input.id && S.pours.find((p) => p.id === input.id);
  const contact = contactBy(input.contactId || existing?.contactId);
  if (contact?.banned && !existing) { alert(contact.name + ' is marked Never do business with. Cannot book a new ticket.'); return null; }
  let address = input.address || existing?.address || '';
  if (input.jobsiteId) { const site = S.jobsites.find((j) => j.id === input.jobsiteId); if (site) address = addr(site); }
  const row = {
    id: existing ? existing.id : uid('pr'),
    ticketNo: existing ? existing.ticketNo : 'SC-' + new Date().toLocaleDateString('en-CA', { timeZone: TZ }).replaceAll('-', '').slice(2) + '-' + Math.floor(Math.random() * 90 + 10),
    contactId: input.contactId ?? existing?.contactId ?? '',
    jobsiteId: input.jobsiteId ?? existing?.jobsiteId ?? '',
    address, truckId: input.truckId || existing?.truckId || S.trucks[0]?.id || '',
    driverId: input.driverId || existing?.driverId || '',
    yards: Number(input.yards ?? existing?.yards ?? 1), psi: Number(input.psi ?? existing?.psi ?? 4000),
    scheduledAt: input.scheduledAt || existing?.scheduledAt || nowIso(),
    status: input.status || existing?.status || 'scheduled',
    notes: input.notes ?? existing?.notes ?? ''
  };
  if (row.jobsiteId) S.jobsites = S.jobsites.map((j) => j.id === row.jobsiteId ? { ...j, lastUsedAt: nowIso() } : j);
  S.pours = existing ? S.pours.map((p) => p.id === row.id ? row : p) : [row, ...S.pours];
  persist(); return row;
}
function setStatus(id, status) { S.pours = S.pours.map((p) => p.id === id ? { ...p, status } : p); persist(); }

const KNOWN_SHOPS = ['Pacific Truck Service', 'River Hydraulics', 'Cowlitz Commercial Inspection', 'Mack Northwest', 'DrumTech Northwest', 'CalPortland'];
function parseMoney(text) { const m = String(text).match(/\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+\.[0-9]{2})/g); if (!m) return null; const nums = m.map((s) => Number(s.replace(/[$,\s]/g, ''))).filter((n) => n > 0); return nums.length ? Math.max(...nums) : null; }
function parseDate(text) { const m = String(text).match(/\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b/); if (!m) return ''; const y = m[3].length === 2 ? '20' + m[3] : m[3]; return y + '-' + String(m[1]).padStart(2, '0') + '-' + String(m[2]).padStart(2, '0'); }
function parseInvoice(text) { const m = String(text).match(/\b(?:invoice|inv|ticket|#)\s*[:#\-]?\s*([A-Z]{0,6}-?\d{3,})/i); return m ? m[1] : ''; }
function parseVendorName(text, fileName) { const blob = (fileName || '') + '\n' + (text || ''); const known = KNOWN_SHOPS.concat(S.vendors.map((v) => v.name)); const hit = known.find((n) => blob.toLowerCase().includes(n.toLowerCase())); if (hit) return hit; const lines = String(text || '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean); return lines.find((l) => /\b(llc|inc|service|hydraulics|truck|shop)\b/i.test(l)) || ''; }
function parseReceiptText(text, fileName) { return { vendorName: parseVendorName(text, fileName), amount: parseMoney(text), date: parseDate(text), invoice: parseInvoice(text), title: (fileName || 'Service receipt').replace(/\.[a-z0-9]+$/i, '') }; }
function splitCsvLine(line) { const out = []; let cur = ''; let q = false; for (let i = 0; i < line.length; i++) { const ch = line[i]; if (ch === '"') { if (q && line[i + 1] === '"') { cur += '"'; i++; } else q = !q; } else if (ch === ',' && !q) { out.push(cur); cur = ''; } else cur += ch; } out.push(cur); return out.map((s) => s.trim()); }
function parseContactCsv(text) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (!lines.length) return [];
  const head = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  const idx = (names) => names.reduce((f, n) => (f >= 0 ? f : head.findIndex((h) => h.includes(n))), -1);
  const iName = idx(['name', 'contact']), iCo = idx(['company', 'org']), iPhone = idx(['phone', 'mobile', 'tel']), iNotes = idx(['note']);
  const start = iName >= 0 || iCo >= 0 ? 1 : 0;
  return lines.slice(start).map((line) => { const cols = splitCsvLine(line); const name = (iName >= 0 ? cols[iName] : cols[0] || '').trim(); const company = (iCo >= 0 ? cols[iCo] : cols[1] || '').trim(); return { name: name || company, company, phone: (iPhone >= 0 ? cols[iPhone] : cols[2] || '').trim(), notes: (iNotes >= 0 ? cols[iNotes] : cols[3] || '').trim() }; }).filter((r) => r.name);
}
function importContacts(rows) {
  let added = 0, updated = 0;
  rows.forEach((row) => {
    const hit = S.contacts.find((c) => c.name.toLowerCase() === row.name.toLowerCase());
    saveContact({ id: hit?.id, name: row.name, company: row.company || hit?.company || '', phones: row.phone ? [{ id: uid('ph'), label: 'Mobile', number: row.phone }] : (hit?.phones || []), notes: [hit?.notes, row.notes].filter(Boolean).join(' '), banned: !!hit?.banned });
    hit ? updated++ : added++;
  });
  return { added, updated };
}

function parseRoute() {
  const raw = (location.hash || '#/').replace(/^#/, '') || '/';
  const [path, qs] = raw.split('?');
  const q = new URLSearchParams(qs || '');
  if (path === '/contacts/new') return { name: 'contact-new' };
  if (path.startsWith('/contacts/') && path !== '/contacts/') return { name: 'contact', id: path.slice(10) };
  if (path === '/contacts') return { name: 'contacts' };
  if (path === '/vendors/new') return { name: 'vendor-new' };
  if (path.startsWith('/vendors/') && path !== '/vendors/') return { name: 'vendor', id: path.slice(9) };
  if (path === '/vendors') return { name: 'vendors' };
  if (path === '/tickets/new') return { name: 'ticket-new', contactId: q.get('contact') || '' };
  if (path.endsWith('/edit') && path.startsWith('/tickets/')) return { name: 'ticket-edit', id: path.slice(9, -5) };
  if (path.startsWith('/tickets/') && path !== '/tickets/') return { name: 'ticket', id: path.slice(9) };
  if (path === '/tickets') return { name: 'tickets' };
  if (path === '/books') return { name: 'books' };
  if (path === '/yard') return { name: 'yard' };
  if (path === '/fleet') return { name: 'fleet' };
  if (path === '/calendar') return { name: 'calendar' };
  if (path === '/quote') return { name: 'quote' };
  return { name: 'dashboard' };
}

function layout(active, inner) {
  const nav = [['/', 'Board', 'dashboard'], ['/contacts', 'Contacts', 'contact'], ['/vendors', 'Vendors', 'vendor'], ['/tickets', 'Tickets', 'ticket'], ['/books', 'Books', 'books'], ['/yard', 'Yard', 'yard'], ['/fleet', 'Fleet', 'fleet'], ['/calendar', 'Calendar', 'calendar'], ['/quote', 'Quote', 'quote']];
  return `<header class="sticky top-0 z-40 bg-navy text-white">
    <div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
      <button data-go="/" class="text-left"><div class="font-display text-2xl leading-none">MixYard</div><div class="text-[11px] uppercase tracking-widest text-mint">Specialty Concrete</div></button>
      <button data-reset class="text-xs text-white/70">Reset demo</button>
    </div>
    <nav class="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-3 pb-3">
      ${nav.map(([h, l, m]) => `<button data-go="${h}" class="whitespace-nowrap rounded-full px-3 py-2 text-sm font-semibold ${active === m ? 'bg-kelly text-white' : 'bg-white/10 text-white'}">${l}</button>`).join('')}
    </nav></header><main class="mx-auto max-w-5xl px-4 py-5 pb-16">${inner}</main>`;
}

function pageDashboard() {
  const today = S.pours.filter((p) => isToday(p.scheduledAt) && p.status !== 'cancelled');
  const yards = today.reduce((s, p) => s + Number(p.yards || 0), 0);
  const rows = today.length ? today.map((p) => {
    const c = contactBy(p.contactId);
    return `<button data-go="/tickets/${p.id}" class="flex w-full items-center justify-between border-t border-navy/10 px-4 py-3 text-left">
      <div><div class="font-semibold">${escapeHtml(c?.name || 'No contact')} · ${p.yards} yd ${p.psi}</div><div class="text-sm text-slateish">${fmtTime(p.scheduledAt)} · ${escapeHtml(p.address)}</div></div>
      <span class="badge ${SCLASS[p.status]}">${STATUS[p.status]}</span></button>`;
  }).join('') : '<div class="px-4 py-4 text-sm text-slateish">No pours scheduled today.</div>';
  const plant = S.materials.map((m) => `<div class="flex justify-between text-sm"><span>${m.label}</span><span>${m.yardQty}/${m.capacity} ${m.unit}</span></div>`).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Specialty Concrete · Kelso yard</p><h1 class="font-display text-4xl">Today's board</h1>
    <section class="card mt-4">
      <div class="flex items-center justify-between px-4 py-3"><h2 class="font-display text-2xl">Pours</h2><button class="btn btn-p" data-go="/tickets/new">New ticket</button></div>
      ${rows}
    </section>
    <div class="mt-3 grid gap-3 sm:grid-cols-3">
      <section class="card p-4"><div class="text-xs font-semibold uppercase text-slateish">Yards today</div><div class="font-display text-4xl">${yards}</div></section>
      <section class="card p-4"><div class="text-xs font-semibold uppercase text-slateish">Trucks</div><div class="font-display text-4xl">${S.trucks.length}</div></section>
      <section class="card p-4"><div class="text-xs font-semibold uppercase text-slateish">Plant</div><div class="mt-1 space-y-1">${plant}</div></section>
    </div>`;
}

function pageContacts() {
  const q = (window._contactQ || '').toLowerCase();
  const list = S.contacts.filter((c) => !q || (c.name + ' ' + c.company + ' ' + (c.phones || []).map((p) => p.number).join(' ')).toLowerCase().includes(q));
  const cards = list.map((c) => {
    const sites = recentSites(c.id).length;
    return `<button data-go="/contacts/${c.id}" class="card w-full p-4 text-left ${c.banned ? 'banned' : ''}">
      <div class="flex items-start justify-between gap-2"><div class="font-semibold">${escapeHtml(c.name)}</div>${c.banned ? '<span class="badge bg-rose-100 text-rose-700">Do not book</span>' : `<span class="badge bg-navy/10 text-navy">${sites} sites</span>`}</div>
      <div class="text-sm text-slateish">${escapeHtml(c.company || 'No company on file')}</div>
      <div class="mt-1 text-sm">${escapeHtml(c.phones?.[0]?.number || 'No phone')}</div></button>`;
  }).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Customers</p><h1 class="font-display text-4xl">Contacts</h1>
    <p class="mt-1 text-sm text-slateish">Edit customers outside of a ticket. Banned contacts stay red and cannot be used on a new ticket.</p>
    <div class="mt-3 flex flex-wrap gap-2"><label class="btn btn-g cursor-pointer">Upload contacts<input id="contactfile" type="file" accept=".csv,.vcf,text/csv,text/vcard" class="hidden" /></label><button class="btn btn-p" data-go="/contacts/new">New contact</button></div>
    <p class="mt-2 text-xs text-slateish">CSV columns: name, company, phone, notes. Sample: sample-contacts.csv</p>
    <input id="contactq" class="field mt-3" placeholder="Search name, company, phone..." value="${escapeAttr(window._contactQ || '')}" />
    <div class="mt-3 grid gap-3">${cards || '<div class="text-sm text-slateish">No contacts.</div>'}</div>`;
}

function pageContact(c, isNew) {
  const phones = (c?.phones || [{ id: uid('ph'), label: 'Mobile', number: '' }]);
  const sites = c ? recentSites(c.id) : [];
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Contact</p><h1 class="font-display text-4xl">${isNew ? 'New contact' : escapeHtml(c.name)}</h1>
    <form id="contactform" class="card mt-4 space-y-3 p-4">
      <label class="block text-sm font-semibold">Name<input name="name" class="field mt-1" value="${escapeAttr(c?.name || '')}" required /></label>
      <label class="block text-sm font-semibold">Company<input name="company" class="field mt-1" value="${escapeAttr(c?.company || '')}" /></label>
      <label class="block text-sm font-semibold">Phone<input name="phone" class="field mt-1" value="${escapeAttr(phones[0]?.number || '')}" /></label>
      <label class="block text-sm font-semibold">Notes<textarea name="notes" class="field mt-1" rows="3">${escapeHtml(c?.notes || '')}</textarea></label>
      <label class="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" name="banned" ${c?.banned ? 'checked' : ''} /> Never do business with</label>
      <div class="flex gap-2"><button class="btn btn-p" type="submit">Save</button><button class="btn btn-g" type="button" data-go="/contacts">Cancel</button>${c ? `<button class="btn btn-d" type="button" id="delcontact">Delete</button>` : ''}</div>
    </form>
    ${c ? `<section class="card mt-3 p-4"><div class="flex items-center justify-between"><h2 class="font-display text-2xl">Jobsites</h2><button class="btn btn-g" data-go="/tickets/new?contact=${c.id}" ${c.banned ? 'disabled' : ''}>New ticket</button></div>
      <div class="mt-2 space-y-2">${sites.map((j) => `<div class="rounded-xl border border-navy/10 p-3 text-sm"><div class="font-semibold">${escapeHtml(j.label || j.line1)}</div><div>${escapeHtml(addr(j))}</div></div>`).join('') || '<div class="text-sm text-slateish">No sites in the last year.</div>'}</div></section>` : ''}`;
}

function pageVendors() {
  const cards = S.vendors.map((v) => {
    const recs = S.receipts.filter((r) => r.vendorId === v.id);
    const total = recs.reduce((s, r) => s + (Number(r.amount) || 0), 0);
    return `<button data-go="/vendors/${v.id}" class="card w-full p-4 text-left"><div class="flex items-start justify-between"><div class="font-semibold">${escapeHtml(v.name)}</div><span class="badge bg-navy/10 text-navy">${recs.length} receipt${recs.length === 1 ? '' : 's'}</span></div><div class="text-sm text-slateish">${escapeHtml(v.phone || '')}</div><div class="mt-1 text-sm">${money(total)} on file</div></button>`;
  }).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Shops · parts · service</p><h1 class="font-display text-4xl">Vendors</h1>
    <p class="mt-1 text-sm text-slateish">Drop a service receipt and MixYard pulls the company, invoice, and total.</p>
    <div class="mt-3 flex gap-2"><button class="btn btn-p" data-go="/vendors/new">New vendor</button></div>
    <section class="card mt-4 p-4"><h2 class="font-display text-2xl">Upload a receipt</h2>
      <p class="text-sm text-slateish">Paste invoice text, or choose a .txt / .csv file. Sample: sample-receipt-pts.txt</p>
      <label class="btn btn-g mt-3 cursor-pointer">Choose file<input id="receiptfile" type="file" accept=".txt,.csv,.pdf" class="hidden" /></label>
      <textarea id="receipttext" class="field mt-3" rows="5" placeholder="PACIFIC TRUCK SERVICE\nInvoice PTS-88421\nUnit V-1\nTotal $1,840.22"></textarea>
      <button class="btn btn-p mt-3" id="filereceipt">File pasted receipt</button></section>
    <div class="mt-3 grid gap-3">${cards}</div>`;
}
function pageVendor(v, isNew) {
  const recs = v ? S.receipts.filter((r) => r.vendorId === v.id) : [];
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Vendor</p><h1 class="font-display text-4xl">${isNew ? 'New vendor' : escapeHtml(v.name)}</h1>
    <form id="vendorform" class="card mt-4 space-y-3 p-4">
      <label class="block text-sm font-semibold">Name<input name="name" class="field mt-1" value="${escapeAttr(v?.name || '')}" required /></label>
      <label class="block text-sm font-semibold">Phone<input name="phone" class="field mt-1" value="${escapeAttr(v?.phone || '')}" /></label>
      <label class="block text-sm font-semibold">Notes<textarea name="notes" class="field mt-1" rows="2">${escapeHtml(v?.notes || '')}</textarea></label>
      <div class="flex gap-2"><button class="btn btn-p" type="submit">Save</button><button class="btn btn-g" type="button" data-go="/vendors">Back</button></div>
    </form>
    ${v ? `<section class="card mt-3 p-4"><h2 class="font-display text-2xl">Receipt catalog</h2><div class="mt-2 space-y-2">${recs.map((r) => `<div class="rounded-xl border border-navy/10 p-3 text-sm"><div class="font-semibold">${escapeHtml(r.title)} · ${money(r.amount)}</div><div class="text-slateish">${escapeHtml(r.date)} · ${escapeHtml(r.invoice || '')}</div></div>`).join('') || '<div class="text-sm text-slateish">No receipts yet.</div>'}</div></section>` : ''}`;
}

function pageTickets() {
  const rows = S.pours.map((p) => {
    const c = contactBy(p.contactId);
    return `<button data-go="/tickets/${p.id}" class="card w-full p-4 text-left"><div class="flex items-start justify-between"><div class="font-semibold">${escapeHtml(p.ticketNo)} · ${escapeHtml(c?.name || 'No contact')}</div><span class="badge ${SCLASS[p.status]}">${STATUS[p.status]}</span></div><div class="text-sm text-slateish">${fmtDate(p.scheduledAt)} ${fmtTime(p.scheduledAt)} · ${p.yards} yd ${p.psi}</div><div class="text-sm">${escapeHtml(p.address)}</div></button>`;
  }).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Pours</p><div class="flex items-end justify-between"><h1 class="font-display text-4xl">Tickets</h1><button class="btn btn-p" data-go="/tickets/new">New ticket</button></div><div class="mt-3 grid gap-3">${rows || '<div class="text-sm text-slateish">No tickets.</div>'}</div>`;
}
function pageTicket(p) {
  const c = contactBy(p.contactId);
  const truck = truckBy(p.truckId);
  const driver = driverBy(p.driverId);
  const next = [['scheduled', 'Schedule'], ['en_route', 'En route'], ['pouring', 'Pouring'], ['complete', 'Complete'], ['cancelled', 'Cancel']];
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">${escapeHtml(p.ticketNo)}</p><h1 class="font-display text-4xl">${escapeHtml(c?.name || 'Ticket')}</h1>
    <section class="card mt-4 p-4 text-sm space-y-1"><div><span class="badge ${SCLASS[p.status]}">${STATUS[p.status]}</span></div><div>${fmtDate(p.scheduledAt)} ${fmtTime(p.scheduledAt)}</div><div>${p.yards} yd · ${p.psi} PSI</div><div>${escapeHtml(p.address)}</div><div>${escapeHtml(truck?.unit || '')} · ${escapeHtml(driver?.name || '')}</div><div>${escapeHtml(p.notes || '')}</div></section>
    <div class="mt-3 flex flex-wrap gap-2">${next.map(([s, l]) => `<button class="btn ${s === p.status ? 'btn-n' : 'btn-g'}" data-status="${s}">${l}</button>`).join('')}<button class="btn btn-g" data-go="/tickets/${p.id}/edit">Edit</button></div>`;
}
function pageTicketForm(existing, presetContactId) {
  const bookable = S.contacts.filter((c) => !c.banned);
  const cid = existing?.contactId || presetContactId || '';
  const sites = cid ? recentSites(cid) : [];
  const when = existing?.scheduledAt ? new Date(existing.scheduledAt).toISOString().slice(0, 16) : '';
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Ticket</p><h1 class="font-display text-4xl">${existing ? 'Edit ticket' : 'New ticket'}</h1>
    <form id="ticketform" class="card mt-4 space-y-3 p-4">
      <label class="block text-sm font-semibold">Contact<select name="contactId" class="field mt-1">${bookable.map((c) => `<option value="${c.id}" ${c.id === cid ? 'selected' : ''}>${escapeHtml(c.name)}${c.company ? ' · ' + escapeHtml(c.company) : ''}</option>`).join('')}</select></label>
      <div id="sitechips" class="flex flex-wrap gap-2">${sites.map((j) => `<button type="button" class="badge bg-mint/30 text-navy" data-site="${j.id}" data-addr="${escapeAttr(addr(j))}">${escapeHtml(j.label || j.line1)}</button>`).join('')}</div>
      <input type="hidden" name="jobsiteId" value="${escapeAttr(existing?.jobsiteId || '')}" />
      <label class="block text-sm font-semibold">Address<input name="address" class="field mt-1" value="${escapeAttr(existing?.address || '')}" /></label>
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="block text-sm font-semibold">Yards<input name="yards" type="number" step="0.5" class="field mt-1" value="${existing?.yards || 4}" /></label>
        <label class="block text-sm font-semibold">PSI<select name="psi" class="field mt-1">${[2500, 3000, 3500, 4000, 4500, 5000].map((n) => `<option ${Number(existing?.psi || 4000) === n ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
      </div>
      <label class="block text-sm font-semibold">When<input name="scheduledAt" type="datetime-local" class="field mt-1" value="${when}" /></label>
      <label class="block text-sm font-semibold">Truck<select name="truckId" class="field mt-1">${S.trucks.map((t) => `<option value="${t.id}" ${t.id === existing?.truckId ? 'selected' : ''}>${escapeHtml(t.unit)} · ${escapeHtml(t.name)}</option>`).join('')}</select></label>
      <label class="block text-sm font-semibold">Notes<textarea name="notes" class="field mt-1" rows="2">${escapeHtml(existing?.notes || '')}</textarea></label>
      <div class="flex gap-2"><button class="btn btn-p" type="submit">Save ticket</button><button class="btn btn-g" type="button" data-go="/tickets">Cancel</button></div>
    </form>`;
}

function pageYard() {
  const rows = S.materials.map((m) => `<section class="card p-4"><div class="flex items-center justify-between"><div><div class="font-display text-2xl">${m.label}</div><div class="text-sm text-slateish">${m.yardQty} / ${m.capacity} ${m.unit}</div></div><button class="btn btn-p" data-fill="${m.kind}">Fill ${m.label.toLowerCase()}</button></div>
    <div class="mt-3 h-2 overflow-hidden rounded-full bg-navy/10"><div class="h-full bg-kelly" style="width:${Math.min(100, (m.yardQty / m.capacity) * 100)}%"></div></div></section>`).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Plant</p><h1 class="font-display text-4xl">Yard</h1><div class="mt-3 flex gap-2"><button class="btn btn-n" data-fill="">Fill all</button></div><div class="mt-3 grid gap-3">${rows}</div>`;
}
function pageFleet() {
  const rows = S.trucks.map((t) => `<section class="card p-4"><div class="font-display text-2xl">${escapeHtml(t.unit)}</div><div class="text-sm">${escapeHtml(t.name)}</div><div class="text-sm text-slateish">Driver: ${escapeHtml(driverBy(t.defaultDriverId)?.name || 'Unassigned')}</div></section>`).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Units</p><h1 class="font-display text-4xl">Fleet</h1><div class="mt-3 grid gap-3 sm:grid-cols-3">${rows}</div>`;
}
function pageCalendar() {
  const byDay = {};
  S.pours.forEach((p) => { const k = new Date(p.scheduledAt).toLocaleDateString('en-CA', { timeZone: TZ }); (byDay[k] = byDay[k] || []).push(p); });
  const days = Object.keys(byDay).sort();
  const rows = days.map((d) => `<section class="card p-4"><div class="font-semibold">${d}</div>${byDay[d].map((p) => `<button data-go="/tickets/${p.id}" class="mt-2 block w-full text-left text-sm">${fmtTime(p.scheduledAt)} · ${escapeHtml(contactBy(p.contactId)?.name || '')} · ${p.yards} yd</button>`).join('')}</section>`).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Schedule</p><h1 class="font-display text-4xl">Calendar</h1><div class="mt-3 grid gap-3">${rows || '<div class="text-sm text-slateish">No pours on the calendar.</div>'}</div>`;
}
function pageQuote() {
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Pricing</p><h1 class="font-display text-4xl">Quote</h1>
    <form id="quoteform" class="card mt-4 space-y-3 p-4">
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="block text-sm font-semibold">Yards<input name="yards" type="number" step="0.5" class="field mt-1" value="5" /></label>
        <label class="block text-sm font-semibold">PSI<select name="psi" class="field mt-1">${Object.keys(S.mixPrices).map((n) => `<option ${n === '4000' ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
      </div>
      <button class="btn btn-p" type="submit">Price</button>
      <div id="quoteout" class="font-display text-4xl"></div>
    </form>`;
}
function pageBooks() {
  const q = S.qbo || { connected: false, log: [] };
  const invoices = S.qboInvoices || [];
  const openAr = invoices.reduce((s, i) => s + (Number(i.balance) || 0), 0);
  const rows = (q.log || []).slice(0, 8).map((l) => `<li class="text-sm text-slateish">${escapeHtml(l.msg)}</li>`).join('') || '<li class="text-sm text-slateish">No syncs yet.</li>';
  const invRows = invoices.map((i) => `<tr class="border-t border-navy/10 text-sm"><td class="py-2 pr-3 font-semibold">${escapeHtml(i.ticketNo)}</td><td class="py-2 pr-3">${escapeHtml(i.date)}</td><td class="py-2 pr-3">${escapeHtml(i.customerName)}</td><td class="py-2 text-right">${money(i.balance)}</td></tr>`).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">QuickBooks Online</p><h1 class="font-display text-4xl">Books</h1>
    <p class="mt-1 text-sm text-slateish">Sandbox pull for customers, vendors, invoices, and bills. Live Intuit needs a Client ID / Secret on a server.</p>
    <section class="card mt-4 p-4"><div class="flex items-center justify-between gap-3"><div><div class="font-semibold">${q.connected ? 'Connected · ' + escapeHtml(q.companyName) : 'Not connected'}</div><div class="text-sm text-slateish">${q.connected ? 'Realm ' + escapeHtml(q.realmId) : 'Scope com.intuit.quickbooks.accounting'}</div></div>
      ${q.connected ? '<button class="btn btn-p" id="qbopull">Pull history</button>' : '<button class="btn btn-p" id="qboconnect">Connect QuickBooks</button>'}</div></section>
    <div class="mt-3 grid gap-3 sm:grid-cols-2"><section class="card p-4"><div class="text-xs uppercase text-slateish">Open AR</div><div class="font-display text-3xl">${money(openAr)}</div></section><section class="card p-4"><div class="text-xs uppercase text-slateish">Invoices pulled</div><div class="font-display text-3xl">${invoices.length}</div></section></div>
    <section class="card mt-3 overflow-x-auto p-4"><table class="w-full text-left"><thead><tr class="text-xs uppercase text-slateish"><th class="pb-2 pr-3">Doc</th><th class="pb-2 pr-3">Date</th><th class="pb-2 pr-3">Customer</th><th class="pb-2 text-right">Balance</th></tr></thead><tbody>${invRows || '<tr><td colspan="4" class="py-3 text-sm text-slateish">Pull history to load invoices.</td></tr>'}</tbody></table></section>
    <section class="card mt-3 p-4"><h2 class="font-display text-2xl">Sync log</h2><ul class="mt-2 space-y-1">${rows}</ul></section>`;
}

function connectQbo() {
  S.qbo = { connected: true, companyName: 'Specialty Concrete LLC', realmId: '934145981234', lastPullAt: '', log: [{ msg: 'Connected sandbox company Specialty Concrete LLC' }] };
  persist();
}
function pullQbo() {
  const customers = [
    { name: 'Longview School District', company: 'Longview School District', phone: '(360) 575-7000', notes: 'PO required. Open AR $0' },
    { name: 'Kelso Public Works', company: 'City of Kelso', phone: '(360) 423-5720', notes: 'Prevailing wage. Open AR $3,960.00' }
  ];
  customers.forEach((c) => {
    const hit = S.contacts.find((x) => x.name.toLowerCase() === c.name.toLowerCase());
    const row = saveContact({ id: hit?.id, name: c.name, company: c.company, phones: [{ id: uid('ph'), label: 'QBO', number: c.phone }], notes: c.notes, banned: !!hit?.banned });
    row.qboId = row.qboId || uid('qbo');
  });
  findOrCreateVendor('CalPortland — aggregate');
  S.qboInvoices = [
    { ticketNo: 'SC-260718-04', date: '2026-07-18', customerName: 'Dana Ellison', balance: 0 },
    { ticketNo: 'SC-260812-09', date: '2026-08-12', customerName: 'Dana Ellison', balance: 1485 },
    { ticketNo: 'SC-260415-11', date: '2026-04-15', customerName: 'Kelso Public Works', balance: 3960 }
  ];
  S.qbo.lastPullAt = nowIso();
  S.qbo.log = [{ msg: 'Pulled customers, vendors, invoices, and bills' }, ...(S.qbo.log || [])];
  persist();
}

function render() {
  const r = parseRoute();
  let active = r.name.startsWith('contact') ? 'contact' : r.name.startsWith('vendor') ? 'vendor' : r.name.startsWith('ticket') ? 'ticket' : r.name;
  let inner = '';
  if (r.name === 'contacts') inner = pageContacts();
  else if (r.name === 'contact-new') inner = pageContact(null, true);
  else if (r.name === 'contact') { const c = contactBy(r.id); inner = c ? pageContact(c) : pageContacts(); }
  else if (r.name === 'vendors') inner = pageVendors();
  else if (r.name === 'vendor-new') inner = pageVendor(null, true);
  else if (r.name === 'vendor') { const v = vendorBy(r.id); inner = v ? pageVendor(v) : pageVendors(); }
  else if (r.name === 'tickets') inner = pageTickets();
  else if (r.name === 'ticket-new') inner = pageTicketForm(null, r.contactId);
  else if (r.name === 'ticket') { const p = S.pours.find((x) => x.id === r.id); inner = p ? pageTicket(p) : pageTickets(); }
  else if (r.name === 'ticket-edit') { const p = S.pours.find((x) => x.id === r.id); inner = p ? pageTicketForm(p) : pageTickets(); }
  else if (r.name === 'books') inner = pageBooks();
  else if (r.name === 'yard') inner = pageYard();
  else if (r.name === 'fleet') inner = pageFleet();
  else if (r.name === 'calendar') inner = pageCalendar();
  else if (r.name === 'quote') inner = pageQuote();
  else inner = pageDashboard();
  $('#app').innerHTML = layout(active, inner);
  bind(r);
}

function bind(r) {
  document.querySelectorAll('[data-go]').forEach((b) => b.addEventListener('click', () => go(b.dataset.go)));
  $('[data-reset]')?.addEventListener('click', () => { if (confirm('Reset demo data?')) resetDemo(); });
  $('#contactq')?.addEventListener('input', (e) => { window._contactQ = e.target.value; render(); });
  $('#contactfile')?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    const text = await file.text();
    const rows = parseContactCsv(text);
    const res = importContacts(rows);
    alert(`Imported ${res.added} new, updated ${res.updated}.`);
  });
  $('#contactform')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const existing = r.name === 'contact' ? contactBy(r.id) : null;
    const row = saveContact({ id: existing?.id, name: f.get('name'), company: f.get('company'), phones: [{ id: existing?.phones?.[0]?.id || uid('ph'), label: 'Mobile', number: f.get('phone') }], notes: f.get('notes'), banned: !!f.get('banned') });
    go('/contacts/' + row.id);
  });
  $('#delcontact')?.addEventListener('click', () => { if (confirm('Delete this contact?')) { deleteContact(r.id); go('/contacts'); } });
  $('#vendorform')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const existing = r.name === 'vendor' ? vendorBy(r.id) : null;
    const row = saveVendor({ id: existing?.id, name: f.get('name'), phone: f.get('phone'), notes: f.get('notes') });
    go('/vendors/' + row.id);
  });
  $('#filereceipt')?.addEventListener('click', () => fileReceipt($('#receipttext')?.value || '', ''));
  $('#receiptfile')?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    fileReceipt(await file.text(), file.name);
  });
  document.querySelectorAll('[data-site]').forEach((b) => b.addEventListener('click', () => {
    const form = $('#ticketform'); if (!form) return;
    form.jobsiteId.value = b.dataset.site;
    form.address.value = b.dataset.addr;
  }));
  $('#ticketform')?.addEventListener('change', (e) => {
    if (e.target.name !== 'contactId') return;
    const sites = recentSites(e.target.value);
    $('#sitechips').innerHTML = sites.map((j) => `<button type="button" class="badge bg-mint/30 text-navy" data-site="${j.id}" data-addr="${escapeAttr(addr(j))}">${escapeHtml(j.label || j.line1)}</button>`).join('');
    document.querySelectorAll('[data-site]').forEach((b) => b.addEventListener('click', () => { e.target.form.jobsiteId.value = b.dataset.site; e.target.form.address.value = b.dataset.addr; }));
  });
  $('#ticketform')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const existing = r.name === 'ticket-edit' ? S.pours.find((p) => p.id === r.id) : null;
    const row = savePour({ id: existing?.id, contactId: f.get('contactId'), jobsiteId: f.get('jobsiteId'), address: f.get('address'), yards: f.get('yards'), psi: f.get('psi'), scheduledAt: f.get('scheduledAt') ? new Date(f.get('scheduledAt')).toISOString() : nowIso(), truckId: f.get('truckId'), notes: f.get('notes') });
    if (row) go('/tickets/' + row.id);
  });
  document.querySelectorAll('[data-status]').forEach((b) => b.addEventListener('click', () => setStatus(r.id, b.dataset.status)));
  document.querySelectorAll('[data-fill]').forEach((b) => b.addEventListener('click', () => fillYard(b.dataset.fill)));
  $('#quoteform')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const price = S.mixPrices[f.get('psi')] || 198;
    $('#quoteout').textContent = money(Number(f.get('yards')) * price);
  });
  $('#qboconnect')?.addEventListener('click', connectQbo);
  $('#qbopull')?.addEventListener('click', pullQbo);
}
function fileReceipt(text, fileName) {
  const parsed = parseReceiptText(text, fileName);
  const vendor = findOrCreateVendor(parsed.vendorName || 'Unknown shop');
  if (!vendor) return;
  saveReceipt({ vendorId: vendor.id, title: parsed.title, date: parsed.date, amount: parsed.amount, invoice: parsed.invoice, notes: 'Filed from upload', text });
  go('/vendors/' + vendor.id);
}

window.addEventListener('hashchange', render);
if (!location.hash) location.hash = '/';
render();
