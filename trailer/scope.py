"""Outcome-first view: does the change do what the stated outcome says, and nothing else?

The stated outcome is the requirement's intent plus the acceptance criteria the PR claims. "Does it" is
answered by the acceptance tests. "Nothing else" is answered by tracing every changed line to the tests
that executed it: a change that the stated requirement's tests never touch is outside the stated intent.
"""
import ast
from pathlib import Path

from .checks import _parse, item
from .testrun import ac_key

SECURITY_FILES = ("ledger/auth.py", "ledger/ratelimit.py", "ledger/api.py")


def area_of(path: str) -> str:
    if path.startswith("web/"):
        return "frontend"
    if path.startswith("migrations/") or path == "ledger/statements.py":
        return "data"
    if path in SECURITY_FILES:
        return "security"
    return "backend"


def lines_by_requirement(head_run, ui_cov, req):
    by_req = {}
    for t in head_run["tests"]:
        k = ac_key(t["id"])
        if not k:
            continue
        by_req.setdefault(k[0], set()).update((p, n) for p, n in t["lines"])
    if req["area"] == "frontend":  # browser tests of the PR's own requirement drive the API server
        by_req.setdefault(req["id"], set()).update(ui_cov)
    return by_req


def scope_check(pr, req, diffs, head: Path, head_run, ui_cov):
    by_req = lines_by_requirement(head_run, ui_cov, req)
    mine = by_req.get(req["id"], set())
    items, impact, units = [], {}, []
    for d in diffs:
        path = d["path"]
        added = [n for n, t in d["added"] if t.strip() and not t.strip().startswith("#")]
        if path.startswith("web/"):
            ok = req["area"] == "frontend"
            units.append({"file": path, "unit": path, "in_scope": ok, "why": "frontend requirement" if ok else "UI file changed by a non-UI requirement"})
            continue
        if path.startswith("migrations/"):
            sql = (head / path).read_text().upper()
            index_only = all(l.strip().startswith(("CREATE INDEX", "--")) or not l.strip() for l in sql.splitlines())
            ok = req["area"] == "data" or index_only
            units.append({"file": path, "unit": path, "in_scope": ok,
                          "why": "schema change for a data requirement" if req["area"] == "data" else
                          ("index only: no data or behaviour change" if ok else "schema change outside a data requirement")})
            if not ok:
                items.append(item("refusal", "O-SCOPE", f"Schema change {path} outside the stated outcome",
                                  f"{req['id']} is not a data requirement, but this migration changes the schema.",
                                  file=path, line=1, ask="Is this schema change part of what you are approving?"))
            continue
        if not path.endswith(".py"):
            continue
        tree = _parse(head / path)
        spans = []
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = n.body[1:] if (len(n.body) > 1 and isinstance(n.body[0], ast.Expr)
                                      and isinstance(n.body[0].value, ast.Constant)) else n.body
                # decorator and def lines run at import time, so only the body counts as "executed by a test"
                spans.append((n.name, min(d.lineno for d in n.decorator_list) if n.decorator_list else n.lineno,
                              n.end_lineno, body[0].lineno))
        spans.sort(key=lambda s: s[2] - s[1])  # innermost first
        grouped = {}
        for ln in added:
            name = next((s[0] for s in spans if s[1] <= ln <= s[2]), "<module>")
            grouped.setdefault(name, []).append(ln)
        for name, lns in grouped.items():
            span = next((sp for sp in spans if sp[0] == name), None)
            body_lns = [n for n in lns if span and n >= span[3]] or lns
            hit_mine = any((path, n) in mine for n in body_lns)
            others = sorted(r for r, ls in by_req.items() if r != req["id"] and any((path, n) in ls for n in body_lns))
            for r in others:
                impact.setdefault(r, set()).add(f"{path}:{name}")
            if name == "<module>":
                units.append({"file": path, "unit": f"{path} (module level)", "in_scope": True, "why": "imports and constants"})
                continue
            if hit_mine:
                units.append({"file": path, "unit": f"{name}()", "in_scope": True,
                              "why": f"executed by {req['id']} acceptance tests"})
            else:
                why = (f"only executed by tests of {', '.join(others)}" if others
                       else f"never executed by any {req['id']} acceptance test")
                units.append({"file": path, "unit": f"{name}()", "in_scope": False, "why": why})
                items.append(item("refusal", "O-SCOPE", f"`{name}()` changed outside the stated outcome",
                                  f"The stated outcome is {req['id']} ({req['title']}). This change is {why}, so the "
                                  "evidence for the outcome says nothing about it.",
                                  file=path, line=lns[0],
                                  ask=f"Is the change to `{name}()` part of what you are approving? If yes, which criterion covers it?"))
    return {"units": units, "impact": {k: sorted(v) for k, v in sorted(impact.items())}}, items


def outcome(pr, req, evidence, items, rows, scope):
    claimed = [e for e in evidence if e["claimed"]]
    texts = [e["text"] for e in claimed]
    statement = req["intent"] + (" Specifically: " + " ".join(texts) if texts else "")
    if not pr.get("behavior_change", True):
        statement = f"No behaviour change. {pr['description']}"
    findings = [i for i in items if i["kind"] == "finding" and i["verified"] and i["severity"] == "block"]
    if pr.get("behavior_change", True):
        if not claimed:
            does = ("unproven", "The PR claims no acceptance criterion, so nothing proves the outcome.")
        elif all(e["status"] == "pass" for e in claimed):
            does = ("yes", f"{len(claimed)} claimed criterion(s) pass their acceptance tests on this PR.")
        elif any(e["status"] == "fail" for e in claimed):
            does = ("no", "A claimed criterion fails its acceptance test.")
        else:
            does = ("unproven", "A claimed criterion has no acceptance test.")
    else:
        diff_bad = [i for i in items if i["rule"] == "B-DIFFERENTIAL"]
        stateful = [i for i in items if i["rule"] in ("B-STATEFUL", "B-TOPLEVEL")]
        does = (("no", "Behaviour changed on random inputs.") if diff_bad else
                ("unproven", "Some changed code is stateful, so equivalence could not be tested.") if stateful else
                ("yes", "Changed functions matched main on 4000 random inputs each."))
    regress = sorted({r["req"] for r in rows if r["regression"]})
    out_of_scope = [u for u in scope["units"] if not u["in_scope"]]
    side = [i for i in findings if not i["rule"].startswith("T-CLAIM")]
    if regress or side:
        nothing_else = ("no", "It breaks something else: " + ", ".join(regress + [i["title"] for i in side if i["rule"] != "T-REGRESSION"]))
    elif out_of_scope:
        nothing_else = ("unproven", f"{len(out_of_scope)} changed unit(s) are outside the stated outcome: "
                        + ", ".join(u["unit"] for u in out_of_scope))
    else:
        nothing_else = ("yes", "Every changed unit is exercised by the stated requirement's tests, and no other requirement regressed.")
    return {"statement": statement, "does_it": {"verdict": does[0], "why": does[1]},
            "nothing_else": {"verdict": nothing_else[0], "why": nothing_else[1]}}


def confidence_and_spots(diffs, items, notes, scope, max_spots=10):
    areas = {}
    for d in diffs:
        areas.setdefault(area_of(d["path"]), {"files": [], "level": "high", "reasons": []})["files"].append(d["path"])
    for i in items + notes:
        if not i.get("file"):
            if i["kind"] == "refusal":  # e.g. a criterion with no test: lowers every touched area
                for a in areas.values():
                    if a["level"] == "high":
                        a["level"] = "medium"
                    a["reasons"].append(f"open question: {i['title']}")
            continue
        a = areas.get(area_of(i["file"]))
        if a is None:
            continue
        if i["kind"] == "finding" and i["verified"]:
            a["level"] = "low"
            a["reasons"].append(f"verified problem: {i['title']}")
        elif i["kind"] in ("refusal", "finding"):
            if a["level"] != "low":
                a["level"] = "low" if i["rule"] in ("S-POLICY", "D-DESTRUCTIVE") else "medium"
            a["reasons"].append(f"open question: {i['title']}")
        elif i["rule"] == "C-UNCOVERED":
            if a["level"] == "high":
                a["level"] = "medium"
            a["reasons"].append(i["title"])
    for a in areas.values():
        if not a["reasons"]:
            a["reasons"].append("every changed line ran under the stated requirement's tests; no open questions")
    rank = {"block": 0, "refusal": 1, "warn": 2, "note": 3}
    spots = []
    for i in items + notes:
        key = "block" if i["kind"] == "finding" and i["verified"] else ("refusal" if i["kind"] == "refusal" else
                                                                        ("warn" if i["kind"] == "finding" else "note"))
        spots.append({"file": i["file"], "line": i["line"], "what": i["title"], "why": i.get("ask") or i["detail"],
                      "kind": key})
    spots.sort(key=lambda s: rank[s["kind"]])
    seen, uniq = set(), []
    for s in spots:
        k = (s["file"], s["line"], s["what"])
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    return areas, uniq[:max_spots]
