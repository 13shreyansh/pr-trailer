"""Collect graded runs into the hill-climbing ledger: out/chat_eval.json (read by the app and docs)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VERSIONS = [
    ("floor", "Rules only (no model): keyword answers from the trailer", None),
    ("v1", "First shipped prompt", "baseline"),
    ("v2", "Number every diff line in the context", "Wrong line numbers come from the model counting lines in a raw diff"),
    ("v3", "Answer first, cite only printed line numbers, no stock caveats", "Stock 'load, concurrency, config' caveats bury the answer"),
    ("v4", "Reason from the evidence instead of refusing", "v3 refuses answerable questions (ratings, examples, fixes)"),
    ("v5", "v3 plus one rule: give supported judgements, labelled, using only numbers in the context", "Keep v3's grounding and fix its over-refusal without v4's invented specifics"),
]
def load(name):
    p = HERE / "runs" / f"{name}.graded.json"
    return json.loads(p.read_text())["summary"] if p.exists() else None
rows = []
for v, change, hyp in VERSIONS:
    r = {"version": v, "change": change, "hypothesis": hyp}
    for split in ("dev", "heldout", "heldout2"):
        s = load(f"{v}.{split}.k3") or load(f"{v}.{split}.k1")
        if s:
            r[split] = {"all": s["all"], "pass_hat_k": s["pass_hat_k"], "k": s["k"], "n": s["n_cases"],
                        **{k: s[k] for k in ("answer", "concise", "no_padding", "no_verdict", "cites_real", "grounded") if k in s}}
    rows.append(r)
cases = json.loads((HERE / "cases.json").read_text())
res = {
    "shipped": "v5",
    "cases": {s: sum(c["split"] == s for c in cases) for s in ("dev", "heldout", "heldout2")},
    "categories": sorted({c["category"] for c in cases}),
    "failure_modes": [
        {"id": "grounded", "found_by": "LLM judge, after a first pass of hand reading missed it", "what": "Cites a file:line that is not the code it talks about (v1: 9 of 36 answers)", "grader": "Gemini judge with the real text of every cited line; 94% agreement with hand labels"},
        {"id": "no_padding", "found_by": "open coding", "what": "Appends a stock list of unchecked areas to unrelated answers (v1: 14 of 36)", "grader": "code"},
        {"id": "over_refusal", "found_by": "held-out set", "what": "Says 'not covered' to questions the evidence answers (rate it, give an example, what is the fix)", "grader": "code (case assertions)"},
        {"id": "no_verdict", "found_by": "spec", "what": "Approves or calls the PR safe on the approver's behalf", "grader": "code"},
    ],
    "alignment": json.loads((HERE / "alignment.json").read_text()),
    "ledger": rows,
    "still_failing": "PR-104 'Does 19.99 parse correctly?': the context only proves the float bug on 19985.01, so v5 either hedges or states the 19.99 result without evidence.",
}
(ROOT / "out" / "chat_eval.json").write_text(json.dumps(res, indent=1))
for r in rows:
    print(r["version"], {k: (r[k]["all"], r[k]["pass_hat_k"]) for k in ("dev", "heldout", "heldout2") if k in r})
