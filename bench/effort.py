"""Effort-aware benchmark: how many lines must a human read before every planted bug is in front of them?

Treat the 13 sample PRs as one agent sprint. Each reading strategy is an ordered list of lines a human reads.
A bug counts as found when its line is read (generous to every baseline: we assume the reader notices it).
This is the effort-aware recall used in just-in-time defect prediction (Kamei et al., TSE 2013): recall after
inspecting X% of the changed lines, and Popt (area under the effort curve, normalised against optimal and worst).

Writes out/effort.json.
"""
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"

# Where each planted bug lives: file and a pattern that matches the bug's line in the PR (head side).
BUG_LINES = {
    "PR-102": ("ledger/transfers.py", r"status = 'booked'"),
    "PR-103": ("ledger/api.py", r'params\["account_id"\]'),
    "PR-104": ("ledger/money.py", r"float\(text"),
    "PR-105": ("ledger/transfers.py", r"log\.warning"),
    "PR-106": ("migrations/002_drop_memo.sql", r"DROP COLUMN memo"),
    "PR-108": ("web/app.js", r'addEventListener\("change", \(e\)'),
    "PR-109": ("ledger/transfers.py", r"WHERE idempotency_key = \?"),
    "PR-110": ("ledger/fees.py", r"round\(Decimal"),
}
LANE_ORDER = {"return": 0, "full": 1, "targeted": 2, "light": 3}


def diff_lines(pid, t):
    """Every line of the PR's unified diff a reviewer reads top to bottom, as (pid, file, head_line|None, text)."""
    rows = []
    for d in t["diff"]:
        head = None
        for raw in (d.get("unified") or "").splitlines():
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
            if m:
                head = int(m.group(1))
                continue
            if raw.startswith(("---", "+++")) or head is None:
                continue
            if raw.startswith("-"):
                rows.append((pid, d["path"], None, raw[1:]))
            else:
                rows.append((pid, d["path"], head, raw[1:]))
                head += 1
    return rows


def bug_key(pid, rows):
    f, pat = BUG_LINES[pid]
    for r in rows:
        if r[1] == f and r[2] is not None and re.search(pat, r[3]):
            return (pid, f, r[2])
    raise SystemExit(f"bug line not found for {pid}")


def curve(order, bugs, total):
    """Cumulative (lines_read, bugs_found) points for an ordered reading list of keys."""
    found, pts = set(), [(0, 0)]
    for i, k in enumerate(order, 1):
        if k in bugs and k not in found:
            found.add(k)
            pts.append((i, len(found)))
    pts.append((total, len(found)))
    return pts, found


def recall_at(pts, x, nbugs):
    best = 0
    for lx, n in pts:
        if lx <= x:
            best = n
    return best / nbugs


def area(pts, total, nbugs):
    """Area under the step curve, normalised to [0,1] over [0,total] x [0,nbugs]."""
    a, prev_x, prev_y = 0.0, 0, 0
    for x, y in pts:
        a += (x - prev_x) * prev_y
        prev_x, prev_y = x, y
    a += (total - prev_x) * prev_y
    return a / (total * nbugs)


def main():
    trailers = {p.name: json.loads((p / "trailer.json").read_text()) for p in sorted(OUT.glob("PR-1*"))}
    data = {p["id"]: p for p in json.loads((ROOT / "app" / "data.json").read_text())["prs"]}
    rows_by = {pid: diff_lines(pid, t) for pid, t in trailers.items()}
    all_rows = [r for pid in sorted(rows_by) for r in rows_by[pid]]
    keys = [(r[0], r[1], r[2] if r[2] is not None else f"-{i}") for i, r in enumerate(all_rows)]
    total = len(keys)
    bugs = {bug_key(pid, rows_by[pid]) for pid in BUG_LINES}
    nb = len(bugs)

    # 1. Diff order: PR-101 .. PR-113, top to bottom.
    diff_pts, _ = curve(keys, bugs, total)

    # 2. Smallest PR first (unsupervised effort-aware ranking from the JIT literature: small changes first).
    by_size = sorted(rows_by, key=lambda p: (len(rows_by[p]), p))
    small = [k for p in by_size for k in keys if k[0] == p]
    small_pts, _ = curve(small, bugs, total)

    # 3. Random order: mean of 2,000 shuffles, reported at fixed effort points.
    rng = random.Random(7)
    grid = sorted({0, total} | {round(total * f / 20) for f in range(21)})
    acc = [0.0] * len(grid)
    for _ in range(2000):
        o = keys[:]
        rng.shuffle(o)
        pts, _ = curve(o, bugs, total)
        for j, x in enumerate(grid):
            acc[j] += recall_at(pts, x, nb)
    random_pts = [(x, acc[j] / 2000 * nb) for j, x in enumerate(grid)]

    # 4. PR Trailer. PRs sent back with a reproduced failure cost one line each (the finding with file:line).
    #    PRs left for a human cost the lines in their review spots, in spot order. Light lanes cost nothing.
    trailer_order, spent, per_pr = [], 0, []
    for pid in sorted(data, key=lambda p: (LANE_ORDER[data[p]["decision"]["tier"]], p)):
        p = data[pid]
        tier = p["decision"]["tier"]
        if tier == "return":
            f = next((x for x in p["findings"] if x.get("verified") and x.get("severity") == "block"), None)
            hit = [k for k in bugs if k[0] == pid]
            trailer_order.append(hit[0] if hit else (pid, "finding", 0))
            per_pr.append({"pr": pid, "lane": tier, "lines": 1, "why": "read the reproduced failure: " + (f["title"] if f else "")})
            continue
        seen = []
        if tier == "full":  # the owner reads the whole change
            seen = [k for k in keys if k[0] == pid]
        for s in p["spots"]:
            for ln in (s.get("snippet") or []):
                k = (pid, s["file"], ln["n"])
                if k not in seen:
                    seen.append(k)
        trailer_order.extend(seen)
        per_pr.append({"pr": pid, "lane": tier, "lines": len(seen), "why": p["decision"]["why"]})
    # Per PR: which diff lines are the ones you read (for the sprint picture on the landing page).
    for row in per_pr:
        pk = [k for k in keys if k[0] == row["pr"]]
        want = set(trailer_order)
        row["diff_len"] = len(pk)
        row["hl"] = [i for i, k in enumerate(pk) if k in want]
        row["title"] = data[row["pr"]]["title"]
    trailer_total = len(trailer_order)
    trailer_pts, trailer_found = curve(trailer_order, bugs, trailer_total)
    trailer_pts[-1] = (trailer_total, len(trailer_found))

    # Reviewer comparison on the same 8 bugs (no reading order: they comment or they don't).
    ai = json.loads((OUT / "ai_compare.json").read_text())["summary"]

    def pct_x(pts):
        return [{"x": x, "pct": round(100 * x / total, 1), "found": y} for x, y in pts]

    def first_all(pts):
        return next((x for x, y in pts if y >= nb), None)

    res = {
        "what": "Lines a human reads before every planted bug in the 13-PR sprint is in front of them",
        "total_diff_lines": total,
        "bugs": nb,
        "bug_lines": [{"pr": k[0], "file": k[1], "line": k[2]} for k in sorted(bugs)],
        "strategies": {
            "trailer": {"label": "PR Trailer", "points": pct_x(trailer_pts), "lines_for_all": first_all(trailer_pts),
                        "lines_total": trailer_total, "found": len(trailer_found),
                        "recall_at_20": recall_at(trailer_pts, total * 0.2, nb), "popt_area": round(area(trailer_pts, total, nb), 3),
                        "per_pr": per_pr},
            "diff": {"label": "Read the diff top to bottom", "points": pct_x(diff_pts), "lines_for_all": first_all(diff_pts),
                     "recall_at_20": recall_at(diff_pts, total * 0.2, nb), "popt_area": round(area(diff_pts, total, nb), 3)},
            "small_first": {"label": "Smallest PR first (effort-aware heuristic)", "points": pct_x(small_pts),
                            "lines_for_all": first_all(small_pts), "recall_at_20": recall_at(small_pts, total * 0.2, nb),
                            "popt_area": round(area(small_pts, total, nb), 3)},
            "random": {"label": "Random order (mean of 2,000)", "points": [{"x": x, "pct": round(100 * x / total, 1), "found": round(y, 2)} for x, y in random_pts],
                       "lines_for_all": total, "recall_at_20": 0.2, "popt_area": round(area(random_pts, total, nb), 3)},
        },
        "reviewers": {
            "devin": {"label": "Devin review", "found": ai["devin"]["caught"], "of": ai["devin"]["of"]},
            "codex": {"label": "Codex review", "found": ai["codex"]["caught"], "of": ai["codex"]["of"]},
            "copilot": {"label": "Copilot review", "note": ai.get("copilot")},
        },
        "assumptions": [
            "A baseline reader notices a bug the moment they read its line. Real reviewers miss some, so baselines are flattered.",
            "A PR sent back with a reproduced failure costs one line: the finding names the file and line.",
            "Lines are every line of the unified diff (added, removed and the context shown around them).",
        ],
        "sources": [
            {"title": "Kamei et al., A Large-Scale Empirical Study of Just-in-Time Quality Assurance (TSE 2013): effort-aware recall at 20% of changed lines, Popt",
             "url": "https://das.encs.concordia.ca/pdf/Kamei_TSE2013.pdf"},
            {"title": "SmartBear and Cisco, Best Kept Secrets of Peer Code Review: reviewers stop finding defects beyond 200 to 400 lines",
             "url": "http://static0.smartbear.co/support/media/resources/cc/book/code-review-cisco-case-study.pdf"},
        ],
    }
    (OUT / "effort.json").write_text(json.dumps(res, indent=1))
    s = res["strategies"]
    print(f"diff lines in sprint: {total}, bugs: {nb}")
    for k, v in s.items():
        print(f"  {v['label']:45} all bugs after {v['lines_for_all']} lines  recall@20%={v['recall_at_20']:.2f}  area={v.get('popt_area')}")
    print("  trailer reads", trailer_total, "lines total;", per_pr)


if __name__ == "__main__":
    main()
