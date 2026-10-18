// Smart Music Playlist Manager: front end. All algorithms run on the Python server (playlist.py);
// this page only draws the result and what each algorithm did.
const $ = (s) => document.querySelector(s);
const FIELDS = [["title", "Title"], ["artist", "Artist"], ["album", "Album"], ["genre", "Genre"], ["released", "Released"], ["length", "Length"]];
const TINT = { Jazz: ["#4b3a86", "#e4dbff"], Rock: ["#7a3b31", "#ffd9d0"], Pop: ["#2f4d96", "#dbe6ff"], Electronic: ["#1f5f68", "#cdf3f7"],
  "Hip-hop": ["#6e5520", "#ffefc6"], Soul: ["#2a6a45", "#d3f5e1"], Disco: ["#7c2e66", "#ffd6f1"] };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let state = null, view = "list", groups = null, hits = new Set(), fresh = null, selected = null;

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

function art(t) {
  const [bg, fg] = TINT[t.genre] || ["#3a3f4d", "#e6e8ef"];
  return `<div class="art" style="background:${bg};color:${fg}">${esc((t.genre || "?")[0])}</div>`;
}

function rowHtml(t, i) {
  const cls = ["row", hits.has(t.uid) ? "hit" : "", fresh === t.uid ? "new" : "", selected === t.uid ? "sel" : ""].join(" ");
  return `<div class="${cls}" data-uid="${t.uid}" data-i="${i}">
    <span class="num">${i + 1}</span>
    <div class="tt">${art(t)}<div style="min-width:0"><div class="t1">${esc(t.title)}</div>
      <div class="t2"><span class="bd">${esc(t.genre || "—")}</span>${esc(t.artist || "Unknown artist")}</div></div></div>
    <span class="alb">${esc(t.album || "—")}</span><span class="yr">${esc(t.year)}</span><span class="ln">${esc(t.len)}</span>
    <button class="del" type="button" aria-label="Delete ${esc(t.title)}" data-del="${i}"><svg viewBox="0 0 24 24"><path d="M6 12h12"/></svg></button>
  </div>`;
}

// FLIP: remember where rows were, re-render, then slide them from old to new places
function render(animate = true) {
  const box = $("#rows");
  const before = new Map([...box.querySelectorAll(".row")].map((r) => [r.dataset.uid, r.getBoundingClientRect().top]));
  const byUid = new Map(state.tracks.map((t, i) => [t.uid, [t, i]]));
  if (view === "group" && groups) {
    box.innerHTML = groups.buckets.map((b) => `<div class="group-h">${esc(b.key)}<span>${b.uids.length} track${b.uids.length > 1 ? "s" : ""}</span></div>` +
      b.uids.map((u) => rowHtml(...byUid.get(u))).join("")).join("");
  } else {
    box.innerHTML = state.tracks.map(rowHtml).join("");
  }
  if (animate) {
    box.querySelectorAll(".row").forEach((r) => {
      const was = before.get(r.dataset.uid);
      if (was === undefined) return;
      const dy = was - r.getBoundingClientRect().top;
      if (Math.abs(dy) < 1) return;
      r.animate([{ transform: `translateY(${dy}px)` }, { transform: "translateY(0)" }], { duration: 520, easing: "cubic-bezier(.2,.8,.2,1)" });
    });
  }
  $("#ptitle").textContent = `Sample ${state.sample} · ${state.sample_name}`;
  document.querySelectorAll("[data-sample]").forEach((b) => b.classList.toggle("on", b.dataset.sample === state.sample));
  const label = FIELDS.find(([f]) => f === state.sort_field)?.[1] || state.sort_field;
  $("#psub").textContent = `Sorted by ${label.toLowerCase()} · ${state.counts.tracks} tracks · ${state.counts.duration}`;
  $("#sortChips").innerHTML = FIELDS.map(([f, l]) => `<button class="chip ${f === state.sort_field ? "on" : ""}" type="button" data-sort="${f}">${l}</button>`).join("");
  const g = state.counts.genres, top = Object.entries(g).sort((a, b) => b[1] - a[1]).slice(0, 2);
  $("#counters").innerHTML = `<div><b>${state.counts.tracks}</b><span>tracks</span></div><div><b>${state.counts.duration}</b><span>total</span></div>
    <div><b>${Object.keys(g).length}</b><span>genres</span></div>` + top.map(([k, v]) => `<div><b>${v}</b><span>${esc(k)}</span></div>`).join("");
  $("#total").textContent = state.counts.duration;
  $("#listBtn").classList.toggle("on", view === "list");
  document.querySelectorAll("[data-group]").forEach((b) => b.classList.toggle("on", view === "group" && groups?.field === b.dataset.group));
  const hit = box.querySelector(".row.hit, .row.new");
  if (hit) hit.scrollIntoView({ block: "center", behavior: "smooth" });
}

function showOp(o, body) {
  $("#opStructure").textContent = o.structure;
  $("#opName").textContent = o.algorithm;
  $("#opTime").textContent = `${o.micros} µs`;
  $("#opBadges").innerHTML = `<span class="badge on">${esc(o.cost)}</span><span class="badge">${esc(o.name)}</span>`;
  $("#opBody").innerHTML = body;
}

function err(msg) { $("#err").textContent = msg || ""; }

async function run(fn) {
  err("");
  try { await fn(); } catch (e) { err(e.message); showOp({ structure: "Error", algorithm: "Not done", micros: 0, cost: "—", name: "error" }, `<p class="hint">${esc(e.message)}</p>`); }
}

// ---------- operations ----------
async function sortBy(field) {
  const { state: s, op } = await api("/api/sort", { field });
  state = s; view = "list"; hits.clear(); fresh = null; render();
  const label = FIELDS.find(([f]) => f === field)[1];
  const segs = (row) => row.map((seg) => `<div class="seg">${seg.map((v) => `<span>${esc(v)}</span>`).join("")}</div>`).join("");
  let k = 0;
  const lv = (row, cls) => `<div class="lvl ${cls}" style="animation-delay:${(k++) * 0.22}s">${segs(row)}</div>`;
  const split = op.trace.split.map((r) => lv(r, "")).join("");
  const merge = op.trace.merge.slice(1).map((r, i, a) => lv(r, i === a.length - 1 ? "m final" : "m")).join("");
  showOp(op, `<p class="hint">Split into halves until every piece is one track, then merge the pieces back in order of <b>${label.toLowerCase()}</b>. Equal tracks keep their order (stable).</p>
    <div class="lvtag">split</div><div class="levels">${split}</div>
    <div class="lvtag">merge</div><div class="levels">${merge}</div>
    <div class="result">${op.trace.split.length - 1} levels deep for ${s.counts.tracks} tracks: about log₂ n. The linked list was rebuilt in the same order.</div>`);
  const card = document.querySelector(".opcard");
  card.scrollTop = 0;
  setTimeout(() => card.scrollTo({ top: card.scrollHeight, behavior: "smooth" }), k * 220 - 600);   // follow the merge to the final row
}

async function search(field, q) {
  const { state: s, op } = await api("/api/search", { field, q });
  state = s; view = "list"; hits = new Set(op.hits); fresh = null; render();
  const n = s.tracks.length;
  const steps = op.trace.map((st, k) => `<div class="step"><b>step ${k + 1}</b><div class="cells" style="grid-template-columns:repeat(${n},1fr)">${
    Array.from({ length: n }, (_, j) => `<i class="${j === st.mid ? "mid" : j >= st.lo && j < st.hi ? "in" : ""}"></i>`).join("")}</div>
    <span class="steptxt">checked #${st.mid + 1} ${esc(st.title)}</span></div>`).join("");
  const found = op.hits.length ? `${op.hits.length} match${op.hits.length > 1 ? "es" : ""} (${op.mode === "prefix" ? "prefix match" : "exact"})` : "No match";
  showOp(op, `${op.resorted ? `<p class="hint">The list wasn't sorted by ${esc(field)}, so it was sorted first. Binary search needs that.</p>` : ""}
    ${steps}<div class="result"><b>${found}</b> in ${op.trace.length} steps, instead of checking all ${n} tracks.</div>`);
}

async function group(field) {
  const { state: s, op } = await api("/api/group", { field });
  state = s; view = "group"; groups = op; hits.clear(); fresh = null; render();
  const max = Math.max(...op.buckets.map((b) => b.uids.length));
  showOp(op, `<p class="hint">One pass over the playlist: each track dropped into its ${esc(field)} bucket. The order inside each bucket is the order you chose.</p>
    <div class="buckets">${op.buckets.map((b) => `<div class="bucket"><span>${esc(b.key)}</span><div class="barw"><i style="width:${(b.uids.length / max) * 100}%"></i></div><b>${b.uids.length}</b></div>`).join("")}</div>`);
}

async function count() {
  const { state: s, op } = await api("/api/count", {});
  state = s; render(false);
  const c = $("#counters"); c.classList.remove("pulse"); void c.offsetWidth; c.classList.add("pulse");
  const g = s.counts.genres;
  showOp(op, `<p class="hint">Nothing was recounted. These counters are updated every time a track is added or removed, so reading them is instant.</p>
    <div class="kv"><div><b>${s.counts.tracks}</b><span>tracks</span></div><div><b>${s.counts.duration}</b><span>total time</span></div>
    <div><b>${Object.keys(g).length}</b><span>genres</span></div><div><b>${Object.keys(s.counts.artists).length}</b><span>artists</span></div></div>`);
}

async function insert(form) {
  const body = Object.fromEntries(new FormData(form));
  const { state: s, op } = await api("/api/insert", body);
  state = s; view = "list"; hits.clear(); fresh = op.uid; render();
  const n = op.n;
  const steps = op.trace.map((st, k) => `<div class="step"><b>step ${k + 1}</b><div class="cells" style="grid-template-columns:repeat(${n},1fr)">${
    Array.from({ length: n }, (_, j) => `<i class="${j === st.mid ? "mid" : j >= st.lo && j < st.hi ? "in" : ""}"></i>`).join("")}</div>
    <span class="steptxt">compared with #${st.mid + 1} ${esc(st.title)}</span></div>`).join("");
  showOp(op, `<p class="hint">Binary search found the slot after any equal tracks (${op.trace.length} steps), then the new node was spliced into the linked list by rewiring the links on both sides. Nothing else moved.</p>
    ${steps}
    <div class="nodes"><span class="node">${esc(op.before ?? "start")}</span><span class="link">⇄</span><span class="node new">${esc(body.title)}</span><span class="link">⇄</span><span class="node">${esc(op.after ?? "end")}</span></div>
    <div class="result">Inserted at position ${op.index + 1}, sorted order kept.</div>`);
  form.reset();
}

async function del(i, rowEl) {
  rowEl?.classList.add("out");
  await new Promise((r) => setTimeout(r, 300));
  const { state: s, op } = await api("/api/delete", { index: i });
  state = s; hits.clear(); fresh = null;
  if (view === "group" && groups) groups = (await api("/api/group", { field: groups.field })).op;
  render();
  showOp(op, `<p class="hint">The node was unlinked: its neighbours now point to each other. The counters went down by one. Nothing else moved.</p>
    <div class="nodes"><span class="node">${esc(op.before ?? "start")}</span><span class="link">⇄</span><span class="node gone">${esc(op.title)}</span><span class="link">⇄</span><span class="node">${esc(op.after ?? "end")}</span></div>
    <div class="result">Removed “${esc(op.title)}” from position ${op.index + 1}.</div>`);
}

async function speedRace() {
  showOp({ structure: "Speed race", algorithm: "Racing…", micros: 0, cost: "50,000 tracks", name: "race" },
    `<p class="hint">Generating 50,000 tracks and timing both ways. The first run takes a few seconds.</p>`);
  $("#opTime").textContent = "";
  const { race: r } = await api("/api/race", {});
  const fmt = (v, unit) => `${v.toLocaleString(undefined, { maximumFractionDigits: unit === "µs" ? 1 : 3 })} ${unit}`;
  const box = (title, slowName, slow, fastName, fast, unit) => {
    const ratio = slow / fast, w = Math.max(.6, (fast / slow) * 100);
    return `<div class="rbox"><h3>${title}</h3>
      <div class="rline"><span>${slowName}</span><div class="barw"><i style="width:100%"></i></div><b>${fmt(slow, unit)}</b></div>
      <div class="rline us"><span>${fastName}</span><div class="barw"><i style="width:${w}%"></i></div><b>${fmt(fast, unit)}</b></div>
      <div class="xfast">${Math.round(ratio).toLocaleString()}× faster</div></div>`;
  };
  showOp({ structure: "Speed race", algorithm: `${r.n.toLocaleString()} tracks`, micros: 0, cost: "measured now", name: "race" },
    `<div class="race">${box("Search one title", "Linear scan · O(n)", r.linear_us, "Binary search · O(log n)", r.binary_us, "µs")}
      ${box("Insert one track in order", "Append + re-sort", r.resort_ms, "Search + splice", r.splice_ms, "ms")}</div>`);
  $("#opTime").textContent = "";
}

// ---------- events ----------
document.querySelectorAll("[data-sample]").forEach((b) => b.addEventListener("click", () => run(async () => {
  state = (await api("/api/load", { sample: b.dataset.sample })).state; view = "list"; hits.clear(); fresh = null; render();
  showOp({ structure: `Sample ${state.sample}`, algorithm: state.sample_name, micros: 0, cost: `${state.counts.tracks} tracks`, name: "loaded" },
    `<p class="hint">Loaded from <b>sample_data/</b>, sorted by ${esc(state.sort_field)}. Every operation now runs on this sample.</p>`);
  $("#opTime").textContent = "";
})));
$("#raceBtn").addEventListener("click", () => run(speedRace));
$("#sortChips").addEventListener("click", (e) => { const b = e.target.closest("[data-sort]"); if (b) run(() => sortBy(b.dataset.sort)); });
$("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); run(() => search($("#sfield").value, $("#q").value)); });
document.querySelectorAll("[data-group]").forEach((b) => b.addEventListener("click", () => run(() => group(b.dataset.group))));
$("#countBtn").addEventListener("click", () => run(count));
$("#listBtn").addEventListener("click", () => { view = "list"; render(); });
$("#addForm").addEventListener("submit", (e) => { e.preventDefault(); run(() => insert(e.target)); });
$("#reset").addEventListener("click", () => run(async () => { state = (await api("/api/reset", {})).state; view = "list"; hits.clear(); fresh = null; render(); }));
$("#rows").addEventListener("click", (e) => {
  const d = e.target.closest("[data-del]");
  if (d) { e.stopPropagation(); return run(() => del(Number(d.dataset.del), d.closest(".row"))); }
  const r = e.target.closest(".row");
  if (r) { selected = Number(r.dataset.uid); nowPlaying(); render(false); }
});
$("#playBtn").addEventListener("click", () => { if (state.tracks.length) { selected = selected ?? state.tracks[0].uid; nowPlaying(); render(false); } });

// decorative now-playing bar (no audio)
let tick = null;
function nowPlaying() {
  const t = state.tracks.find((x) => x.uid === selected);
  if (!t) return;
  $("#nowTitle").textContent = t.title;
  $("#nowSub").textContent = `${t.artist} · ${t.year}`;
  $("#nowArt").outerHTML = art(t).replace('class="art"', 'class="art" id="nowArt"');
  let s = 0; clearInterval(tick);
  tick = setInterval(() => { s = (s + 1) % (t.length + 1); $("#elapsed").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; $("#prog").style.width = `${(s / t.length) * 100}%`; }, 1000);
  $("#total").textContent = t.len;
}

run(async () => {
  state = (await api("/api/state")).state; render(false);
  // Open the page mid-take from the address bar, e.g. ?run=sample:B,sort:length or ?search=lose%20yourself&field=title
  const q = new URLSearchParams(location.search);
  for (const step of (q.get("run") || "").split(",").filter(Boolean)) {
    const [what, arg = "", arg2 = ""] = step.split(":");
    if (what === "sample") document.querySelector(`[data-sample="${arg.toUpperCase()}"]`)?.click();
    if (what === "sort") await sortBy(arg);
    if (what === "group") await group(arg || "genre");
    if (what === "count") await count();
    if (what === "race") await speedRace();
    if (what === "search") { $("#q").value = arg2; $("#sfield").value = arg; await search(arg, arg2); }
    await new Promise((r) => setTimeout(r, 400));
  }
  if (q.get("search")) { $("#q").value = q.get("search"); $("#sfield").value = q.get("field") || "title"; await search($("#sfield").value, q.get("search")); }
});
