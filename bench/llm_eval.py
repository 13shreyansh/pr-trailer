"""Score the optional Gemini reviewer on the 13 sample PRs (advisory layer; it never blocks).

python3 -m bench.llm_eval   # needs GEMINI_API_KEY; answers cached in out/llm/ for replay
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trailer import diffing, llm, workspace  # noqa: E402


def main():
    truth = json.loads((ROOT / "bench" / "ground_truth.json").read_text())
    g = llm.Gemini(replay_dir=ROOT / "bench" / "llm_cache")
    rows = []
    for pid in workspace.all_pr_ids():
        pr = workspace.load_pr(pid)
        req = workspace.requirement(pr["requirement"])
        base, head = workspace.materialise(pr)
        before = dict(g.stats)
        items = g.review(pr, req, diffing.diff_pr(base, head, pr["files"]), head)
        found = [i for i in items if i["rule"] == "L-LLM"]
        bug = truth.get(pid)
        rows.append({"pr": pid, "buggy": bool(bug), "grounded": len(found),
                     "dropped": g.stats["hallucinated"] - before["hallucinated"],
                     "on_bug_file": bool(bug and any(f["file"] == bug["file"] for f in found)),
                     "claims": [f"{f['file']}:{f['line']} {f['title'][16:]}" for f in found]})
        print(pid, rows[-1]["grounded"], rows[-1]["dropped"], rows[-1]["on_bug_file"], flush=True)
    bugs = [r for r in rows if r["buggy"]]
    clean = [r for r in rows if not r["buggy"]]
    summary = {"model": g.model, "raw_findings": g.stats["raw"], "grounded": g.stats["grounded"],
               "dropped_as_ungrounded": g.stats["hallucinated"],
               "hallucination_rate": round(g.stats["hallucinated"] / max(1, g.stats["raw"]), 3),
               "buggy_prs_with_grounded_finding_on_bug_file": f"{sum(r['on_bug_file'] for r in bugs)}/{len(bugs)}",
               "clean_prs_with_any_grounded_finding": f"{sum(r['grounded'] > 0 for r in clean)}/{len(clean)}"}
    (ROOT / "out" / "llm_eval.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
