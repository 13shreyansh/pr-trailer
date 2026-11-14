"""Side-by-side: the trailer vs AI code reviewers (Gemini via our harness, Devin Review, Codex) on the same 13 PRs.

Reads out/bench.json, out/llm_eval.json, bench/llm_labels.json and bench/ai_reviewers.json (captured from GitHub).
Writes out/ai_compare.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build():
    b = json.loads((ROOT / "out" / "bench.json").read_text())
    rev = json.loads((ROOT / "bench" / "ai_reviewers.json").read_text())
    llm = ROOT / "out" / "llm_eval.json"
    labels = json.loads((ROOT / "bench" / "llm_labels.json").read_text())
    gem = {r["pr"]: r for r in json.loads(llm.read_text())["rows"]} if llm.exists() else {}
    rows = []
    for r in b["samples"]["rows"]:
        pid, buggy = r["pr"], r["buggy"]
        if r["blocked"]:
            trailer = "caught: reproduced, returned to agent"
        elif r["routed_to_bug"]:
            trailer = "caught: question on the faulty file, sent to owner"
        elif buggy:
            trailer = "missed"
        else:
            trailer = {"light": "clean: light check", "targeted": "clean: targeted review",
                       "full": "clean: full read (policy)", "return": "FALSE BLOCK"}[r["tier"]]
        g = gem.get(pid)
        if not g:
            gemini = "not run"
        elif buggy:
            right = any(c["correct"] for c in labels.get(pid, []))
            gemini = "caught" if g["on_bug_file"] and right else "missed"
        else:
            gemini = (f"{g['grounded']} comment" + ("s" if g["grounded"] > 1 else "")) if g["grounded"] else "no issues"
        p = rev["prs"][pid]
        rows.append({"pr": pid, "buggy": buggy, "bug": r["bug"], "trailer": trailer, "lane": r["tier"],
                     "gemini": gemini, "devin": p["devin"], "codex": p["codex"]})
    bugs = [x for x in rows if x["buggy"]]
    clean = [x for x in rows if not x["buggy"]]

    def tally(key, is_caught):
        return {"caught": sum(is_caught(x) for x in bugs), "of": len(bugs),
                "clean_with_comments": sum(1 for x in clean if comments(x, key))}

    def comments(x, key):
        v = x[key]
        if key == "trailer":
            return x["lane"] in ("targeted", "full")
        if key == "gemini":
            return v.startswith(tuple("123456789"))
        return v["verdict"] in ("comments", "caught", "hidden")

    summary = {
        "trailer": tally("trailer", lambda x: x["trailer"].startswith("caught")),
        "trailer_reproduced": sum(1 for x in bugs if "reproduced" in x["trailer"]),
        "gemini": tally("gemini", lambda x: x["gemini"] == "caught"),
        "devin": tally("devin", lambda x: x["devin"]["verdict"] == "caught"),
        "devin_hidden_on_bugs": sum(1 for x in bugs if x["devin"]["verdict"] == "hidden"),
        "codex": tally("codex", lambda x: x["codex"]["verdict"] == "caught"),
        "codex_reviewed": sum(1 for x in rows if x["codex"]["verdict"] not in ("review failed", "still running")),
        "copilot": "requested on all 13; refused every one for insufficient quota",
        "captured_at": rev["captured_at"],
    }
    out = {"summary": summary, "rows": rows, "notes": rev["notes"]}
    (ROOT / "out" / "ai_compare.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(build()["summary"], indent=2))
