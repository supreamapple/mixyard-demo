async function syncYard() {
  if (!window.MIXYARD_SERVER) return;
  await fetch('/api/jobs/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contacts: S.contacts, pours: S.pours })
  });
}

function mergeServer(data) {
  let changed = false;
  (data.contacts || []).forEach((c) => {
    const row = S.contacts.find((x) => x.id === c.id);
    if (!row) {
      S.contacts.push({
        id: c.id,
        name: c.name,
        company: '',
        email: c.email || '',
        phones: c.phone ? [{ id: uid('ph'), label: 'Mobile', number: c.phone }] : [],
        notes: '',
        banned: !!c.do_not_contact,
        emailOptOut: !!c.email_opt_out,
        smsOptOut: !!c.sms_opt_out,
        createdAt: nowIso()
      });
      changed = true;
      return;
    }
    if (!row.email && c.email) { row.email = c.email; changed = true; }
    if (!!row.emailOptOut !== !!c.email_opt_out) { row.emailOptOut = !!c.email_opt_out; changed = true; }
    if (!!row.smsOptOut !== !!c.sms_opt_out) { row.smsOptOut = !!c.sms_opt_out; changed = true; }
  });
  (data.jobs || []).forEach((j) => {
    if (S.pours.some((p) => p.id === j.id)) return;
    S.pours.unshift({
      id: j.id,
      ticketNo: j.ticket_no,
      contactId: j.contact_id,
      jobsiteId: '',
      address: j.address || '',
      truckId: '',
      driverId: '',
      yards: j.quantity || 0,
      psi: 0,
      scheduledAt: j.scheduled_at,
      status: j.status,
      notes: j.notes || ''
    });
    changed = true;
  });
  if (changed) localStorage.setItem(KEY, JSON.stringify(S));
}

async function refreshFollowups() {
  if (!window.MIXYARD_SERVER) { window.F = null; return; }
  const res = await fetch('/api/bootstrap', { cache: 'no-store' });
  if (!res.ok) { window.F = null; return; }
  window.F = await res.json();
  mergeServer(window.F);
}

function stamp(iso) {
  if (!iso) return '—';
  return fmtDate(iso) + ' ' + fmtTime(iso);
}

function tapAnchor(jobId) {
  const job = ((window.F && window.F.jobs) || []).find((j) => j.id === jobId);
  if (!job || !job.tap_href) return '';
  return `<a class="btn btn-g shrink-0" data-tap="${escapeAttr(job.tap_nudge)}" data-job="${escapeAttr(job.id)}" href="${escapeAttr(job.tap_href)}">Text</a>`;
}

function ticketTap(p) {
  const job = ((window.F && window.F.jobs) || []).find((j) => j.id === p.id);
  if (!job || !job.tap_href) return '';
  return `<a class="btn btn-p" data-tap="${escapeAttr(job.tap_nudge)}" data-job="${escapeAttr(job.id)}" href="${escapeAttr(job.tap_href)}">Text customer</a>`;
}

function ticketFollowups(p) {
  const rows = window._jobLog || [];
  const list = rows.length
    ? rows.map((m) => `<div class="border-t border-navy/10 py-2 text-sm"><div class="flex items-center justify-between gap-2"><span class="font-semibold">${escapeHtml(m.label)}</span><span class="badge bg-navy/10 text-navy">${escapeHtml(m.status_label)}</span></div><div class="text-slateish">${escapeHtml(stamp(m.at))}</div><div class="bubble mt-1">${escapeHtml(m.body)}</div></div>`).join('')
    : '<div class="text-sm text-slateish">Nothing sent on this ticket.</div>';
  return `<section class="card mt-3 p-4"><h2 class="font-display text-2xl">Follow-ups</h2><div class="mt-2">${list}</div></section>`;
}

function contactThread(c) {
  const thread = window._thread;
  if (!thread || thread.contact_id !== c.id || !thread.inbox) return '';
  const items = (thread.items || []).map((item) => {
    if (item.kind === 'call') return `<div class="text-center text-xs font-semibold uppercase tracking-wide text-slateish">${escapeHtml(stamp(item.at))} · Missed call</div>`;
    const mine = item.direction === 'out';
    return `<div class="flex ${mine ? 'justify-end' : 'justify-start'}"><div class="max-w-[85%] rounded-2xl px-3 py-2 text-sm ${mine ? 'bg-kelly/15' : 'bg-navy/5'}"><div class="bubble">${escapeHtml(item.body)}</div><div class="mt-1 text-[11px] text-slateish">${escapeHtml(stamp(item.at))}${mine ? ' · ' + escapeHtml(item.status_label) : ''}</div></div></div>`;
  }).join('') || '<div class="text-sm text-slateish">No texts or calls yet.</div>';
  const composer = thread.sms_opt_out
    ? '<p class="mt-3 text-sm text-rose-700">This customer opted out. Texts stay off.</p>'
    : `<form id="threadform" class="mt-3 flex gap-2"><input name="text" class="field" placeholder="Text ${escapeAttr(c.name.split(' ')[0] || 'the customer')}" /><button class="btn btn-p" type="submit">Send</button></form>`;
  return `<section class="card mt-3 p-4"><h2 class="font-display text-2xl">Texts and calls</h2><div class="mt-3 space-y-2">${items}</div>${composer}</section>`;
}

function pageSettings() {
  if (!window.F || !window.F.followups) {
    return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Settings</p><h1 class="font-display text-4xl">Customer follow-ups</h1><p class="mt-2 text-sm text-slateish">Every follow-up stays off until a switch is on.</p>`;
  }
  return pageFollowupSettings();
}

function pageFollowupSettings() {
  const f = window.F.followups;
  const groups = f.groups.map((group) => {
    const onCount = group.items.filter((item) => item.on).length;
    const badge = onCount ? `<span class="badge bg-kelly/15 text-kelly">${onCount} on</span>` : `<span class="badge bg-navy/10 text-navy">Off</span>`;
    const items = group.items.map((item) => {
      const message = item.has_message ? `<div class="bubble mt-2 rounded-xl bg-paper px-3 py-2 text-sm">${escapeHtml(item.preview)}</div>
        <label class="mt-2 block text-xs font-semibold uppercase tracking-wide text-slateish">Message
          <textarea class="field mt-1" rows="3" data-message="${escapeAttr(item.key)}">${escapeHtml(item.body)}</textarea>
        </label>
        <button class="btn btn-g mt-2" type="button" data-save-message="${escapeAttr(item.key)}">Save message</button>` : '';
      const note = item.locked ? '<p class="mt-1 text-xs text-slateish">Turn on automatic texting to use this.</p>' : '';
      return `<div class="border-t border-navy/10 px-4 py-3">
        <div class="flex items-center justify-between gap-3"><div class="font-semibold">${escapeHtml(item.label)}</div>
          <label class="switch"><input type="checkbox" data-switch="${escapeAttr(item.key)}" ${item.on ? 'checked' : ''} ${item.locked ? 'disabled' : ''} aria-label="${escapeAttr(item.label)}" /><i></i></label>
        </div>${note}${message}</div>`;
    }).join('');
    return `<section class="card mt-4"><div class="flex items-start justify-between gap-3 px-4 py-3"><div><h2 class="font-display text-2xl">${escapeHtml(group.title)}</h2><p class="text-sm text-slateish">${escapeHtml(group.intro)}</p></div>${badge}</div>
      ${groupExtras(group, f)}${items}</section>`;
  }).join('');
  const held = !f.email_ready || !f.texting_ready;
  const heldNote = held ? '<p class="mt-2 text-sm text-slateish">Mail and texts stay in the list below until the yard server is connected to them. Test mode does not use a live shop number.</p>' : '';
  const activity = (f.activity || []).map((row) => `<div class="border-t border-navy/10 px-4 py-3 text-sm"><div class="flex items-start justify-between gap-2"><div><div class="font-semibold">${escapeHtml(row.who)} · ${escapeHtml(row.label)}</div><div class="text-slateish">${escapeHtml(stamp(row.at))}</div></div><span class="badge bg-navy/10 text-navy">${escapeHtml(row.status_label)}</span></div><div class="bubble mt-1">${escapeHtml(row.body)}</div></div>`).join('')
    || '<div class="px-4 py-3 text-sm text-slateish">Nothing sent yet.</div>';
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Settings</p>
    <h1 class="font-display text-4xl">Customer follow-ups</h1>
    <p class="mt-1 text-sm text-slateish">Every switch is off until you turn it on. Messages are written by E<span class="text-kelly">nza</span>. Edit any of them.</p>
    ${heldNote}
    <section class="card mt-4 p-4"><label class="block text-sm font-semibold">Shop name on messages<input id="shop-name" class="field mt-1" value="${escapeAttr(f.shop_name)}" /></label><button class="btn btn-g mt-3" type="button" id="save-shop">Save name</button></section>
    ${groups}
    <section class="card mt-4"><div class="flex items-center justify-between px-4 py-3"><h2 class="font-display text-2xl">Sent</h2><button class="btn btn-n" type="button" id="followup-run">Check now</button></div>${activity}</section>`;
}

function groupExtras(group, f) {
  if (group.id === 'done') {
    return `<div class="border-t border-navy/10 px-4 py-3"><label class="block text-sm font-semibold">Google review link<input id="review-url" class="field mt-1" placeholder="https://g.page/..." value="${escapeAttr(f.google_review_url)}" /></label><button class="btn btn-g mt-2" type="button" id="save-review">Save link</button></div>`;
  }
  if (group.id === 'texting') {
    const addon = group.items.find((item) => item.key === 'texting_addon');
    const tools = addon && addon.on ? `<div class="border-t border-navy/10 px-4 py-3"><div class="font-semibold">Test a call or text</div><p class="text-sm text-slateish">Nothing leaves the yard. Demo numbers stay held.</p>
      <input id="sim-phone" class="field mt-2" value="(360) 555-0198" />
      <input id="sim-body" class="field mt-2" value="Can you pour Thursday?" />
      <div class="mt-2 flex flex-wrap gap-2"><button class="btn btn-g" type="button" id="sim-miss">Missed call</button><button class="btn btn-g" type="button" id="sim-text">Customer text</button></div></div>` : '';
    return `<div class="border-t border-navy/10 px-4 py-3"><label class="block text-sm font-semibold">Forward calls to<input id="forward-to" class="field mt-1" placeholder="(360) 555-0100" value="${escapeAttr(f.forward_to)}" /></label><button class="btn btn-g mt-2" type="button" id="save-forward">Save number</button></div>${tools}`;
  }
  return '';
}

function pageQuotes() {
  const quotes = (window.F && window.F.quotes) || [];
  const bookable = S.contacts.filter((c) => !c.banned);
  const cards = quotes.map((q) => {
    const tone = q.badge === 'Signed' ? 'bg-kelly/15 text-kelly' : q.badge === 'Viewed, not signed' ? 'bg-amber-100 text-amber-800' : 'bg-navy/10 text-navy';
    const tap = q.tap_href ? `<a class="btn btn-p" data-tap="tap_quote" data-quote="${escapeAttr(q.id)}" href="${escapeAttr(q.tap_href)}">Text</a>` : '';
    const send = q.status === 'draft' ? `<button class="btn btn-n" type="button" data-send-quote="${escapeAttr(q.id)}">Send quote</button>` : '';
    return `<section class="card p-4"><div class="flex items-start justify-between gap-2"><div><div class="font-semibold">${escapeHtml(q.contact_name)} · ${q.quantity} yards</div><div class="text-sm text-slateish">${escapeHtml(q.detail)} · ${money(q.amount_cents / 100)}</div><div class="text-sm">${escapeHtml(q.address)}</div></div><span class="badge ${tone}">${escapeHtml(q.badge)}</span></div>
      <div class="mt-3 grid grid-cols-3 gap-2 text-center text-sm"><div><div class="text-[11px] font-semibold uppercase text-slateish">Sent</div><div class="font-semibold">${escapeHtml(stamp(q.sent_at))}</div></div><div><div class="text-[11px] font-semibold uppercase text-slateish">Viewed</div><div class="font-semibold">${escapeHtml(stamp(q.viewed_at))}</div></div><div><div class="text-[11px] font-semibold uppercase text-slateish">Signed</div><div class="font-semibold">${escapeHtml(stamp(q.signed_at))}</div></div></div>
      <div class="mt-3 flex flex-wrap gap-2">${send}${tap}<a class="btn btn-g" target="_blank" rel="noopener" href="${escapeAttr(q.customer_path)}?preview=1">Preview</a></div>
      <p class="mt-2 break-all text-xs text-slateish">${escapeHtml(location.origin + q.customer_path)}</p></section>`;
  }).join('');
  return `<p class="text-xs font-semibold uppercase tracking-widest text-slateish">Pricing</p><h1 class="font-display text-4xl">Quotes</h1>
    <p class="mt-1 text-sm text-slateish">Sent, viewed, and signed stay on the quote. Follow-ups go out only after a customer has looked and has not signed.</p>
    <form id="quotefollow" class="card mt-4 space-y-3 p-4">
      <label class="block text-sm font-semibold">Customer<select name="contactId" class="field mt-1">${bookable.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}</select></label>
      <label class="block text-sm font-semibold">Jobsite<input name="address" class="field mt-1" placeholder="88 River Rd, Longview" /></label>
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="block text-sm font-semibold">Yards<input name="yards" type="number" step="0.5" class="field mt-1" value="5" /></label>
        <label class="block text-sm font-semibold">PSI<select name="psi" class="field mt-1">${Object.keys(S.mixPrices).map((n) => `<option ${n === '4000' ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
      </div>
      <button class="btn btn-p" type="submit">Save quote</button>
    </form>
    <div class="mt-3 grid gap-3">${cards || '<div class="text-sm text-slateish">No quotes yet.</div>'}</div>`;
}

async function saveFollowups(patch) {
  await fetch('/api/followups', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch)
  });
  await render();
}

function bindFollowups() {
  document.querySelectorAll('[data-switch]').forEach((input) => {
    input.addEventListener('change', () => {
      const patch = {};
      patch[input.dataset.switch] = input.checked;
      saveFollowups({ switches: patch });
    });
  });
  document.querySelectorAll('[data-save-message]').forEach((button) => {
    button.addEventListener('click', () => {
      const key = button.dataset.saveMessage;
      const field = document.querySelector(`[data-message="${key}"]`);
      const messages = {};
      messages[key] = field ? field.value : '';
      saveFollowups({ messages });
    });
  });
  $('#save-shop')?.addEventListener('click', () => saveFollowups({ shop_name: $('#shop-name').value }));
  $('#save-review')?.addEventListener('click', () => {
    let url = ($('#review-url').value || '').trim();
    if (url && !/^https?:\/\//i.test(url)) url = 'https://' + url;
    saveFollowups({ google_review_url: url });
  });
  $('#save-forward')?.addEventListener('click', () => saveFollowups({ forward_to: $('#forward-to').value }));
  $('#followup-run')?.addEventListener('click', async () => {
    await fetch('/api/followups/run', { method: 'POST' });
    await render();
  });
  $('#sim-miss')?.addEventListener('click', () => simulate('voice'));
  $('#sim-text')?.addEventListener('click', () => simulate('sms'));
  document.querySelectorAll('[data-tap]').forEach((link) => {
    link.addEventListener('click', () => {
      const payload = { nudge: link.dataset.tap };
      if (link.dataset.job) payload.job_id = link.dataset.job;
      if (link.dataset.quote) payload.quote_id = link.dataset.quote;
      fetch('/api/followups/tapped', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    });
  });
  document.querySelectorAll('[data-send-quote]').forEach((button) => {
    button.addEventListener('click', async () => {
      await fetch('/api/quotes/' + button.dataset.sendQuote + '/send', { method: 'POST' });
      await render();
    });
  });
  $('#quotefollow')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const psi = form.get('psi');
    const yards = Number(form.get('yards'));
    const price = S.mixPrices[psi] || 198;
    await fetch('/api/quotes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: form.get('contactId'),
        quantity: yards,
        detail: psi + ' PSI',
        address: form.get('address'),
        amount: yards * price
      })
    });
    await render();
  });
  $('#threadform')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = window._thread && window._thread.contact_id;
    if (!id) return;
    await fetch('/api/contacts/' + encodeURIComponent(id) + '/reply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: new FormData(e.target).get('text') })
    });
    await render();
  });
}

async function simulate(kind) {
  const phone = ($('#sim-phone') && $('#sim-phone').value) || '(360) 555-0198';
  const body = ($('#sim-body') && $('#sim-body').value) || 'Can you pour Thursday?';
  const path = kind === 'voice' ? '/api/voice/missed' : '/api/sms/inbound';
  await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Mixyard-Test': '1' },
    body: JSON.stringify({ from: phone, body })
  });
  await render();
}
