"""JavaScript extractors evaluated inside Avito pages.

Selectors rely on Avito's ``data-marker`` attributes, which are more stable than
CSS class names. Every extractor degrades to plain text so the model can still
read a page whose layout changed.
"""

PAGE_TEXT_JS = r"""
(selector) => {
  const root = selector ? document.querySelector(selector) : document.body;
  if (!root) return null;
  return root.innerText.replace(/[ \t ]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
}
"""

# Marks visible interactive elements with data-mcp-ref and lists them.
SNAPSHOT_JS = r"""
({maxItems, viewportOnly}) => {
  const sel = [
    'a[href]', 'button', 'input:not([type=hidden])', 'textarea', 'select', 'summary',
    '[role=button]', '[role=tab]', '[role=link]', '[role=checkbox]', '[role=radio]',
    '[role=menuitem]', '[role=option]', '[role=switch]', '[role=combobox]',
    '[contenteditable=""]', '[contenteditable=true]'
  ].join(',');
  // Refs are stable: an element keeps its ref across snapshots, new elements get the next number.
  const refOf = el => {
    let r = el.getAttribute('data-mcp-ref');
    if (!r) { window.__mcpRefSeq = (window.__mcpRefSeq || 0) + 1; r = 'e' + window.__mcpRefSeq; el.setAttribute('data-mcp-ref', r); }
    el.setAttribute('data-mcp-now', '');  // listed in this snapshot; cleared at the end
    return r;
  };
  const out = [];
  let n = 0;
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || st.opacity === '0') continue;
    const inView = r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
    if (viewportOnly && !inView) continue;
    const img = el.querySelector('img[alt]');
    let name = el.getAttribute('aria-label') || el.innerText || el.value || el.placeholder
      || el.title || (img && img.alt) || '';
    name = name.replace(/\s+/g, ' ').trim().slice(0, 140);
    n++;
    const ref = refOf(el);
    const item = {ref, tag: el.tagName.toLowerCase()};
    const role = el.getAttribute('role'); if (role) item.role = role;
    if (name) item.name = name;
    const href = el.getAttribute('href'); if (href) item.href = href.split('?')[0].slice(0, 200);
    if (el.type && el.tagName !== 'BUTTON') item.type = el.type;
    const marker = el.getAttribute('data-marker'); if (marker) item.marker = marker;
    if (el.getAttribute('aria-selected') === 'true' || el.getAttribute('aria-checked') === 'true' || el.checked) item.selected = true;
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') item.disabled = true;
    if (!inView) item.offscreen = true;
    out.push(item);
    if (n >= maxItems) break;
  }
  // Second pass: clickable blocks without a role (React handlers), outermost only.
  for (const el of document.querySelectorAll('div,span,li,img,svg')) {
    if (n >= maxItems) break;
    if (el.closest('[data-mcp-now]')) continue;
    const st = getComputedStyle(el);
    if (st.cursor !== 'pointer') continue;
    if (el.parentElement && getComputedStyle(el.parentElement).cursor === 'pointer') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || st.visibility === 'hidden') continue;
    const inView = r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
    if (viewportOnly && !inView) continue;
    const img = el.tagName === 'IMG' ? el : el.querySelector('img[alt]');
    let name = el.getAttribute('aria-label') || el.innerText || el.title || (img && img.alt) || '';
    name = name.replace(/\s+/g, ' ').trim().slice(0, 140);
    const owner = el.closest('[data-marker]');
    n++;
    const ref = refOf(el);
    const item = {ref, tag: el.tagName.toLowerCase(), role: 'clickable'};
    if (name) item.name = name;
    if (owner) item.marker = owner.getAttribute('data-marker');
    if (!inView) item.offscreen = true;
    out.push(item);
  }
  document.querySelectorAll('[data-mcp-now]').forEach(e => e.removeAttribute('data-mcp-now'));
  return out;
}
"""

# Same card selectors as the scraper used on 22-23.09.2026, plus location and date.
SEARCH_CARDS_JS = r"""
() => {
  const tx = e => e ? e.innerText.replace(/\s+/g, ' ').trim() : '';
  return [...document.querySelectorAll('[data-marker="item"]')].map((c, i) => {
    const a = c.querySelector('[data-marker="item-title"]');
    const all = c.innerText;
    const sl = [...c.querySelectorAll('a')].find(x => /\/(brands|user)\//.test(x.getAttribute('href') || ''));
    const dm = c.querySelector('meta[itemprop="description"]');
    return {
      id: c.getAttribute('data-item-id') || '',
      position: i + 1,
      title: tx(a),
      url: a ? new URL(a.getAttribute('href') || '', location.origin).href.split('?')[0] : '',
      // goods cards often have no item-price node: fall back to schema.org meta, then the first "N ₽" in the text
      price: tx(c.querySelector('[data-marker="item-price"]'))
        || ((c.querySelector('meta[itemprop="price"]') || {}).content ? c.querySelector('meta[itemprop="price"]').content + ' ₽' : '')
        || ((all.match(/(\d[\d\s\u00a0]*)\s?₽/) || [''])[0]).replace(/\s+/g, ' ').trim(),
      price_list: tx(c.querySelector('[data-marker="price-lists-block"]')),
      description: dm ? dm.content.slice(0, 400) : '',
      location: tx(c.querySelector('[data-marker="item-address"], [data-marker="item-location"]')),
      date: tx(c.querySelector('[data-marker="item-date"]')),
      promoted: /Продвинуто/.test(all),
      seller: sl ? sl.innerText.split('\n')[0].trim() : '',
      seller_url: sl ? new URL(sl.getAttribute('href') || '', location.origin).href.split('?')[0] : '',
      seller_score: tx(c.querySelector('[data-marker="seller-info/score"],[data-marker="seller-rating/score"]')),
      seller_reviews: ((all.match(/(\d[\d\s]*)\s+отзыв/) || [])[1] || '').replace(/\s/g, ''),
      badges: [...c.querySelectorAll('[data-marker^="badge-title"]')].map(tx),
      photos_in_card: c.querySelectorAll('[data-marker^="slider-image"]').length,
    };
  }).filter(x => x.id);
}
"""

LISTING_JS = r"""
() => {
  const t = document.body.innerText;
  const q = s => { const e = document.querySelector(s); return e ? e.innerText.replace(/[ \t ]+/g, ' ').trim() : ''; };
  const Q = String.fromCharCode(34);
  const h = document.documentElement.innerHTML.split(String.fromCharCode(92)).join('');
  const parts = h.split(Q + '1280x960' + Q + ':' + Q);
  const photos = []; for (let k = 1; k < parts.length; k++) photos.push(parts[k].split(Q)[0]);
  const ri = t.indexOf('Отзывы');
  const views = q('[data-marker="item-view/total-views"]') || ((t.match(/(\d[\d\s]*)\s+просмотр[^\n]*/) || [''])[0]);
  return {
    url: location.href.split('?')[0],
    id: ((location.pathname.match(/_(\d+)$/) || [])[1]) || ((t.match(/№\s?(\d+)/) || [])[1] || ''),
    title: q('[data-marker="item-view/title-info"]') || q('h1'),
    price: q('[data-marker="item-view/item-price"]'),
    price_list: [...document.querySelectorAll('[data-marker^="PRICE_LIST_VALUE_MARKER"]')].map(e => e.innerText.replace(/\s+/g, ' ').trim()),
    params: q('[data-marker="item-view/item-params"]'),
    description: q('[data-marker="item-view/item-description"]'),
    address: q('[data-marker="item-view/item-address"]') || q('[itemprop="address"]'),
    date: q('[data-marker="item-view/item-date"]'),
    views: views,
    views_today: q('[data-marker="item-view/today-views"]'),
    seller: q('[data-marker="item-view/seller-info"]'),
    badges: [...document.querySelectorAll('[data-marker^="badge-title"],[data-marker^="badge-description"]')].map(e => e.innerText.trim()),
    reviews_excerpt: ri >= 0 ? t.slice(ri, ri + 1500) : '',
    photos: [...new Set(photos)],
  };
}
"""

# Own listings in the profile. The personal cabinet uses item-snippet markers;
# the Pro cabinet is matched by links to listing pages as a fallback.
MY_ITEMS_JS = r"""
() => {
  const tx = e => e ? e.innerText.replace(/[ \t ]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim() : '';
  let cards = [...document.querySelectorAll('[data-marker^="item-snippet/"]')];
  let source = 'item-snippet';
  if (!cards.length) {
    source = 'listing-links';
    const seen = new Set();
    for (const a of document.querySelectorAll('a[href]')) {
      const href = a.getAttribute('href') || '';
      const m = href.match(/_(\d{6,})(?:[?#]|$)/) || href.match(/\/items\/(\d{6,})/);
      if (!m || seen.has(m[1])) continue;
      seen.add(m[1]);
      let card = a;
      for (let k = 0; k < 8 && card.parentElement; k++) {
        const p = card.parentElement;
        const ids = new Set([...p.querySelectorAll('a[href]')].map(x => ((x.getAttribute('href') || '').match(/_(\d{6,})|\/items\/(\d{6,})/) || []).slice(1).find(Boolean)).filter(Boolean));
        if (ids.size > 1) break;
        card = p;
      }
      card.dataset.mcpItemId = m[1];
      cards.push(card);
    }
  }
  const items = cards.map(c => {
    const marker = c.getAttribute('data-marker') || '';
    const id = marker.startsWith('item-snippet/') ? marker.split('/')[1] : c.dataset.mcpItemId;
    const link = [...c.querySelectorAll('a[href]')].find(a => /_\d{6,}|\/items\/\d{6,}/.test(a.getAttribute('href') || ''));
    return {
      id,
      url: link ? new URL(link.getAttribute('href'), location.origin).href.split('?')[0] : null,
      text: tx(c).slice(0, 600),
    };
  });
  const tabs = [...document.querySelectorAll('[role=tab], [data-marker*="tab"] a, [data-marker*="tabs"] button')]
    .map(e => e.innerText.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return {source, tabs: [...new Set(tabs)].slice(0, 20), items};
}
"""

# Profile switcher in the avatar menu: profile-switch/first, /second, /third...
PROFILES_JS = r"""
() => [...document.querySelectorAll('[data-marker^="profile-switch/"]')]
  .filter(e => e.getAttribute('data-marker') !== 'profile-switch/add')
  .map((e, i) => {
    const img = e.querySelector('img');
    const letter = (e.innerText || '').trim();
    return {
      index: i + 1,
      slot: e.getAttribute('data-marker').split('/')[1],
      current: i === 0,
      avatar: img ? img.getAttribute('src') : null,
      letter: letter || null,
    };
  })
"""

PROFILE_NAME_JS = r"""
() => {
  const pick = s => { const e = document.querySelector(s); return e ? e.innerText.replace(/\s+/g, ' ').trim() : ''; };
  return pick('[data-marker="profile/name"], [data-marker="sidebar/name"], [data-marker*="username"] h3, h1');
}
"""

# Replace one exact fragment inside an input, textarea or rich-text editor, keeping the editor's own state.
REPLACE_TEXT_JS = r"""
(el, [find, repl]) => {
  if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
    const v = el.value; const i = v.indexOf(find);
    if (i < 0) return {ok: false, reason: 'not_found'};
    if (v.indexOf(find, i + 1) >= 0) return {ok: false, reason: 'ambiguous'};
    const proto = el.tagName === 'INPUT' ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v.slice(0, i) + repl + v.slice(i + find.length));
    el.dispatchEvent(new Event('input', {bubbles: true}));
    return {ok: true, text: el.value};
  }
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const nodes = []; let full = '';
  for (let n = walker.nextNode(); n; n = walker.nextNode()) { nodes.push([n, full.length]); full += n.data; }
  const i = full.indexOf(find);
  if (i < 0) return {ok: false, reason: 'not_found'};
  if (full.indexOf(find, i + 1) >= 0) return {ok: false, reason: 'ambiguous'};
  // start: node containing pos; end: node where pos falls inside or exactly at its end,
  // so a fragment ending a paragraph never stretches into the next one
  const atStart = pos => { for (const [n, o] of nodes) if (pos >= o && pos < o + n.data.length) return [n, pos - o]; };
  const atEnd = pos => { for (const [n, o] of nodes) if (pos > o && pos <= o + n.data.length) return [n, pos - o]; };
  const [sn, so] = atStart(i); const [en, eo] = atEnd(i + find.length);
  // Rich editors (Draft.js) keep their own state: only select the fragment here, the caller types over it.
  el.focus();
  const range = document.createRange(); range.setStart(sn, so); range.setEnd(en, eo);
  const sel = getSelection(); sel.removeAllRanges(); sel.addRange(range);
  document.dispatchEvent(new Event('selectionchange'));
  return {ok: true, selected: true};
}
"""
