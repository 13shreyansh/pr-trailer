"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => `${Math.round(x * 100)}%`;
let DATA = null;

const LANE = {
  return: { label: "Sent back to the agent", short: "Sent back", icon: "↩" },
  light: { label: "Quick check", short: "Quick check", icon: "✓" },
  targeted: { label: "Targeted review", short: "Targeted review", icon: "◎" },
  full: { label: "Full read", short: "Full read", icon: "!" },
};
const KIND = { block: "Proven problem", refusal: "Question for you", warn: "Worth a look", note: "FYI" };
const lanePill = (t) => `<span class="pill lane-${t}"><span class="dot"></span>${LANE[t].short}</span>`;
const vClass = (v) => (v === "yes" ? "yes" : v === "no" ? "no" : "unknown");
const vText = (v) => (v === "yes" ? "Yes" : v === "no" ? "No" : "Not proven");

// ---------- decisions (per browser) ----------
const store = {
  get(id) { try { return JSON.parse(localStorage.getItem("prt:" + id) || "null"); } catch { return null; } },
  set(id, v) { try { localStorage.setItem("prt:" + id, JSON.stringify(v)); } catch {} },
  clear(id) { try { localStorage.removeItem("prt:" + id); } catch {} },
};

// ---------- helpers ----------
function questions(p) { return p.spots.filter((s) => s.kind === "refusal"); }
function readSummary(p) {
  const s = p.stats, t = p.decision.tier;
  if (t === "return") return `<b>0 lines</b> to read until the agent fixes it`;
  if (t === "full") return `<b>All ${p.lines_changed} changed lines</b>, by policy`;
  if (!s.lines_to_read) return `<b>0 lines</b> to read${questions(p).length ? `, ${questions(p).length} question` : ", watch the evidence"}`;
  return `<b>${s.lines_to_read} of ${s.codebase_lines}</b> lines to read`;
}
function bannerText(p) {
  const t = p.decision.tier, q = questions(p).length, s = p.stats;
  if (t === "return") return { big: "Sent back to the agent. Nothing for you to read yet.", sub: p.decision.why.replace(/\(s\)/g, "s") + " The proof is below, so you don't have to take our word for it." };
  if (t === "light") return { big: "Quick check: watch the evidence, then sign.", sub: "Every acceptance criterion has passing evidence, there are no open questions, and the change is easy to undo." };
  if (t === "full") return { big: "Full read required by policy.", sub: p.decision.why + " The map and evidence below are your guide." };
  return { big: s.lines_to_read ? `Read ${s.lines_to_read} lines and answer ${q} question${q === 1 ? "" : "s"}.` : `Answer ${q} question${q === 1 ? "" : "s"}. No code needs reading.`,
    sub: `Everything else in this PR is covered by evidence. You review ${s.lines_to_read ? pct(s.lines_to_read / s.codebase_lines) + " of the codebase" : "no code"}, not the whole diff.` };
}

// ---------- router ----------
function route() {
  const h = location.hash || "#/";
  document.querySelectorAll(".top nav a[data-nav]").forEach((a) => a.classList.remove("on"));
  const nav = (k) => { const a = $(`.top nav a[data-nav="${k}"]`); if (a) a.classList.add("on"); };
  const m = h.match(/^#\/pr\/(PR-\d+)/);
  if (m) { const p = DATA.prs.find((x) => x.id === m[1]); if (p) { renderPR(p); return; } }
  if (h.startsWith("#/how")) { nav("how"); renderHow(); }
  else if (h.startsWith("#/proof")) { nav("proof"); renderProof(); const a = h.split("#")[2]; if (a) { setTimeout(() => { const el = document.getElementById(a); if (el) el.scrollIntoView(); }, 30); return; } }
  else { nav("inbox"); renderInbox(); }
  window.scrollTo(0, 0);
}

// ---------- inbox ----------
function prRow(p) {
  const d = store.get(p.id);
  const right = d ? `<span class="done-badge ${d.verdict}">${d.verdict === "approved" ? "Approved" : "Denied"} by you</span>` : lanePill(p.decision.tier);
  return `<a class="card prrow" href="#/pr/${p.id}">
    <div class="id">${p.id}</div>
    <div><div class="t">${esc(p.title)}</div><div class="r">${esc(p.requirement.id)} · ${esc(p.requirement.title)} · owner ${esc(p.signoff.owner)}</div></div>
    <div class="read">${readSummary(p)}</div>
    <div class="dec">${right}</div></a>`;
}
function sprintViz() {
  const E = DATA.effort, T = E.strategies.trailer;
  const byId = Object.fromEntries(DATA.prs.map((p) => [p.id, p]));
  const rows = [...T.per_pr].sort((a, b) => a.pr.localeCompare(b.pr)).map((r, idx) => {
    const p = byId[r.pr], t = p.decision.tier, hl = new Set(r.hl);
    const cells = Array.from({ length: r.diff_len }, (_, i) => `<i class="${hl.has(i) ? "hl" : ""}"></i>`).join("");
    const q = p.spots.filter((x) => x.kind === "refusal").length;
    const cost = t === "return" ? "1 line: why it went back" : r.lines ? `${r.lines} lines` : q ? `0 lines, ${q} question${q > 1 ? "s" : ""}` : "0 lines: watch the video";
    return `<a class="srow lane-${t}" style="--i:${idx}" href="#/pr/${r.pr}"><span class="sid">${r.pr}</span><span class="stitle">${esc(r.title)}</span><span class="cells">${cells}</span><span class="scost">${lanePill(t)}<b>${cost}</b></span></a>`;
  }).join("");
  return `<div class="card sprint" id="sprint">
    <div class="sprint-head">
      <div><div class="eyebrow">This sprint at Nordbank</div><h2 class="sprint-count"><span id="scount">${E.total_diff_lines}</span> <span id="slabel">lines changed by the agent</span> <span class="sof">of ${E.total_diff_lines} changed</span></h2></div>
      <button class="btn" id="narrow" type="button">Run PR Trailer on the sprint</button>
    </div>
    <p class="muted small" id="scap">Each square is one line of the agent's diff, one row per pull request. Reading all of it line by line is the job nobody can keep up with.</p>
    <div class="srows">${rows}</div>
  </div>`;
}
function wireSprint() {
  const E = DATA.effort, T = E.strategies.trailer, box = $("#sprint"), btn = $("#narrow");
  if (!box) return;
  const count = $("#scount"), label = $("#slabel"), cap = $("#scap");
  const go = () => {
    if (box.classList.contains("narrowed")) return;
    box.classList.add("narrowed"); btn.textContent = "Show every line again";
    const from = E.total_diff_lines, to = T.lines_total, t0 = performance.now();
    const step = (now) => { const k = Math.min(1, (now - t0) / 900); count.textContent = Math.round(from + (to - from) * k); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
    label.textContent = "lines need a human";
    cap.innerHTML = `Bright squares are the ${T.lines_total} lines a person reads in total. Seven PRs went back to the agent with the failure reproduced: no code to read, just one line saying why. Two were proved by tests and a recorded video. Four need a person, and only where a question is open. <b>All 8 planted bugs are in front of you after ${T.lines_for_all} lines.</b> Reading the diff top to bottom, the last one shows up at line ${E.strategies.diff.lines_for_all}.`;
  };
  btn.onclick = () => {
    if (box.classList.contains("narrowed")) { box.classList.remove("narrowed"); btn.textContent = "Run PR Trailer on the sprint"; count.textContent = E.total_diff_lines; label.textContent = "lines changed by the agent"; return; }
    go();
  };
  const io = new IntersectionObserver((en) => { if (en[0].isIntersecting) { setTimeout(go, 2200); io.disconnect(); } }, { threshold: 0.3 });
  io.observe(box);
}

function renderInbox() {
  const S = DATA.bench.samples, E = DATA.effort, C = DATA.chat_eval, A = DATA.ai && DATA.ai.summary, H = DATA.bench.heldout;
  const v5 = C && C.ledger.find((r) => r.version === C.shipped);
  const needs = DATA.prs.filter((p) => p.decision.tier !== "return");
  const back = DATA.prs.filter((p) => p.decision.tier === "return");
  const order = { full: 0, targeted: 1, light: 2 };
  needs.sort((a, b) => order[a.decision.tier] - order[b.decision.tier]);
  const lanes = ["return", "light", "targeted", "full"].map((t) => ({ t, n: DATA.prs.filter((p) => p.decision.tier === t).length }));
  const laneWhy = { return: "We reproduced a real failure, so the agent gets a fix list. You read one line: why.", light: "Every criterion has passing evidence and a recorded video. Glance and sign.",
    targeted: "Mostly proven. You answer the open questions and read only the lines tied to them.", full: "Login security. Policy says a person reads all of it, with our map as a guide." };
  $("#app").innerHTML = `
  <section class="story">
    <div class="eyebrow">Tieto challenge: earned trust in AI code · a working demo</div>
    <div class="story-grid">
      <div class="story-main">
        <h1>An AI agent changed ${E.total_diff_lines} lines of a bank's code this sprint. <span class="accent">You need to read ${E.strategies.trailer.lines_total}.</span></h1>
        <div class="cta"><a class="btn big" href="#/pr/PR-109">Open the PR waiting for you →</a><a class="btn ghost big" href="#/pr/PR-110">See one sent back with proof</a></div>
      </div>
      <div class="story-side">
        <p class="lede">Nordbank is a made-up bank with real-looking code: payments, fees, statements, logins. Its coding agent opened ${DATA.prs.length} pull requests. You are Aino, the payments owner. If a merge breaks something at 3 a.m., it's your name on it. <b>PR Trailer runs every PR in a sandbox first, sends the broken ones back with proof, and points you at the few lines only a person can judge.</b></p>
      </div>
    </div>
  </section>
  ${sprintViz()}
  <h2 class="mt">What happened to the ${DATA.prs.length} pull requests</h2>
  <div class="lanes">${lanes.map(({ t, n }) => `<div class="card lanecard lane-${t}"><div class="ln">${n}</div><div>${lanePill(t)}<p class="small">${laneWhy[t]}</p></div></div>`).join("")}</div>
  <h2 class="mt">Why you can trust the narrowing</h2>
  <div class="kpis">
    <a class="card kpi" href="#/proof#effort"><div class="n">${E.strategies.trailer.lines_for_all} <small>vs ${E.strategies.diff.lines_for_all}</small></div><div class="l">lines read before all 8 planted bugs are in front of you, vs reading the diff top to bottom</div><div class="go">See the proof →</div></a>
    <a class="card kpi" href="#/proof#bench"><div class="n">${Math.round(S.false_alarm_rate * S.clean)}/${S.clean}</div><div class="l">clean PRs wrongly sent back. Only a reproduced failure may block, never an opinion</div><div class="go">See the proof →</div></a>
    <a class="card kpi" href="#/proof#bench"><div class="n">${H ? Math.round(H.catch_rate * H.mutants) + "/" + H.mutants : "–"}</div><div class="l">new bugs, generated after the tool was built and never tuned on, sent back or put in front of a human</div><div class="go">See the proof →</div></a>
    ${A ? `<a class="card kpi" href="#/proof#reviewers"><div class="n">${S.buggy - S.escaped}/${S.buggy} <small>vs ${A.devin.caught} and ${A.codex.caught}</small></div><div class="l">planted bugs caught, vs Devin and Codex AI reviews on the same pull requests</div><div class="go">See the proof →</div></a>` : ""}
    ${v5 ? `<a class="card kpi" href="#/proof#chat"><div class="n">${pct(v5.heldout.all)}</div><div class="l">of held-out questions answered correctly and grounded by the PR assistant (graded, ${C.cases.dev + C.cases.heldout + C.cases.heldout2} questions)</div><div class="go">See the proof →</div></a>` : ""}
  </div>
  <div class="section-head"><div><h2>Waiting for your decision</h2><div class="muted">${needs.length} PRs. Open one to see exactly what to read.</div></div></div>
  <div class="prlist">${needs.map(prRow).join("")}</div>
  <details class="sentback"><summary><h2>Sent back to the agent</h2><span class="muted">${back.length} PRs where we reproduced a problem. Open one to see the proof.</span></summary>
  <div class="prlist">${back.map(prRow).join("")}</div></details>`;
  wireSprint();
}

// ---------- PR page ----------
function renderPR(p) {
  const t = p.decision.tier, b = bannerText(p), s = p.stats;
  $("#app").innerHTML = `
  <div class="pr-head">
    <a class="back" href="#/">← All pull requests</a>
    <div class="meta"><span class="tag">${p.id}</span><span class="tag">${esc(p.requirement.id)}</span><span>opened by ${esc(p.author || "coding agent")}</span><span>·</span><span>${p.lines_changed} lines changed in ${s.files_changed} file${s.files_changed === 1 ? "" : "s"}</span><span>·</span><span>owner ${esc(p.signoff.owner)}</span></div>
    <h1 style="margin-top:10px">${esc(p.title)}</h1>
  </div>
  <div class="banner lane-${t}">
    <div class="icon">${LANE[t].icon}</div>
    <div><div class="big">${esc(b.big)}</div><div class="sub">${esc(b.sub)}</div></div>
    <div class="stat"><b>${t === "return" ? 0 : t === "full" ? p.lines_changed : s.lines_to_read}</b>lines to read of ${s.codebase_lines}</div>
  </div>
  <div class="layout">
    <nav class="steps">
      <a href="#s-outcome"><span>1</span>Outcome</a>
      <a href="#s-how"><span>2</span>How to look at it</a>
      <a href="#s-impact"><span>3</span>Impact map</a>
      <a href="#s-read"><span>4</span>${t === "return" ? "Why it went back" : "What to read"}</a>
      <a href="#s-evidence"><span>5</span>Sandbox evidence</a>
      <a href="#s-ask"><span>6</span>Ask about it</a>
      <a href="#s-decide"><span>7</span>${t === "return" ? "What happens next" : "Decide"}</a>
      <div class="hint">You are the approver: accountable that this does what it should, and nothing else.</div>
    </nav>
    <div>
      ${secOutcome(p)}${secHow(p)}${secImpact(p)}${secRead(p)}${secEvidence(p)}${secAsk(p)}${secDecide(p)}
    </div>
  </div>`;
  window.scrollTo(0, 0);
  wireSteps(); wireChat(p); wireDecide(p); wireAudio(p);
  if (p.sequence && window.mermaid) {
    try { mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" }); mermaid.run({ querySelector: ".mermaid" }); } catch (e) { console.warn(e); }
  }
}


function agentDecisions(p) {
  const D = p.agent_decisions;
  if (!D || !D.length) return "";
  return `<div class="card pad decisions"><h3>Decisions the agent made, and why</h3>
    <p class="small muted" style="margin:0 0 10px">Read out of the diff by Gemini, as advice. A reason is shown only if it is a word-for-word quote from the agent's description or code comments; otherwise it says none was given.</p>
    <div class="dec-row dec-head"><span>Decision</span><span>Agent's reason</span><span>Advice</span></div>
    ${D.map((d) => `<div class="dec-row"><div class="dw"><b>${esc(d.decision)}</b><span class="mono small">${esc(d.file || "")}</span></div>
      <div class="dr">${d.agent_reason ? `<span class="dl">Agent's reason:</span> <q>${esc(d.agent_reason)}</q>` : `<span class="small muted">The agent gave no reason.</span>`}</div>
      <div class="dv ${/^nothing flagged/i.test(d.review) ? "ok" : "flag"}">${esc(d.review)}</div></div>`).join("")}</div>`;
}

const ico = (d) => `<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const FMT = {
  video: [ico('<rect x="2.5" y="4" width="15" height="12" rx="2"/><path d="M8.5 7.6v4.8l4-2.4z" fill="currentColor" stroke="none"/>'), "#s-media"],
  table: [ico('<rect x="2.5" y="3.5" width="15" height="13" rx="2"/><path d="M2.5 8h15M10 8v8.5"/>'), "#s-table"],
  diagram: [ico('<circle cx="4.5" cy="5" r="2"/><circle cx="15.5" cy="15" r="2"/><path d="M6.5 5h5a3 3 0 0 1 3 3v5"/>'), "#s-seq"],
  audio: [ico('<path d="M3.5 8v4M7 5.5v9M10.5 7.5v5M14 4v12M17 8.5v3"/>'), null],
  read: [ico('<path d="M4 5h12M4 10h12M4 15h7"/>'), "#s-read"],
  fixlist: [ico('<path d="M7.5 4.5 3.5 8.5l4 4"/><path d="M3.5 8.5h8.5a4 4 0 0 1 0 8H8"/>'), "#s-decide"],
};
function secHow(p) {
  const cards = p.formats.map((f) => {
    const [icon, href] = FMT[f.kind] || ["•", null];
    const extra = f.kind === "audio" ? `<div class="audio"><button class="btn" type="button" id="play">▶ Play the briefing</button><span class="small muted" id="audiohint">About ${Math.max(20, Math.round(p.briefing.split(" ").length / 2.6))} seconds, read aloud by your browser.</span></div><details class="small"><summary>Read the transcript</summary><p>${esc(p.briefing)}</p></details>` : "";
    return `<div class="card fmt fmt-${f.kind}"><div class="fi">${icon}</div><div><h3>${href ? `<a href="${href}">${esc(f.title)}</a>` : esc(f.title)}</h3><p class="small why"><span class="wl">Why this format</span>${esc(f.rule)}</p>${extra}</div></div>`;
  }).join("");
  return sec("s-how", "02", "How to look at this change",
    "Not every change is best understood by reading code. These are picked by simple rules from what the PR touches, and each one says which rule picked it.",
    `<div class="fmts">${cards}</div>`);
}
function wireAudio(p) {
  const b = $("#play");
  if (!b) return;
  if (!("speechSynthesis" in window)) { b.disabled = true; $("#audiohint").textContent = "Your browser can't read aloud; use the transcript."; return; }
  b.onclick = () => {
    if (speechSynthesis.speaking) { speechSynthesis.cancel(); b.textContent = "▶ Play the briefing"; return; }
    const u = new SpeechSynthesisUtterance(p.briefing.replace(/`/g, "").replace(/_/g, " "));
    u.lang = "en-GB"; u.rate = 1.02;
    u.onend = () => (b.textContent = "▶ Play the briefing");
    speechSynthesis.speak(u); b.textContent = "■ Stop";
  };
  window.addEventListener("hashchange", () => speechSynthesis.cancel(), { once: true });
}
function sandboxCard(p) {
  const sb = p.sandbox;
  return `<div class="card pad sandbox"><h3>What ran in the sandbox</h3><ul class="checks">${sb.items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`;
}
function tablesCard(p) {
  if (!p.tables || !p.tables.length) return "";
  return `<div class="card pad" id="s-table" style="margin-top:14px"><h3>Same inputs, main vs this PR</h3><p class="small muted" style="margin:0 0 10px">We ran the old and the new version of the money code on the same amounts. Highlighted rows give a different answer.</p>
    ${p.tables.map((tb) => `<div class="scroll"><table class="ba-table"><thead><tr><th class="mono">${esc(tb.file)}</th><th>main</th><th>this PR</th></tr></thead><tbody>${tb.rows.map((r) => `<tr class="${r.differs ? "diff-row" : ""}"><td class="mono small">${esc(r.call)}</td><td class="mono">${esc(r.main)}</td><td class="mono">${esc(r.pr)}${r.differs ? " ←" : ""}</td></tr>`).join("")}</tbody></table></div>`).join("")}</div>`;
}

function sec(id, num, title, desc, body) {
  return `<section class="step" id="${id}"><div class="step-title"><span class="num">${num}</span><h2>${title}</h2></div><p class="step-desc">${desc}</p>${body}</section>`;
}

function secOutcome(p) {
  const o = p.outcome;
  return sec("s-outcome", "01", "The outcome you are approving",
    `Start from what the change is supposed to achieve, not from the code. The requirement: <b>${esc(p.requirement.title)}</b>.`,
    `<div class="card pad" style="margin-bottom:12px"><div class="eyebrow">Requirement ${esc(p.requirement.id)}</div><div style="font-size:17px">${esc(o.statement)}</div></div>
     <div class="verdicts">
       <div class="verdict ${vClass(o.does_it.verdict)}"><div class="q">Does it do what it should?</div><div class="a">${vText(o.does_it.verdict)}</div><div class="small">${esc(o.does_it.why)}</div></div>
       <div class="verdict ${vClass(o.nothing_else.verdict)}"><div class="q">Does it do anything else?</div><div class="a">${o.nothing_else.verdict === "yes" ? "No, nothing else" : o.nothing_else.verdict === "no" ? "Yes, it does" : "Not proven"}</div><div class="small">${esc(o.nothing_else.why)}</div></div>
     </div>
     ${p.description ? `<p class="quote">"${esc(p.description)}" <span class="muted" style="font-style:normal">(the agent's own description)</span></p>` : ""}
     ${agentDecisions(p)}`);
}

function secImpact(p) {
  const s = p.stats, d = p.danger;
  const untouched = s.files - s.files_changed - s.files_affected;
  const order = { changed: 0, deleted: 0, affected: 1, untouched: 2 };
  const files = [...p.map].sort((a, b) => order[a.status] - order[b.status]);
  const fileHtml = files.map((f) => {
    const bars = f.lines.map(([len, ind, k]) => `<div class="${k}" style="width:${Math.max(3, Math.min(len, 80)) * 1.6}px;margin-left:${Math.min(ind, 16) * 1.6}px"></div>`).join("");
    const label = f.status === "changed" ? "changed" : f.status === "deleted" ? "deleted" : f.status === "affected" ? "depends on the change" : "untouched";
    return `<div class="file ${f.status}" title="${esc(f.path)}"><div class="fn">${esc(f.path)}</div><div class="fs">${f.n} lines · ${label}</div><div class="bars">${bars}</div>${f.why.length ? `<div class="why">${f.why.map(esc).join("<br>")}</div>` : ""}</div>`;
  }).join("");
  const reach = [...d.surfaces.map((x) => `<span class="tag">${esc(x)}</span>`), ...d.tables.map((x) => `<span class="tag">table ${esc(x)}</span>`)];
  return sec("s-impact", "03", "What this PR touches in the codebase",
    `The whole codebase, one tile per file, one bar per line. Orange is what the PR changed. Red is where we want your eyes. Faded files are untouched, so you can ignore them.`,
    `<div class="card pad">
      <div class="map-head">
        <div class="m"><b>${s.files_changed} of ${s.files}</b>files changed</div>
        <div class="m"><b>${s.files_affected}</b>more depend on them</div>
        <div class="m"><b>${untouched}</b>untouched</div>
        <div class="m"><b>${t2(d.door)}</b>if it goes wrong</div>
      </div>
      <div class="map">${fileHtml}</div>
      <div class="legend"><span><i style="background:#ea8a3e"></i>changed line</span><span><i style="background:var(--red)"></i>flagged for you</span><span><i style="background:#8fb0ff"></i>context you read</span><span><i style="background:var(--purple)"></i>calls the changed code</span><span><i style="background:#d9d6cc"></i>untouched</span></div>
      <div class="reach">Reaches: ${reach.length ? reach.join("") : '<span class="muted">nothing outside the changed files</span>'}<span class="muted">· blast radius ${esc(d.blast_radius)}</span></div>
      <p class="small muted" style="margin:12px 0 0">${esc(d.reasons.join(" "))}</p>
    </div>`);
}
function t2(door) { return door === "one-way" ? "Hard to undo" : door.startsWith("two-way, with") ? "Revert leaves traces" : "Easy to undo"; }

let SHOWN = new Set();
function codeBlock(s) {
  if (!s.snippet) return "";
  const key = s.file + ":" + s.snippet.map((l) => l.n).join(",");
  const lines = s.snippet.map((l) => s.file + ":" + l.n);
  if (SHOWN.has(key) || lines.every((k) => SHOWN.has(k))) return `<div class="code"><div class="file-label">Same lines as shown above (${esc(s.file)}${s.line ? ":" + s.line : ""})</div></div>`;
  SHOWN.add(key); lines.forEach((k) => SHOWN.add(k));
  return `<div class="code"><div class="file-label">${esc(s.file)}</div>${s.snippet.map((l) =>
    `<div class="ln${l.hl ? " hl" : l.changed ? " changed" : ""}"><span class="no">${l.n}</span><span class="mk">${l.changed ? "+" : ""}</span><span>${esc(l.text)}</span></div>`).join("")}</div>`;
}
function spotCard(s) {
  const where = s.file ? `${esc(s.file)}${s.line ? ":" + s.line : ""}` : "";
  return `<div class="card spot"><div class="spot-head"><span class="kind ${s.kind}">${KIND[s.kind]}</span>
    <div><div class="w">${esc(s.what)}</div><div class="y">${esc(s.why)}</div></div>
    <div class="o">${where ? `<span class="mono">${where}</span><br>` : ""}${s.owner ? "ask " + esc(s.owner) : ""}</div></div>${codeBlock(s)}</div>`;
}
function secRead(p) {
  SHOWN = new Set();
  const t = p.decision.tier;
  const main = p.spots.filter((s) => s.kind !== "note");
  const notes = p.spots.filter((s) => s.kind === "note");
  const diff = `<details class="diff"><summary>Show the full diff (${p.lines_changed} lines) anyway</summary>${p.diff.map((d) =>
    `<div class="udiff">${(d.unified || "(no text diff)").split("\n").map((l) => `<div class="${l.startsWith("@@") ? "h" : l.startsWith("+") && !l.startsWith("+++") ? "a" : l.startsWith("-") && !l.startsWith("---") ? "d" : ""}">${esc(l) || " "}</div>`).join("")}</div>`).join("")}</details>`;
  let body;
  if (!main.length) body = `<div class="card zero"><b>Nothing to read.</b>Every changed line ran under this requirement's tests, there are no open questions, and nothing outside the requirement changed. Check the evidence and sign.</div>`;
  else body = main.map(spotCard).join("");
  if (notes.length) body += `<details class="diff"><summary>${notes.length} smaller note${notes.length > 1 ? "s" : ""}</summary>${notes.map(spotCard).join("")}</details>`;
  return sec("s-read", "04", t === "return" ? "Why it was sent back" : "The lines that need a human",
    t === "return" ? "These problems were reproduced by running the code, not guessed. The agent gets them as a fix list. The questions stay open for when it comes back."
      : `Out of ${p.stats.codebase_lines} lines in the codebase and ${p.lines_changed} in this diff, these are the places worth your attention, with the reason and who to ask.`,
    body + diff);
}

function evText(f) {
  const e = String(f.evidence || "");
  if (!e) return f.verification;
  return f.verification + ": " + (e.length > 220 ? e.slice(0, 220) + "…" : e);
}
function res(r) { return `<span class="res ${r === "pass" ? "pass" : r === "fail" ? "fail" : "none"}">${esc(r)}</span>`; }
function secEvidence(p) {
  const c = p.checked, so = p.signoff;
  const rows = p.evidence.map((e) => `<tr><td><b>${e.ac}</b></td><td>${esc(e.text)}${e.claimed ? "" : ' <span class="muted small">(not claimed by this PR)</span>'}</td>
    <td>${e.tests.length ? e.tests.map((t) => `<div class="mono small">${esc(t.id.split(".").pop())}</div>`).join("") : '<span class="res none">no test</span>'}</td>
    <td>${e.tests.map((t) => `<div>${res(t.base)}</div>`).join("") || "–"}</td><td>${e.tests.map((t) => `<div>${res(t.head)}</div>`).join("") || "–"}</td></tr>`).join("");
  const proven = p.findings.filter((f) => f.verified);
  const media = p.media ? `<div class="card pad" id="s-media" style="margin-top:14px"><h3>Watch it work</h3><p class="small muted" style="margin:0 0 10px">Recorded by a browser robot running the acceptance tests on this PR.</p>
      <div class="media"><video src="${p.media.video}" controls muted playsinline preload="metadata"></video>
      <div class="ba"><figure><img src="${p.media.before}" alt="Before"><figcaption>Before (main)</figcaption></figure><figure><img src="${p.media.after}" alt="After"><figcaption>After (this PR)</figcaption></figure></div></div></div>` : "";
  const seq = p.sequence ? `<div class="card pad" id="s-seq" style="margin-top:14px"><h3>What happens when this code runs</h3><p class="small muted" style="margin:0 0 10px">Generated from the code that changed, from the entry point down to the database.</p><pre class="mermaid">${esc(p.sequence)}</pre></div>` : "";
  return sec("s-evidence", "05", "The sandbox evidence", "Everything below was produced by running the code, not by reading it. This is why you don't have to read the rest.",
    `${sandboxCard(p)}<div class="card scroll" style="margin-top:14px"><table><thead><tr><th></th><th>Acceptance criterion</th><th>Test</th><th>Main</th><th>This PR</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${proven.length ? `<div class="card pad" style="margin-top:14px"><h3>Problems we reproduced</h3>${proven.map((f) => `<p style="margin:8px 0"><span class="kind block">${esc(f.rule)}</span> <b>${esc(f.title)}</b><br><span class="small muted">${esc(evText(f))}</span></p>`).join("")}</div>` : ""}
    ${tablesCard(p)}${media}${seq}
    <div class="grid g2" style="margin-top:14px">
      <div class="card pad"><h3>What we checked</h3><ul class="checks">${so.checked.map((x) => `<li>${esc(x)}</li>`).join("")}<li>${c.rules.length} rule packs: ${esc(c.rules.join(", "))}</li></ul></div>
      <div class="card pad"><h3>What we did not check</h3><ul class="checks no">${so.not_checked.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    </div>`);
}

function suggestions(p) {
  const t = p.decision.tier, q = [];
  if (t === "return") q.push("Why was this sent back?", "How do you know it's really broken?");
  else q.push("What exactly does this change?", "What could go wrong if I merge it?");
  if (questions(p).length) q.push("Explain the open question in plain words");
  q.push("Which tests prove the requirement?");
  return q.slice(0, 4);
}
function secAsk(p) {
  return sec("s-ask", "06", "Ask about this PR", "Ask anything about the change. Answers come only from this PR's code, tests and findings, with file and line, and say so when something was not checked.",
    `<div class="card chat"><div class="suggest">${suggestions(p).map((q) => `<button type="button">${esc(q)}</button>`).join("")}</div>
     <div class="chat-log" id="chatlog"></div>
     <form id="chatform"><input id="chatq" placeholder="e.g. Does this change who can see the data?" autocomplete="off" maxlength="1000"><button class="btn" type="submit">Ask</button></form></div>`);
}

function secDecide(p) {
  const t = p.decision.tier;
  if (t === "return") {
    const proven = p.findings.filter((f) => f.verified && f.severity === "block");
    const msg = `To: ${p.author || "coding agent"}\nRe: ${p.id} ${p.title}\n\nThis PR was returned before human review. Fix these and push again:\n\n` +
      proven.map((f, i) => `${i + 1}. ${f.title}${f.file ? ` (${f.file}${f.line ? ":" + f.line : ""})` : ""}\n   Proof: ${evText(f)}`).join("\n") +
      (questions(p).length ? `\n\nOpen questions the owner will ask when you come back:\n` + questions(p).map((r) => `- ${r.what}`).join("\n") : "");
    return sec("s-decide", "07", "What happens next", `Nothing for you to sign yet. This is the fix list the agent receives. When it pushes a fix, the PR comes back through the same checks.`,
      `<div class="agent-msg">${esc(msg)}</div>`);
  }
  const d = store.get(p.id);
  if (d) {
    return sec("s-decide", "07", "Your decision", "Recorded in this browser.",
      `<div class="receipt ${d.verdict}"><h3>${d.verdict === "approved" ? "Approved" : "Denied"} · ${new Date(d.at).toLocaleString()}</h3><p style="margin:6px 0"><b>Reason:</b> ${esc(d.reason)}</p>${d.accepted.length ? `<p class="small" style="margin:6px 0"><b>You confirmed:</b> ${d.accepted.map(esc).join(" · ")}</p>` : ""}<button class="btn ghost" id="undo" type="button" style="margin-top:8px">Change my decision</button></div>`);
  }
  const so = p.signoff;
  const items = [
    ...questions(p).map((r) => `I have answered: ${r.what}`),
    ...so.residual_risk.map((r) => `I accept this risk: ${r}`),
    "The AI review was advice, not approval. I am accountable for this merge.",
  ];
  return sec("s-decide", "07", "Your decision", `You are approving the outcome, so confirm the open points, then approve or deny. A reason is always required, so the record shows why.`,
    `<div class="card pad decide">
      ${items.map((x, i) => `<label class="chk"><input type="checkbox" data-i="${i}"><span>${esc(x)}</span></label>`).join("")}
      <textarea id="reason" placeholder="Your reason (required), e.g. Fee cap matches REQ-PAY-204; confirmed AC3 manually on staging."></textarea>
      <div class="row"><span class="small muted" id="dhint">Tick every box and write a reason to approve.</span><button class="btn red" id="deny" type="button" disabled>Deny</button><button class="btn green" id="approve" type="button" disabled>Approve</button></div>
    </div>`);
}

function wireDecide(p) {
  const undo = $("#undo");
  if (undo) undo.onclick = () => { store.clear(p.id); renderPR(p); location.hash = `#/pr/${p.id}`; setTimeout(() => $("#s-decide").scrollIntoView(), 50); };
  const ap = $("#approve"), dn = $("#deny"), reason = $("#reason");
  if (!ap) return;
  const boxes = [...document.querySelectorAll(".decide input[type=checkbox]")];
  const update = () => {
    const okReason = reason.value.trim().length >= 8;
    ap.disabled = !(okReason && boxes.every((b) => b.checked));
    dn.disabled = !okReason;
  };
  boxes.forEach((b) => (b.onchange = update)); reason.oninput = update;
  const record = (verdict) => {
    store.set(p.id, { verdict, reason: reason.value.trim(), at: Date.now(),
      accepted: boxes.filter((b) => b.checked).map((b) => b.nextElementSibling.textContent) });
    renderPR(p); setTimeout(() => $("#s-decide").scrollIntoView(), 50);
  };
  ap.onclick = () => record("approved");
  dn.onclick = () => record("denied");
}

function wireChat(p) {
  const log = $("#chatlog"), form = $("#chatform"), input = $("#chatq");
  const history = [];
  const add = (role, text, src) => {
    const el = document.createElement("div");
    el.className = "msg " + (role === "user" ? "user" : "bot");
    el.textContent = text;
    if (src) { const s = document.createElement("span"); s.className = "src"; s.textContent = src; el.appendChild(s); }
    log.appendChild(el); log.scrollTop = log.scrollHeight; return el;
  };
  add("bot", `Hi. I've read this PR's diff, tests and findings. ${p.decision.tier === "return" ? "It was sent back to the agent. Ask me why." : "Ask me anything before you decide."}`);
  const ask = async (q) => {
    q = q.trim(); if (!q) return;
    add("user", q); history.push({ role: "user", text: q });
    const pending = add("bot", "Thinking…");
    form.querySelector("button").disabled = true;
    try {
      const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pr: p.id, question: q, history: history.slice(0, -1) }) });
      const j = await r.json();
      pending.remove();
      add("bot", j.answer || j.error || "No answer.", j.source === "trailer" ? "answered from this PR's evidence (no model)" : j.source ? `answered by ${j.source}, grounded in this PR` : "");
      history.push({ role: "bot", text: j.answer || "" });
    } catch (e) {
      pending.textContent = "Couldn't reach the assistant. Try again.";
    } finally { form.querySelector("button").disabled = false; }
  };
  form.onsubmit = (e) => { e.preventDefault(); const q = input.value; input.value = ""; ask(q); };
  document.querySelectorAll(".suggest button").forEach((b) => (b.onclick = () => ask(b.textContent)));
}

function wireSteps() {
  const links = [...document.querySelectorAll(".steps a")];
  links.forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(a.getAttribute("href")).scrollIntoView({ behavior: "smooth" }); }));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => { if (en.isIntersecting) links.forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + en.target.id)); });
  }, { rootMargin: "-30% 0px -60% 0px" });
  document.querySelectorAll("section.step").forEach((s) => io.observe(s));
}

// ---------- how ----------
function renderHow() {
  $("#app").innerHTML = `
  <div class="eyebrow">How it works</div>
  <h1>From "read everything" to "read these lines"</h1>
  <p class="lede" style="margin-bottom:28px">Tieto's mentors told us the person who merges is not really a reviewer any more. They are the approver: accountable that the change does what it should and nothing else, so they can sleep without fearing a 3 a.m. call. Nobody can read millions of lines. So we built the steps that let them stop.</p>
  <div class="how-steps">
    <div class="card"><div class="n">01</div><div><h3>Start from the outcome</h3><p class="muted" style="margin:0">Every PR is tied to a requirement ID with acceptance criteria. We answer two questions first: does it do what the requirement says, and does it do anything else? Changed code that the requirement's tests never reach is flagged as "outside the outcome".</p></div></div>
    <div class="card"><div class="n">02</div><div><h3>Map the impact on the whole codebase</h3><p class="muted" style="margin:0">Which files changed, which import or call them, which API endpoints, screens and tables they reach, and how hard it is to undo (a dropped column is forever; a code revert is not). Untouched files fade out.</p></div></div>
    <div class="card"><div class="n">03</div><div><h3>Test and attack it before a human looks</h3><p class="muted" style="margin:0">Acceptance tests run on main and on the PR. UI changes are clicked through in a real browser and recorded on video. Probes try to read another customer's data, grep logs for leaked IBANs, check money invariants, and fuzz "no behaviour change" claims against main. Anything reproduced sends the PR back to the agent with the proof.</p></div></div>
    <div class="card"><div class="n">04</div><div><h3>Point the human at the few risky spots</h3><p class="muted" style="margin:0">What the AI could not decide on its own (intent, security, data loss) becomes a question with a named owner and the exact lines, at most 10 spots. Everything else is covered by the evidence. The approver can ask questions about the code in plain English.</p></div></div>
    <div class="card"><div class="n">05</div><div><h3>A human approves or denies, with a reason</h3><p class="muted" style="margin:0">The AI never approves. The approver ticks what they checked and what risk they accept, and writes why. Trust is earned per area: the quick-check lane opens only after clean PRs, and one escaped bug closes it again.</p></div></div>
  </div>
  <div class="note-box" style="margin-top:22px">Rule we never break: only problems we can reproduce are allowed to block. Opinions, including an LLM's, can only point a human somewhere. That keeps false alarms at zero, so people keep trusting the lane.</div>`;
}

// ---------- proof ----------
function effortChart() {
  const E = DATA.effort; if (!E) return "";
  const W = 960, Hh = 420, L = 44, R = 20, T = 58, B = 52, N = E.total_diff_lines, nb = E.bugs;
  const x = (v) => L + (v / N) * (W - L - R), y = (v) => T + (1 - v / nb) * (Hh - T - B);
  const S = E.strategies;
  const steps = (pts) => { let d = `M${x(0)},${y(0)}`, py = 0; pts.forEach((p) => { d += ` L${x(p.x)},${y(py)} L${x(p.x)},${y(p.found)}`; py = p.found; }); return d; };
  const line = (pts, cls) => `<path class="${cls}" d="${steps(pts)}"/>`;
  const rnd = `<path class="c-rand" d="${S.random.points.map((p, i) => `${i ? "L" : "M"}${x(p.x)},${y(p.found)}`).join(" ")}"/>`;
  const grid = [0, 2, 4, 6, 8].map((v) => `<line class="g${v ? "" : " g0"}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="t" x="${L - 10}" y="${y(v) + 4}" text-anchor="end">${v}</text>`).join("")
    + [0, 50, 100, 150, 200, 250, N].map((v) => `<line class="g tick" x1="${x(v)}" x2="${x(v)}" y1="${y(0)}" y2="${y(0) + 5}"/><text class="t" x="${x(v)}" y="${y(0) + 20}" text-anchor="middle">${v}</text>`).join("");
  const A = DATA.ai && DATA.ai.summary;
  // AI reviewers are drawn as ceilings: a flat line with hatching on the side they never reach.
  const defs = `<defs>${["devin", "codex"].map((k) => `<pattern id="hatch-${k}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="h-${k}" x1="0" y1="0" x2="0" y2="7"/></pattern>`).join("")}</defs>`;
  const flat = A ? [["devin", A.devin.caught, "Devin review"], ["codex", A.codex.caught, "Codex review"]].map(([k, v, l]) => `<rect x="${L}" y="${y(v) - 7}" width="${W - L - R}" height="7" fill="url(#hatch-${k})"/><line class="c-${k}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="t halo lbl-${k}" x="${W - R - 6}" y="${y(v) - 13}" text-anchor="end">${l}: ${v}/${nb}, however long you read</text>`).join("") : "";
  const mk = S.trailer.lines_for_all, md = S.diff.lines_for_all, tp = S.trailer.points, tEnd = tp[tp.length - 1].x;
  return `<figure class="card pad chart" id="effort"><h3>Bugs in front of you, per line read</h3>
    <div class="scroll"><svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="Planted bugs found against lines read">${defs}${grid}
    <text class="t" x="${L - 30}" y="18">planted bugs in front of you (of ${nb})</text>
    <line class="mk2" x1="${x(md)}" x2="${x(md)}" y1="${y(nb)}" y2="${y(0)}"/><line class="mk" x1="${x(mk)}" x2="${x(mk)}" y1="${y(nb)}" y2="${y(0)}"/>
    ${flat}${rnd}${line(S.small_first.points, "c-small")}${line(S.diff.points, "c-diff")}
    <path class="a-trailer" d="${steps(tp)} L${x(tEnd)},${y(0)} Z"/>${line(tp, "c-trailer")}
    <circle class="d-diff" cx="${x(md)}" cy="${y(nb)}" r="4"/><text class="t halo lbl-diff" x="${x(md)}" y="${y(nb) - 14}" text-anchor="middle">top to bottom: ${md}</text>
    <circle class="d-trailer" cx="${x(mk)}" cy="${y(nb)}" r="5.5"/><text class="t halo strong" x="${x(mk) - 6}" y="${y(nb) - 14}">PR Trailer: all ${nb} after ${mk} lines</text>
    <text class="t" x="${(W + L - R) / 2}" y="${Hh - 8}" text-anchor="middle">lines read (of ${N} changed in the sprint)</text></svg></div>
    <div class="legend"><span><i class="k-trailer"></i>PR Trailer</span><span><i class="k-diff"></i>Read the diff top to bottom</span><span><i class="k-small"></i>Smallest PR first</span><span><i class="k-rand"></i>Random order (mean of 2,000)</span>${A ? '<span><i class="k-devin"></i>Devin</span><span><i class="k-codex"></i>Codex</span>' : ""}</div>
    <figcaption class="small muted">This is the effort-aware recall used in defect-prediction research: how many bugs you have seen after reading a given share of the changed lines. Generous to the baselines: we assume a reader spots a bug the moment they read its line. Sources: ${E.sources.map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${esc(s.title.split(":")[0])}</a>`).join(", ")}.</figcaption></figure>`;
}
function chatEval() {
  const C = DATA.chat_eval; if (!C) return "";
  const cell = (r, k) => r[k] ? `${pct(r[k].all)}${r[k].k > 1 ? ` <span class="muted small">(${pct(r[k].pass_hat_k)} right on all ${r[k].k} tries)</span>` : ""}` : '<span class="muted">–</span>';
  const al = C.alignment;
  return `<h2 style="margin-top:36px" id="chat">Is the PR assistant telling the truth?</h2>
  <p class="muted" style="max-width:78ch">The "Ask about this PR" assistant is graded on ${C.cases.dev + C.cases.heldout + C.cases.heldout2} questions an approver would ask, including traps: pressure to approve, questions nothing was tested for, off-topic requests. We read every answer, grouped what went wrong, wrote one pass/fail check per failure, then changed one thing at a time. Held-out questions were never used to tune; a second held-out set was written after the first had been looked at.</p>
  <div class="card scroll"><table><thead><tr><th>Version</th><th>What changed</th><th>Dev (${C.cases.dev})</th><th>Held-out (${C.cases.heldout})</th><th>Held-out 2 (${C.cases.heldout2})</th></tr></thead><tbody>
  ${C.ledger.map((r) => `<tr${r.version === C.shipped ? ' class="shipped"' : ""}><td><b>${r.version}</b>${r.version === C.shipped ? " (live)" : ""}</td><td class="small">${esc(r.change)}${r.hypothesis && r.hypothesis !== "baseline" ? `<br><span class="muted">Why: ${esc(r.hypothesis)}</span>` : ""}</td><td>${cell(r, "dev")}</td><td>${cell(r, "heldout")}</td><td>${cell(r, "heldout2")}</td></tr>`).join("")}</tbody></table></div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card pad"><h3>What went wrong, and how we check it</h3><ul class="checks">${C.failure_modes.map((f) => `<li><b>${esc(f.what)}</b><br><span class="small muted">Found by ${esc(f.found_by)}. Checked by ${esc(f.grader)}.</span></li>`).join("")}</ul></div>
    <div class="card pad"><h3>Can the grader be trusted?</h3><p class="small">The one check a script cannot do (does each cited line really say that?) is done by an LLM judge that sees the real text of every cited line. Against ${al.n} answers we labelled by hand, it caught ${pct(al.tpr)} of the bad ones and passed ${pct(al.tnr)} of the good ones (${pct(al.agreement)} agreement).</p>
    <p class="small"><b>Still failing:</b> ${esc(C.still_failing)}</p></div>
  </div>`;
}

function renderProof() {
  const B = DATA.bench, S = B.samples, M = B.mutants, H = B.heldout, A = DATA.ai;
  const rows = B.rows.map((r) => `<tr><td><a href="#/pr/${r.pr}">${r.pr}</a></td><td>${esc(r.bug || "none (clean)")}</td><td>${lanePill(r.tier)}</td><td class="mono small">${esc(r.caught_by.join(", ") || "–")}</td><td>${r.baseline_min}</td><td>${r.trailer_min}</td></tr>`).join("");
  let cmp = "";
  if (A) {
    const c = A.summary;
    const v = (x) => x.verdict === "caught" ? `<span class="ok">✓</span> ${esc(x.quote || "")}` : x.verdict === "hidden" ? `<span class="meh">flagged, text hidden</span>` : `<span class="meh">${esc(x.verdict)}</span>`;
    cmp = `<h2 style="margin-top:36px" id="reviewers">Against AI code reviewers on the same PRs</h2>
    <p class="muted" style="max-width:75ch">Every sample PR is a real pull request on GitHub. We asked GitHub Copilot to review all 13 (it refused: the account was out of review quota). Devin Review and Codex also reviewed them. They are useful, and on these PRs they flagged 3 to 4 of the 8 bugs. The bigger difference is what the approver gets: a comment is an opinion to re-check, while PR Trailer reproduces the failure, sends it back without a human, and tells you what to read on the rest.</p>
    <div class="card scroll"><table class="compare"><thead><tr><th>PR</th><th>Planted bug</th><th>PR Trailer</th><th>Devin Review</th><th>Codex</th></tr></thead><tbody>
    ${A.rows.map((r) => `<tr><td><a href="#/pr/${r.pr}">${r.pr}</a></td><td class="small">${esc(r.bug || "none (clean)")}</td><td class="small">${r.trailer.startsWith("caught") ? `<span class="ok">✓</span> ${esc(r.trailer.slice(8))}` : esc(r.trailer)}</td><td>${v(r.devin)}</td><td>${v(r.codex)}</td></tr>`).join("")}
    <tr><td colspan="2"><b>Planted bugs caught</b></td><td><b>${c.trailer.caught}/${c.trailer.of}</b> (${c.trailer_reproduced} reproduced)</td><td><b>${c.devin.caught}/${c.devin.of}</b> + ${c.devin_hidden_on_bugs} hidden</td><td><b>${c.codex.caught}/${c.codex.of}</b> (finished ${c.codex_reviewed} of 13)</td></tr></tbody></table></div>`;
  }
  const base = B.baselines ? `<h2 style="margin-top:36px">Against simple rules</h2><p class="muted">A change only counts if it beats "CI green = merge" on bugs caught and "read everything" on minutes.</p>
    <div class="card scroll"><table><thead><tr><th>Approach</th><th>13 sample PRs</th><th>${M ? M.mutants + " mutants" : ""}</th><th>${H ? H.mutants + " held-out mutants" : ""}</th></tr></thead><tbody>
    ${B.baselines.samples.map((row, i) => `<tr${row.name === "PR Trailer" ? ' style="font-weight:600"' : ""}><td>${esc(row.name)}</td>${["samples", "mutants", "heldout"].map((k) => B.baselines[k] ? `<td>${pct(B.baselines[k][i].catch_rate)} caught · ${B.baselines[k][i].minutes} min</td>` : "<td></td>").join("")}</tr>`).join("")}</tbody></table></div>` : "";
  $("#app").innerHTML = `
  <div class="eyebrow">Does it work?</div>
  <h1>Measured, including where it fails</h1>
  <p class="lede" style="margin-bottom:24px">We planted 8 bugs in 13 agent PRs, then also generated mechanical mutants we did not hand-pick, and a held-out set we never tuned on. Review minutes are modelled with stated assumptions, not stopwatched: that part is a hypothesis to test with real approvers.</p>
  <div class="kpis">
    <div class="card kpi"><div class="n">${S.buggy - S.escaped}/${S.buggy}</div><div class="l">planted bugs caught (${S.blocked_with_verified_evidence} with reproduced proof)</div></div>
    <div class="card kpi"><div class="n">${pct(S.false_alarm_rate)}</div><div class="l">of ${S.clean} clean PRs wrongly blocked</div></div>
    <div class="card kpi"><div class="n">${M ? pct(M.strict_catch_rate) : "–"}</div><div class="l">of ${M ? M.mutants : ""} unbiased mutants sent back with proof</div></div>
    <div class="card kpi"><div class="n">${S.minutes_with_trailer}</div><div class="l">modelled minutes for all 13, vs ${S.minutes_baseline} reading line by line</div></div>
  </div>
  ${effortChart()}
  <h2 style="margin-top:36px" id="bench">Every sample PR</h2>
  <div class="card scroll"><table><thead><tr><th>PR</th><th>Planted bug</th><th>Lane</th><th>Caught by</th><th>Read-all min</th><th>With PR Trailer, min</th></tr></thead><tbody>${rows}</tbody></table></div>
  <p class="small muted" style="max-width:80ch">Minutes are modelled, not timed. Most of the saving comes from the seven PRs sent back before anyone reads them; on PRs that need a person, the gain is in knowing what to read, and the full read on PR-112 is by policy.</p>
  ${cmp}${chatEval()}${base}
  <h2 style="margin-top:36px">Honest limits</h2>
  <ul class="checks no" style="max-width:80ch">
    <li>Small synthetic banking app (about 400 lines of product code). We wrote the planted bugs and the checks, which is why we also test on mutants we did not write.</li>
    <li>${M ? `${M.passed_as_light} of ${M.mutants} mutants slipped through as a quick check (some change nothing observable). A random 20% spot check of the quick-check lane caught one, and the trust ledger then withdraws that area's quick lane.` : ""}</li>
    <li>Not covered: concurrency, performance, infrastructure, multi-PR interactions.</li>
    <li>"Three days of reading to half an hour" is the hypothesis from Tieto's mentors. Our minutes are a model; the next step is timing real approvers.</li>
  </ul>`;
}

// ---------- boot ----------
fetch("data.json").then((r) => r.json()).then((d) => { DATA = d; route(); window.addEventListener("hashchange", route); })
  .catch(() => { $("#app").innerHTML = '<div class="loading">Could not load data.</div>'; });
