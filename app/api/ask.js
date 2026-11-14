// POST /api/ask {pr, question, history} -> {answer, source}
// Answers questions about one PR, grounded only in that PR's trailer (diff, evidence, findings, questions).
// Uses Gemini when GEMINI_API_KEY is set; otherwise answers from the trailer with simple rules.
const CONTEXT = require("./_context.json");
const PROMPTS = require("./_prompt.js");

const MODEL = process.env.GEMINI_MODEL || "gemini-3.8-flash";

function readBody(req) {
  if (req.body && typeof req.body === "object") return Promise.resolve(req.body);
  if (typeof req.body === "string") return Promise.resolve(JSON.parse(req.body || "{}"));
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (c) => { raw += c; if (raw.length > 1e5) req.destroy(); });
    req.on("end", () => { try { resolve(JSON.parse(raw || "{}")); } catch (e) { reject(e); } });
    req.on("error", reject);
  });
}

function send(res, code, obj) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(obj));
}

function numbered(unified) {
  // Prefix every diff line with its line number in the PR's version of the file (removed lines get "-").
  let head = null;
  return unified.split("\n").map((l) => {
    const m = l.match(/^@@ -\d+(?:,\d+)? \+(\d+)/);
    if (m) { head = Number(m[1]); return l; }
    if (head === null || l.startsWith("---") || l.startsWith("+++")) return l;
    if (l.startsWith("-")) return `    - ${l.slice(1)}`;
    const n = String(head++).padStart(4);
    return `${n} ${l.startsWith("+") ? "+" : " "} ${l.slice(1)}`;
  }).join("\n");
}

function compact(pr, opts = {}) {
  return {
    pr: { id: pr.id, title: pr.title, agent_description: pr.description },
    requirement: pr.requirement,
    lane: pr.decision,
    outcome: pr.outcome,
    merge_danger: pr.danger,
    acceptance_evidence: pr.evidence,
    what_was_checked: pr.checked,
    signoff: pr.signoff,
    proven_problems: pr.findings,
    questions_the_ai_refused_to_decide: pr.refusals,
    notes: pr.notes,
    spots_to_review: pr.spots,
    size: pr.stats,
    ...(opts.tables && pr.tables && pr.tables.length ? { sandbox_runs_main_vs_pr: pr.tables } : {}),
    diff: pr.diff.map((d) => ({ path: d.path, status: d.status, [opts.numbered ? "lines (number = line in the PR version; - = removed)" : "unified"]: (opts.numbered ? numbered(d.unified || "") : d.unified || "").slice(0, 7000) })),
  };
}

function fallback(pr, q) {
  const s = q.toLowerCase();
  const block = pr.findings.filter((f) => f.verified && f.severity === "block");
  const where = (i) => (i.file ? ` (${i.file}${i.line ? ":" + i.line : ""})` : "");
  if (/why|sent back|return|broken|wrong|bug|problem/.test(s) && block.length)
    return "It was sent back because these problems were reproduced, not guessed: " +
      block.map((f) => `${f.title}${where(f)}. Evidence: ${f.evidence || f.verification}`).join(" ");
  if (/test|evidence|prove|cover/.test(s))
    return pr.evidence.map((e) => `${e.ac}: ${e.text} — ${e.status}` + (e.tests.length ? ` (${e.tests.map((t) => `${t.id}: main ${t.base}, PR ${t.head}`).join("; ")})` : "")).join(" ");
  if (/risk|merge|revert|danger|break|impact|affect/.test(s))
    return `Door: ${pr.danger.door}. ${pr.danger.reasons.join(" ")} Blast radius: ${pr.danger.blast_radius}. Reaches: ${[...pr.danger.surfaces, ...pr.danger.tables].join(", ") || "nothing outside the changed files"}.`;
  if (/question|decide|owner|ask/.test(s) && pr.refusals.length)
    return "Open questions for a human: " + pr.refusals.map((r) => `${r.title}${where(r)}: ${r.ask || r.detail}${r.owner ? " (owner " + r.owner + ")" : ""}`).join(" ");
  return `${pr.decision.label}: ${pr.decision.why} Does it meet the requirement? ${pr.outcome.does_it.verdict} (${pr.outcome.does_it.why}) Does it do anything else? ${pr.outcome.nothing_else.verdict} (${pr.outcome.nothing_else.why})`;
}

async function gemini(pr, question, history) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) return null;
  const version = process.env.PROMPT_VERSION || PROMPTS.DEFAULT;
  const hist = (history || []).slice(-6).map((h) => `${h.role === "user" ? "Approver" : "Assistant"}: ${String(h.text).slice(0, 1200)}`);
  const P = PROMPTS.V[version];
  const prompt = P.build(compact(pr, P), hist, question);
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.2, maxOutputTokens: 2048 } }),
    signal: AbortSignal.timeout(45000),
  });
  if (!r.ok) throw new Error(`gemini ${r.status}`);
  const j = await r.json();
  const parts = (j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts) || [];
  const text = parts.filter((p) => !p.thought).map((p) => p.text || "").join("").trim();
  return text || null;
}

async function handler(req, res) {
  if (req.method === "GET") {
    // Health check, no secrets: is the model configured, and which prompt version is live?
    return send(res, 200, { model_configured: Boolean(process.env.GEMINI_API_KEY), model: MODEL, prompt: process.env.PROMPT_VERSION || PROMPTS.DEFAULT });
  }
  if (req.method !== "POST") return send(res, 405, { error: "POST only" });
  let body;
  try { body = await readBody(req); } catch { return send(res, 400, { error: "bad JSON" }); }
  const pr = CONTEXT[body.pr];
  const question = String(body.question || "").trim().slice(0, 1000);
  if (!pr || !question) return send(res, 400, { error: "need pr and question" });
  try {
    const answer = await gemini(pr, question, Array.isArray(body.history) ? body.history : []);
    if (answer) return send(res, 200, { answer, source: MODEL });
  } catch (e) {
    console.error(String(e));
  }
  return send(res, 200, { answer: fallback(pr, question), source: "trailer" });
};

module.exports = handler;
module.exports.fallback = fallback;
module.exports.compact = compact;
