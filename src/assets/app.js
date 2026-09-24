/* Gde živeti — shared front-end logic (no dependencies). */
(function () {
  "use strict";

  /* ---------- storage (safe) ---------- */
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } },
  };

  /* ---------- Latin <-> Cyrillic ---------- */
  const DIGRAPHS = { "Lj": "Љ", "LJ": "Љ", "lj": "љ", "Nj": "Њ", "NJ": "Њ", "nj": "њ", "Dž": "Џ", "DŽ": "Џ", "dž": "џ" };
  const SINGLE = {
    A: "А", B: "Б", V: "В", G: "Г", D: "Д", Đ: "Ђ", E: "Е", Ž: "Ж", Z: "З", I: "И", J: "Ј", K: "К", L: "Л",
    M: "М", N: "Н", O: "О", P: "П", R: "Р", S: "С", T: "Т", Ć: "Ћ", U: "У", F: "Ф", H: "Х", C: "Ц", Č: "Ч", Š: "Ш",
    a: "а", b: "б", v: "в", g: "г", d: "д", đ: "ђ", e: "е", ž: "ж", z: "з", i: "и", j: "ј", k: "к", l: "л",
    m: "м", n: "н", o: "о", p: "п", r: "р", s: "с", t: "т", ć: "ћ", u: "у", f: "ф", h: "х", c: "ц", č: "ч", š: "ш",
  };
  function toCyr(s) {
    let out = "";
    for (let i = 0; i < s.length; i++) {
      const two = s.substr(i, 2);
      if (DIGRAPHS[two]) { out += DIGRAPHS[two]; i++; continue; }
      const ch = s[i];
      out += SINGLE[ch] !== undefined ? SINGLE[ch] : ch;
    }
    return out;
  }
  const originals = new WeakMap();
  const SKIP = new Set(["SCRIPT", "STYLE", "CODE", "TEXTAREA"]);
  function walk(root, fn) {
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        let p = n.parentNode;
        while (p && p !== root.parentNode) {
          if (p.nodeType === 1 && (SKIP.has(p.nodeName) || p.classList.contains("no-translit"))) return NodeFilter.FILTER_REJECT;
          p = p.parentNode;
        }
        return /[A-Za-zČčĆćŠšŽžĐđ]/.test(n.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    const nodes = [];
    while (tw.nextNode()) nodes.push(tw.currentNode);
    nodes.forEach(fn);
  }
  let script = store.get("script") === "cyr" ? "cyr" : "lat";
  function applyScript(root) {
    root = root || document.body;
    if (script === "cyr") {
      walk(root, (n) => {
        if (!originals.has(n)) originals.set(n, n.nodeValue);
        n.nodeValue = toCyr(originals.get(n));
      });
      root.querySelectorAll("[placeholder]").forEach((el) => {
        if (!el.dataset.phLat) el.dataset.phLat = el.placeholder;
        el.placeholder = toCyr(el.dataset.phLat);
      });
    } else {
      const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      while (tw.nextNode()) {
        const n = tw.currentNode;
        if (originals.has(n)) n.nodeValue = originals.get(n);
      }
      root.querySelectorAll("[data-ph-lat]").forEach((el) => { el.placeholder = el.dataset.phLat; });
    }
    document.documentElement.lang = script === "cyr" ? "sr-Cyrl" : "sr-Latn";
    document.querySelectorAll(".script-toggle button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.script === script)));
  }
  /** Use when inserting dynamic content: renders HTML then applies current script. */
  function render(el, html) { el.innerHTML = html; if (script === "cyr") applyScript(el); }
  function t(s) { return script === "cyr" ? toCyr(s) : s; }

  /* ---------- formatting ---------- */
  const nf0 = new Intl.NumberFormat("sr-Latn-RS", { maximumFractionDigits: 0 });
  const nf1 = new Intl.NumberFormat("sr-Latn-RS", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  function fmt(v, m) {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    const d = m && m.decimals ? nf1.format(v) : nf0.format(v);
    const sign = m && m.signed && v > 0 ? "+" : "";
    return sign + d + (m && m.unit ? " " + m.unit : "");
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  /* ---------- data ---------- */
  const BASE = document.documentElement.dataset.base || "/";
  const IX = document.documentElement.dataset.ix || "";
  let dataPromise = null;
  function loadData() {
    if (!dataPromise) dataPromise = fetch(BASE + "assets/data.json").then((r) => r.json());
    return dataPromise;
  }
  const isCat = (m) => m.type === "cat";
  function hasData(data, k) {
    return isCat(data.metrics[k]) ? data.units.some((u) => u.c && u.c[k]) : data.units.some((u) => u.v[k] != null);
  }
  function rankOf(data, key) {
    const m = data.metrics[key];
    if (isCat(m)) {
      const order = Object.fromEntries(m.levels.map((l, i) => [l.code, i]));
      const vals = data.units.filter((u) => u.c[key]);
      vals.sort((a, b) => order[a.c[key]] - order[b.c[key]] || a.name.localeCompare(b.name, "sr"));
      return { rank: {}, n: vals.length, sorted: vals };
    }
    const vals = data.units.filter((u) => u.v[key] != null);
    vals.sort((a, b) => (m.better === "low" ? a.v[key] - b.v[key] : b.v[key] - a.v[key]));
    const r = {};
    vals.forEach((u, i) => { r[u.slug] = i && vals[i - 1].v[key] === u.v[key] ? r[vals[i - 1].slug] : i + 1; });
    return { rank: r, n: vals.length, sorted: vals };
  }
  function levelOf(m, code) { return (m.levels || []).find((l) => l.code === code); }
  function quantileBreaks(values, k) {
    const s = values.filter((v) => v != null).sort((a, b) => a - b);
    const br = [];
    for (let i = 1; i < k; i++) br.push(s[Math.floor((i * s.length) / k)]);
    return br;
  }
  function binOf(v, breaks) { if (v == null) return -1; let i = 0; while (i < breaks.length && v >= breaks[i]) i++; return i; }
  const nfmt = (v, dec) => (v == null ? "—" : (dec ? nf1 : nf0).format(v));

  /** Human-readable value of metric k for unit u (number or category label). */
  function valueText(data, k, u) {
    const m = data.metrics[k];
    if (isCat(m)) { const l = levelOf(m, u.c[k]); return l ? l.label : (m.nodata_label || "nema podataka"); }
    return fmt(u.v[k], m);
  }
  /** Extra detail line for a metric (shown in tooltip, compare and profile). */
  function detailText(k, u) {
    const d = (u.d || {})[k];
    if (!d) return "";
    if (k === "povezanost") return `${nfmt(d.min_centar)} min do: ${d.centar} · ${nfmt(d.min_autoput)} min do auto-puta · ${nfmt(d.min_aerodrom)} min do: ${d.aerodrom}`;
    if (k === "vazduh") return (d.pm10_dani != null ? `${nfmt(d.pm10_dani)} dana sa previše PM10 čestica (dozvoljeno 35)${d.mesto ? ", merno mesto " + d.mesto : ""}` : "merenja postoje") + (d.napomena ? ` · ${d.napomena}` : "");
    if (k === "voda") return [d.fh != null ? `hemijski neispravnih uzoraka ${nfmt(d.fh, 1)}%` : "", d.mb != null ? `mikrobiološki ${nfmt(d.mb, 1)}%` : ""].filter(Boolean).join(" · ");
    if (k === "vrtici") return `${nfmt(d.nisu_primljeni)} dece nije primljeno, ${nfmt(d.upisani)} upisano · u privatnim vrtićima: ${nfmt(d.privatni_pct, 1)}%`;
    if (k === "kriminal") return `${nfmt(d.zivot)} protiv života i tela, ${nfmt(d.imovina)} protiv imovine (ukupno osuđenih: ${nfmt(d.ukupno)})`;
    if (k === "prirastaj") return `rođeno ${nfmt(d.rodjeni, 1)}, umrlo ${nfmt(d.umrli, 1)} na 1.000 stanovnika`;
    if (k === "turizam") return d.po_stanovniku != null ? `${nfmt(d.po_stanovniku, 1)} noćenja po stanovniku` : "";
    return "";
  }
  function noteHtml(m) {
    return `${esc(m.desc)} <span class="muted">Izvor: ${esc(m.source)}${m.period ? ", " + esc(m.period.replace(/\.$/, "")) : ""}.</span> <span class="fresh${m.stale ? " stale" : ""}">${m.stale ? "⚠ " : ""}${esc(m.freshness || "")}</span>`;
  }

  /* ---------- tooltip ---------- */
  let tipEl = null;
  function tip(html, ev) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tooltip"; tipEl.setAttribute("role", "status"); document.body.appendChild(tipEl); }
    if (html === null) { tipEl.classList.remove("show"); return; }
    render(tipEl, html);
    const pad = 14, w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = ev.clientY - h - pad;
    tipEl.style.left = Math.max(8, x) + "px"; tipEl.style.top = Math.max(8, y) + "px";
    tipEl.classList.add("show");
  }

  /* ================= PAGE: home (map + ranking) ================= */
  function initHome(data) {
    const groupsEl = document.getElementById("group-chips");
    const chipsEl = document.getElementById("metric-chips");
    const listEl = document.getElementById("rank-list");
    const searchEl = document.getElementById("rank-search");
    const legendEl = document.getElementById("map-legend");
    const titleEl = document.getElementById("rank-title");
    const noteEl = document.getElementById("metric-note");
    const svg = document.querySelector("#map svg");
    const keys = data.order.filter((k) => hasData(data, k));
    const groupOf = (k) => data.metrics[k].group;
    const groups = Object.keys(data.groups).filter((g) => keys.some((k) => groupOf(k) === g));
    let key = new URLSearchParams(location.search).get("m");
    if (!keys.includes(key)) key = keys[0];
    const bySlug = Object.fromEntries(data.units.map((u) => [u.slug, u]));

    function drawChips() {
      const g = groupOf(key);
      render(groupsEl, groups.map((x) => `<button class="chip" data-g="${x}" aria-pressed="${x === g}">${esc(data.groups[x])}</button>`).join(""));
      const inGroup = keys.filter((k) => groupOf(k) === g);
      chipsEl.hidden = inGroup.length < 2;
      render(chipsEl, inGroup.map((k) => `<button class="chip chip-sub" data-k="${k}" aria-pressed="${k === key}">${esc(data.metrics[k].short)}</button>`).join(""));
    }
    function select(k) {
      key = k;
      const u = new URL(location.href); u.searchParams.set("m", key); history.replaceState(null, "", u);
      drawChips(); draw();
    }
    groupsEl.addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      select(keys.find((k) => groupOf(k) === b.dataset.g));
    });
    chipsEl.addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (b) select(b.dataset.k); });

    function draw() {
      const m = data.metrics[key];
      const { rank, n, sorted } = rankOf(data, key);
      render(noteEl, noteHtml(m));
      const nd = `<span class="nd"><i></i>${esc(m.nodata_label || "nema podataka")}</span>`;
      const q = (searchEl.value || "").trim().toLowerCase();
      const match = (u) => !q || u.name.toLowerCase().includes(q) || toCyr(u.name).toLowerCase().includes(q);

      if (isCat(m)) {
        render(titleEl, esc(m.label));
        if (svg) {
          svg.querySelectorAll("path[data-slug]").forEach((p) => {
            const u = bySlug[p.dataset.slug]; const l = u ? levelOf(m, u.c[key]) : null;
            p.style.fill = l ? l.color : "var(--nodata)";
          });
          render(legendEl, m.levels.map((l) => `<span class="nd"><i style="background:${l.color}"></i>${esc(l.label)}</span>`).join("") + nd);
        }
        const html = m.levels.map((l) => {
          const us = sorted.filter((u) => u.c[key] === l.code && match(u));
          if (!us.length) return "";
          return `<li class="rank-head"><span class="dot" style="background:${l.color}"></span>${esc(l.label)} <span class="muted">(${us.length})</span></li>` +
            us.map((u) => `<li><a href="${BASE}opstina/${u.slug}/${IX}" data-slug="${u.slug}"><span class="pos"></span><span>${esc(u.name)}${(m.levels.indexOf(l) > 0 || (u.d[key] && u.d[key].pm10_dani != null)) && detailText(key, u) ? `<div class="muted" style="font-size:12px">${esc(detailText(key, u))}</div>` : ""}</span><span></span></a></li>`).join("");
        }).join("");
        const missing = data.units.filter((u) => !u.c[key] && match(u)).length;
        render(listEl, (html || `<li class="muted" style="padding:10px">Nema rezultata.</li>`) + (missing ? `<li class="muted" style="padding:10px 6px;font-size:13px">${esc(m.nodata_label || "Nema podataka")}: ${missing} opština</li>` : ""));
        return;
      }

      const vals = data.units.map((u) => u.v[key]);
      const breaks = quantileBreaks(vals, 5);
      const present = vals.filter((v) => v != null);
      const max = Math.max(...present), minV = Math.min(...present);
      const maxAbs = Math.max(...present.map(Math.abs));
      render(titleEl, `${esc(m.label)} — ${m.better === "low" ? "od najnižeg" : "od najvišeg"}`);
      // Diverging metrics: red for decline, blue for growth, darker = further from zero.
      const neg = present.filter((v) => v < 0), pos = present.filter((v) => v > 0);
      const negBr = quantileBreaks(neg.map((v) => -v), 4);
      const posBr = quantileBreaks(pos, 3);
      function colorOf(v) {
        if (v == null) return "var(--nodata)";
        if (m.diverging) {
          if (v < 0) return `var(--neg-${binOf(-v, negBr) + 1})`;
          if (v > 0) return `var(--pos-${binOf(v, posBr) + 1})`;
          return "var(--mid)";
        }
        return `var(--seq-${binOf(v, breaks) + 1})`;
      }
      if (svg) {
        svg.querySelectorAll("path[data-slug]").forEach((p) => {
          const u = bySlug[p.dataset.slug];
          p.style.fill = u ? colorOf(u.v[key]) : "var(--nodata)";
        });
        if (m.diverging) {
          render(legendEl, `<span>${fmt(minV, m)}</span><span class="ramp">${[4, 3, 2, 1].map((i) => `<span style="background:var(--neg-${i})"></span>`).join("")}</span><span>0</span><span class="ramp">${[1, 2, 3].map((i) => `<span style="background:var(--pos-${i})"></span>`).join("")}</span><span>${fmt(max, m)}</span>${nd}<span class="muted">Crveno = pad, plavo = rast</span>`);
        } else {
          render(legendEl, `<span>${fmt(minV, m)}</span><span class="ramp">${[1, 2, 3, 4, 5].map((i) => `<span style="background:var(--seq-${i})"></span>`).join("")}</span><span>${fmt(max, m)}</span>${nd}<span class="muted">Tamnije = veća vrednost</span>`);
        }
      }
      const items = sorted.filter(match);
      render(listEl, items.map((u) => {
        const w = Math.max(2, (Math.abs(u.v[key]) / (m.diverging ? maxAbs : max)) * 100);
        const bc = m.diverging && u.v[key] < 0 ? "var(--neg-3)" : "var(--accent)";
        return `<li><a href="${BASE}opstina/${u.slug}/${IX}" data-slug="${u.slug}"><span class="pos num">${rank[u.slug]}.</span><span><span>${esc(u.name)}</span><div class="bar" style="width:${w}%;background:${bc}"></div></span><span class="val num">${fmt(u.v[key], m)}</span></a></li>`;
      }).join("") || `<li class="muted" style="padding:10px">Nema rezultata.</li>`);
      listEl.dataset.n = n;
    }
    searchEl.addEventListener("input", draw);

    if (svg) {
      svg.addEventListener("mousemove", (e) => {
        const p = e.target.closest("path[data-slug]");
        if (!p) { tip(null); return; }
        const u = bySlug[p.dataset.slug]; const m = data.metrics[key];
        if (!u) {
          tip(`<b>${esc(p.dataset.name || "")}</b><span class="muted">${p.dataset.slug !== "kim" ? "nema podataka" : "RZS od 1999. ne raspolaže podacima za AP Kosovo i Metohija.<br>Klikni za podatke NSZ o nezaposlenima."}</span>`, e);
          return;
        }
        const { rank, n } = rankOf(data, key);
        const det = detailText(key, u);
        tip(`<b>${esc(u.name)}</b>${esc(m.short)}: <strong class="num">${esc(valueText(data, key, u))}</strong>${!isCat(m) && rank[u.slug] ? `<br><span class="muted">${rank[u.slug]}. od ${n}</span>` : ""}${det ? `<br><span class="muted" style="font-size:13px">${esc(det)}</span>` : ""}`, e);
      });
      svg.addEventListener("mouseleave", () => tip(null));
      svg.addEventListener("click", (e) => {
        const p = e.target.closest("path[data-slug]");
        if (p && p.dataset.slug === "kim") location.href = `${BASE}kosovo-i-metohija/${IX}`;
        else if (p && bySlug[p.dataset.slug]) location.href = `${BASE}opstina/${p.dataset.slug}/${IX}`;
      });
      listEl.addEventListener("mouseover", (e) => {
        const a = e.target.closest("a[data-slug]");
        svg.querySelectorAll("path.hl").forEach((x) => x.classList.remove("hl"));
        if (a) { const p = svg.querySelector(`path[data-slug="${a.dataset.slug}"]`); if (p) { p.classList.add("hl"); p.parentNode.appendChild(p); } }
      });
    }
    drawChips();
    draw();
  }

  /* ================= PAGE: compare ================= */
  const COLORS = ["var(--c1)", "var(--c2)", "var(--c3)"];
  function initCompare(data) {
    const pickers = document.getElementById("pickers");
    const out = document.getElementById("cmp-out");
    const list = document.getElementById("unit-names");
    const byName = {}; const bySlug = {};
    data.units.forEach((u) => { byName[u.name.toLowerCase()] = u; byName[toCyr(u.name).toLowerCase()] = u; bySlug[u.slug] = u; });
    list.innerHTML = data.units.map((u) => `<option value="${esc(t(u.name))}">`).join("");
    const params = (new URLSearchParams(location.search).get("o") || "").split(",").filter((s) => bySlug[s]);
    const sel = [params[0] || null, params[1] || null, params[2] || null];
    if (!sel[0] && !sel[1]) { sel[0] = "novi-sad"; sel[1] = "nis"; }

    render(pickers, [0, 1, 2].map((i) => `<div class="picker"><label for="p${i}"><span class="dot" style="background:${COLORS[i]}"></span>${i === 2 ? "Treće mesto (opciono)" : (i === 0 ? "Prvo mesto" : "Drugo mesto")}</label><input class="search" id="p${i}" list="unit-names" placeholder="Upiši opštinu…" autocomplete="off" value="${sel[i] ? esc(t(bySlug[sel[i]].name)) : ""}"></div>`).join(""));
    pickers.addEventListener("change", (e) => {
      const i = Number(e.target.id.slice(1));
      const u = byName[e.target.value.trim().toLowerCase()];
      sel[i] = u ? u.slug : null;
      if (!u) e.target.value = "";
      const url = new URL(location.href); url.searchParams.set("o", sel.filter(Boolean).join(",")); history.replaceState(null, "", url);
      draw();
    });

    document.addEventListener("gz:script", () => {
      [0, 1, 2].forEach((i) => { const el = document.getElementById("p" + i); if (el) el.value = sel[i] ? t(bySlug[sel[i]].name) : ""; });
    });
    function metricBlock(k, chosen) {
      const m = data.metrics[k];
      const period = `<span class="fresh${m.stale ? " stale" : ""}">${esc(m.period || "")}${m.stale ? " · stariji podaci" : ""}</span>`;
      if (isCat(m)) {
        return `<div class="cmp-metric"><h3>${esc(m.label)}</h3><div class="hint">${period}</div>${chosen.map((c) => {
          const l = levelOf(m, c.u.c[k]); const det = detailText(k, c.u);
          return `<div class="cmp-bar"><span>${esc(c.u.name)}</span><span><span class="pill" style="background:transparent;border:1px solid var(--grid)"><span class="dot" style="background:${l ? l.color : "var(--nodata)"}"></span> ${esc(valueText(data, k, c.u))}</span>${det ? `<div class="muted" style="font-size:12px;margin-top:3px">${esc(det)}</div>` : ""}</span><span></span></div>`;
        }).join("")}</div>`;
      }
      const { rank, n } = rankOf(data, k);
      const vals = chosen.map((c) => c.u.v[k]).filter((v) => v != null);
      const all = data.units.map((u) => u.v[k]).filter((v) => v != null);
      const lo = Math.min(0, ...all); const hi = Math.max(...all);
      const best = vals.length && m.better !== "neutral" ? (m.better === "low" ? Math.min(...vals) : Math.max(...vals)) : null;
      const avg = data.serbia[k];
      const pct = (v) => ((v - lo) / (hi - lo)) * 100;
      const hint = m.better === "neutral" ? "" : (m.better === "low" ? "Manje je bolje · " : "Više je bolje · ");
      return `<div class="cmp-metric"><h3>${esc(m.label)}</h3><div class="hint">${esc(hint)}crta = ${esc(data.serbiaLabel)} (${fmt(avg, m)}) · ${period}</div>${chosen.map((c) => {
        const v = c.u.v[k]; const det = detailText(k, c.u);
        return `<div class="cmp-bar"><span>${esc(c.u.name)}${v != null && v === best && vals.length > 1 ? `<span class="win">✓</span>` : ""}</span><span class="track">${v != null ? `<span class="fill" style="width:${Math.max(1, pct(v))}%;background:${c.c}"></span>` : ""}${avg != null ? `<span class="avg" style="left:${pct(avg)}%" title="prosek"></span>` : ""}</span><span class="v num">${fmt(v, m)}<br><span class="muted" style="font-weight:400;font-size:12px">${rank[c.u.slug] ? rank[c.u.slug] + ". od " + n : ""}</span></span></div>${det ? `<div class="muted cmp-det">${esc(det)}</div>` : ""}`;
      }).join("")}</div>`;
    }
    function draw() {
      const chosen = sel.map((s, i) => (s ? { u: bySlug[s], c: COLORS[i] } : null)).filter(Boolean);
      if (chosen.length < 2) { render(out, `<p class="muted">Izaberi bar dva mesta.</p>`); return; }
      const keys = data.order.filter((k) => hasData(data, k));
      const html = Object.keys(data.groups).map((g) => {
        const ks = keys.filter((k) => data.metrics[k].group === g);
        if (!ks.length) return "";
        return `<h2 class="cmp-group">${esc(data.groups[g])}</h2>` + ks.map((k) => metricBlock(k, chosen)).join("");
      }).join("");
      render(out, html);
    }
    draw();
  }

  /* ================= PAGE: quiz ================= */
  function initQuiz(data) {
    const steps = [...document.querySelectorAll(".quiz-step")];
    const bar = document.querySelector(".progress i");
    const answers = { weights: {}, size: "any", regions: new Set(), budget: null };
    Object.keys(data.quizWeights).forEach((k) => { answers.weights[k] = ["neto", "cena_m2", "godine_stan", "nezaposlenost", "povezanost"].includes(k) ? 2 : 1; });
    let cur = 0;
    function show(i) {
      cur = i; steps.forEach((s, j) => s.classList.toggle("active", j === i));
      bar.style.width = ((i + 1) / steps.length) * 100 + "%";
      window.scrollTo({ top: document.querySelector(".quiz").offsetTop - 80, behavior: "smooth" });
      if (steps[i].dataset.step === "results") results();
    }
    document.querySelectorAll("[data-next]").forEach((b) => b.addEventListener("click", () => show(Math.min(cur + 1, steps.length - 1))));
    document.querySelectorAll("[data-prev]").forEach((b) => b.addEventListener("click", () => show(Math.max(cur - 1, 0))));
    document.querySelectorAll("[data-restart]").forEach((b) => b.addEventListener("click", () => show(0)));

    // weights UI, grouped by theme
    const wEl = document.getElementById("q-weights");
    const wk = Object.keys(data.quizWeights);
    render(wEl, Object.keys(data.groups).map((g) => {
      const ks = wk.filter((k) => data.metrics[k].group === g);
      if (!ks.length) return "";
      return `<h3 class="q-group">${esc(data.groups[g])}</h3>` + ks.map((k) => {
        const lbl = data.quizWeights[k];
        return `<div class="weight-row"><div><b>${esc(lbl.title)}</b><br><span class="muted" style="font-size:14px">${esc(lbl.hint)}</span></div><div class="seg" data-k="${k}">${["Nebitno", "Malo", "Bitno", "Presudno"].map((l, i) => `<button type="button" data-w="${i}" aria-pressed="${i === answers.weights[k]}">${l}</button>`).join("")}</div></div>`;
      }).join("");
    }).join(""));
    wEl.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-w]"); if (!b) return;
      const seg = b.parentNode; answers.weights[seg.dataset.k] = Number(b.dataset.w);
      seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    });
    document.querySelectorAll("[data-single]").forEach((grp) => grp.addEventListener("click", (e) => {
      const b = e.target.closest(".q-opt"); if (!b) return;
      grp.querySelectorAll(".q-opt").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      answers[grp.dataset.single] = b.dataset.v;
    }));
    document.querySelectorAll("[data-multi]").forEach((grp) => grp.addEventListener("click", (e) => {
      const b = e.target.closest(".q-opt"); if (!b) return;
      const on = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", String(on));
      on ? answers.regions.add(b.dataset.v) : answers.regions.delete(b.dataset.v);
    }));
    const budgetEl = document.getElementById("q-budget");
    if (budgetEl) budgetEl.addEventListener("input", () => { const v = Number(budgetEl.value); answers.budget = v > 0 ? v : null; });

    function scorer(key) {
      const m = data.metrics[key];
      if (isCat(m)) {
        return (u) => {
          const l = levelOf(m, u.c[key]); if (!l) return null;
          return l.score;
        };
      }
      const arr = data.units.map((u) => u.v[key]).filter((v) => v != null).sort((a, b) => a - b);
      return (u) => {
        const v = u.v[key]; if (v == null) return null;
        let lo = 0, hi = arr.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (arr[mid] < v) lo = mid + 1; else hi = mid; }
        const p = arr.length > 1 ? lo / (arr.length - 1) : 0.5;
        return m.better === "low" ? 1 - p : p;
      };
    }
    function results() {
      const keys = Object.keys(data.quizWeights).filter((k) => hasData(data, k));
      const sc = Object.fromEntries(keys.map((k) => [k, scorer(k)]));
      const size = answers.size;
      const cands = data.units.filter((u) => {
        if (answers.regions.size && !answers.regions.has(u.region)) return false;
        const pop = u.population;
        if (pop != null) {
          if (size === "big" && pop < 100000) return false;
          if (size === "mid" && (pop < 30000 || pop >= 100000)) return false;
          if (size === "small" && pop >= 30000) return false;
        }
        if (answers.budget && u.v.cena_m2 != null && u.v.cena_m2 > answers.budget) return false;
        return true;
      });
      const scored = cands.map((u) => {
        let s = 0, w = 0; const why = [];
        keys.forEach((k) => {
          const wt = answers.weights[k]; if (!wt) return;
          let p = sc[k](u);
          if (p == null) { p = 0.5; if (k === "cena_m2" && wt >= 2) why.push("nema podataka o ceni stana"); }
          else if (p >= 0.8 && wt >= 2) why.push(data.quizWeights[k].good);
          s += p * wt; w += wt;
        });
        return { u, score: w ? Math.round((s / w) * 100) : 0, why };
      }).sort((a, b) => b.score - a.score).slice(0, 10);
      const el = document.getElementById("q-results");
      if (!scored.length) { render(el, `<p>Nijedno mesto ne ispunjava sve uslove. Probaj da proširiš region ili budžet.</p>`); return; }
      render(el, scored.map((r, i) => `<div class="result"><span class="medal">${i + 1}</span><div><a href="${BASE}opstina/${r.u.slug}/${IX}"><b>${esc(r.u.name)}</b></a> <span class="pill">${esc(data.regions[r.u.region])}</span><div class="why">${r.why.map((w) => `<span>${esc(w)}</span>`).join("")}</div></div><div class="score num">${r.score}<span class="muted" style="font-size:12px;font-weight:500">/100</span></div></div>`).join("") +
        `<p class="muted" style="margin-top:14px;font-size:14px">Rezultat 0–100 pokazuje koliko je mesto bolje od ostalih po stvarima koje su ti bitne (100 = najbolje u Srbiji po svim izabranim merilima). Ako za neko mesto nema podatka, računa se kao prosečno. Bezbednost i turizam nisu deo kviza jer ti podaci ne opisuju pouzdano svakodnevni život u opštini.</p><p><a class="btn btn-ghost" href="${BASE}uporedi/${IX}?o=${scored.slice(0, 3).map((r) => r.u.slug).join(",")}">Uporedi prva tri →</a></p>`);
    }
    show(0);
  }

  /* ================= boot ================= */
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".script-toggle button").forEach((b) => b.addEventListener("click", () => {
      script = b.dataset.script; store.set("script", script); applyScript();
      const dl = document.getElementById("unit-names");
      if (dl && window.__gzData) dl.innerHTML = window.__gzData.units.map((u) => `<option value="${esc(t(u.name))}">`).join("");
      document.dispatchEvent(new CustomEvent("gz:script"));
    }));
    applyScript();
    const page = document.body.dataset.page;
    if (["home", "compare", "quiz"].includes(page)) {
      loadData().then((data) => {
        window.__gzData = data;
        if (page === "home") initHome(data);
        if (page === "compare") initCompare(data);
        if (page === "quiz") initQuiz(data);
      }).catch((err) => { console.error(err); });
    }
  });
})();
