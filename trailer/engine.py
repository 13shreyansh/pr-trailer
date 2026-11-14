"""Build the trailer for one PR: evidence per requirement, findings, refusals, merge danger, sign-off card."""
import ast
import json
import shutil
from pathlib import Path

from . import checks, diffing, testrun, ui, workspace
from .checks import _functions, _parse, _route_handlers, changed_functions

AREA_OWNER = {"payments": "@aino.payments", "security": "@mikko.security", "data": "@sara.data",
              "frontend": "@lauri.frontend", "observability": "@aino.payments"}


# ---------------------------------------------------------------- blast radius and sequence diagram

def call_graph(ws: Path):
    funcs, calls = {}, {}
    for py in sorted((ws / "ledger").glob("*.py")):
        tree = _parse(py)
        if not tree:
            continue
        for name, fn in _functions(tree).items():
            funcs[name] = (str(py.relative_to(ws)), fn)
            calls[name] = [n.func.id if isinstance(n.func, ast.Name) else n.func.attr
                           for n in ast.walk(fn) if isinstance(n, ast.Call)
                           and isinstance(n.func, (ast.Name, ast.Attribute))]
    routes = {}
    api = _parse(ws / "ledger" / "api.py")
    for fn, name, _ in _route_handlers(api):
        routes[fn.name] = name
    return funcs, calls, routes


def blast_radius(head: Path, changed):
    funcs, calls, routes = call_graph(head)
    callers = {}
    for f, cs in calls.items():
        for c in cs:
            callers.setdefault(c, set()).add(f)
    names = {c["name"] for c in changed}
    seen, frontier = set(names), list(names)
    while frontier:
        n = frontier.pop()
        for c in callers.get(n, ()):
            if c not in seen:
                seen.add(c)
                frontier.append(c)
    reached = sorted(routes[f] for f in seen if f in routes)
    return {"changed_functions": sorted(names), "transitive_callers": sorted(seen - names),
            "entry_points": reached}


def path_to(route_fn, target, calls):
    stack = [(route_fn, [route_fn])]
    while stack:
        n, path = stack.pop()
        if n == target:
            return path
        for c in calls.get(n, []):
            if c in calls and c not in path:
                stack.append((c, path + [c]))
    return None


def sequence_diagram(head: Path, changed):
    """Mermaid sequence diagram from the entry point to the first changed function, then what it calls."""
    funcs, calls, routes = call_graph(head)
    if not changed:
        return None
    target = next((c["name"] for c in changed if not c["name"].startswith("_") and c["name"] != "tracer"), changed[0]["name"])
    chain = None
    for rfn, rname in routes.items():
        chain = path_to(rfn, target, calls)
        if chain:
            entry = rname
            break
    lines = ["sequenceDiagram", "    autonumber", "    actor C as Customer app"]
    if chain:
        lines.append(f"    participant R as {entry}")
        prev = "R"
        lines.append(f"    C->>R: request")
        for i, fn in enumerate(chain[1:], 1):
            alias = f"F{i}"
            lines.insert(3 + i, f"    participant {alias} as {fn}()")
            lines.append(f"    {prev}->>{alias}: call")
            prev = alias
    else:
        prev = "F0"
        lines.append(f"    participant F0 as {target}()")
        lines.append(f"    C->>F0: call")
    _, fn = funcs[target]
    has_db = has_audit = has_log = False
    body = []
    for n in sorted((n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))),
                    key=lambda n: (n.lineno, n.col_offset)):
        name = n.func.id if isinstance(n.func, ast.Name) else n.func.attr
        if name == "execute" and n.args and isinstance(n.args[0], ast.Constant):
            sql = " ".join(str(n.args[0].value).split())
            verb, table, preds = checks._sql_shape(sql)
            where = (" WHERE " + " AND ".join(preds)) if preds else ""
            body.append(f"    {prev}->>DB: {verb} {table}{where}"[:150])
            has_db = True
        elif name == "record":
            body.append(f"    {prev}->>A: audit {n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else 'event'}")
            has_audit = True
        elif name in ("warning", "info", "error", "debug"):
            body.append(f"    {prev}->>L: log.{name}")
            has_log = True
        elif name in funcs and name != target and not name.startswith("_reach"):
            body.append(f"    {prev}->>{prev}: {name}()")
    if has_db:
        lines.append("    participant DB as SQLite")
    if has_audit:
        lines.append("    participant A as audit_log")
    if has_log:
        lines.append("    participant L as App logs")
    lines += body[:14]
    return "\n".join(lines)


# ---------------------------------------------------------------- merge danger

def merge_danger(pr, items, diffs, radius):
    rules = {i["rule"] for i in items}
    reasons = []
    if "D-DESTRUCTIVE" in rules:
        door = "one-way"
        reasons.append("Migration destroys stored data; a code revert does not restore it.")
    elif {"S-AUTHZ", "P-PII-LOG"} & {i["rule"] for i in items if i["kind"] == "finding"}:
        door = "one-way"
        reasons.append("Data exposed while this is live (to another user or to log storage) cannot be taken back.")
    elif any(d["path"].startswith("migrations/") for d in diffs):
        door = "two-way, with residue"
        reasons.append("Additive migration: reverting needs a down-migration, but no data is lost.")
    elif any(f in radius["changed_functions"] + radius["transitive_callers"] for f in ("create_transfer", "transfer_fee")) \
            or "POST /api/transfer" in radius["entry_points"]:
        door = "two-way, with residue"
        reasons.append("Code reverts cleanly, but payments made while it is live stay made.")
    else:
        door = "two-way"
        reasons.append("Code-only change; a revert fully undoes it.")
    web = [d["path"] for d in diffs if d["path"].startswith("web/")]
    surfaces = list(radius["entry_points"]) + (["Transfer form (web)"] if web else [])
    tables = sorted({m for d in diffs for m in ["transfers"] if d["path"].startswith("migrations/")})
    size = len(radius["changed_functions"]) + len(radius["transitive_callers"])
    level = "wide" if (door == "one-way" or len(surfaces) >= 3) else ("contained" if size <= 2 and len(surfaces) <= 1 else "moderate")
    return {"door": door, "reasons": reasons, "blast_radius": level, "surfaces": surfaces, "tables": tables,
            "changed_functions": radius["changed_functions"], "callers": radius["transitive_callers"]}


# ---------------------------------------------------------------- routing

def route(items, danger, uncovered_lines):
    blocking = [i for i in items if i["kind"] == "finding" and i["severity"] == "block" and i["verified"]]
    refusals = [i for i in items if i["kind"] == "refusal"]
    if blocking:
        return {"tier": "return", "label": "Return to agent",
                "why": f"{len(blocking)} verified problem(s). No human review needed until the agent fixes them."}
    if danger["door"] == "one-way" or any(i["rule"] == "S-POLICY" for i in refusals):
        return {"tier": "full", "label": "Full read",
                "why": "One-way door or security policy: the owner reads the whole change."}
    if refusals or uncovered_lines or any(i["kind"] == "finding" for i in items):
        return {"tier": "targeted", "label": "Targeted review",
                "why": "Read the trailer, then answer the open questions and read the flagged hunks only."}
    return {"tier": "light", "label": "Light check",
            "why": "Every claimed criterion has passing evidence, no open questions. Read the trailer and sign."}


# ---------------------------------------------------------------- build

def build(pr_id: str, out_root: Path, with_ui=True, llm=None) -> dict:
    pr = workspace.load_pr(pr_id)
    req = workspace.requirement(pr["requirement"])
    req["owner"] = AREA_OWNER[req["area"]]
    base, head = workspace.materialise(pr)
    out = out_root / pr_id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    diffs = diffing.diff_pr(base, head, pr["files"])
    base_run, head_run = testrun.run_suite(base), testrun.run_suite(head)
    rows = testrun.compare(base_run, head_run)
    cov = testrun.covered_lines(head_run)

    touches_ui = any(d["path"].startswith("web/") for d in diffs) or req["area"] == "frontend"
    ui_rows, video = [], None
    if with_ui and touches_ui:
        caps = {"intro": f"{pr['id']} · {req['id']} · {pr['title']}"}
        ui_base = ui.run_ui(base, out / "_base_ui")
        ui_head = ui.run_ui(head, out / "evidence", caps)
        for path, line in ui.run_ui.last_coverage:
            cov.setdefault(path, {}).setdefault(line, set()).add("<ui-test>")
        ub = {r["id"]: r["status"] for r in ui_base}
        for r in ui_head:
            key = testrun.ac_key(r["id"])
            before = ub.get(r["id"], "absent")
            ui_rows.append({"id": r["id"], "req": key[0], "ac": key[1], "base": before, "head": r["status"],
                            "detail": r["detail"], "regression": before == "pass" and r["status"] != "pass",
                            "fixed": before != "pass" and r["status"] == "pass", "ui": True})
        shutil.move(str(out / "_base_ui" / "final.png"), str(out / "evidence" / "before.png"))
        shutil.rmtree(out / "_base_ui")
        video = "evidence/walkthrough.mp4"

    changed = changed_functions(base, head, diffs)
    items = []
    items += checks.check_tests(pr, req, rows, ui_rows)
    items += checks.check_invariants(head_run)
    items += checks.check_money_float(base, head, diffs, head_run)
    items += checks.check_pii_logs(base, head, diffs, head_run, base_run)
    items += checks.check_authz(base, head, diffs)
    items += checks.check_sql(base, head, diffs)
    items += checks.check_migrations(base, head, diffs)
    items += checks.check_security_policy(pr, req, diffs)
    items += checks.check_no_behaviour_change(pr, base, head, diffs)
    notes = checks.check_coverage(diffs, cov)
    if llm:
        items += llm.review(pr, req, diffs, head)

    # De-duplicate: the same invariant failure is reported once even when a static rule also points at it.
    seen, uniq = set(), []
    for i in items:
        key = (i["rule"], i["file"], i["line"], i["title"])
        if key not in seen:
            seen.add(key)
            uniq.append(i)
    items = uniq
    if any(i["rule"] == "M-FLOAT" and i["verified"] for i in items):
        items = [i for i in items if not (i["rule"] == "I-INVARIANT" and "parse_is_exact" in i["title"])]

    radius = blast_radius(head, changed)
    danger = merge_danger(pr, items, diffs, radius)
    uncovered = [n for n in notes if n["rule"] == "C-UNCOVERED"]
    decision = route(items, danger, uncovered)

    evidence = []
    for ac in req["acceptance"]:
        tests = [r for r in rows + ui_rows if r["req"] == req["id"] and r["ac"] == ac["ac"]]
        evidence.append({"ac": ac["ac"], "text": ac["text"], "claimed": ac["ac"] in pr.get("claims_acs", []),
                         "tests": [{"id": t["id"], "base": t["base"], "head": t["head"], "ui": t.get("ui", False)} for t in tests],
                         "status": ("no test" if not tests else ("pass" if all(t["head"] == "pass" for t in tests) else "fail"))})
    other = [r for r in rows + ui_rows if r["req"] != req["id"]]
    checked = {
        "spec_tests": {"total": len(rows), "pass": sum(r["head"] == "pass" for r in rows),
                       "already_failing": sum(r["head"] != "pass" and r["base"] != "pass" for r in rows),
                       "regressions": sum(r["regression"] for r in rows), "seconds": head_run["seconds"]},
        "ui_tests": {"total": len(ui_rows), "pass": sum(r["head"] == "pass" for r in ui_rows),
                     "regressions": sum(r["regression"] for r in ui_rows)} if ui_rows else None,
        "invariants": [{"id": i["id"], "ok": i["result"] is None} for i in head_run.get("invariants", [])],
        "other_requirements_regressed": sorted({r["req"] for r in other if r["regression"] and r["req"]}),
        "rules": ["tests", "invariants", "money-float", "pii-in-logs", "authz-probe", "sql-scope", "migrations",
                  "security-policy", "behaviour-claim"] + (["llm-reviewer"] if llm else []),
    }

    owners = sorted({req["owner"]} | {i["owner"] for i in items if i["kind"] == "refusal" and i["owner"]})
    primary = workspace.owner_for(pr["files"][0])
    signoff = {
        "owner": primary if decision["tier"] != "full" else (
            "@mikko.security" if any(i["rule"] == "S-POLICY" for i in items) else primary),
        "co_signers": [o for o in owners if o != primary],
        "checked": [f"{checked['spec_tests']['total']} acceptance tests run on main and on this PR: "
                    f"{checked['spec_tests']['regressions']} regressions, {checked['spec_tests']['pass']} pass, "
                    f"{checked['spec_tests']['already_failing']} fail on both (features not built yet)"]
                   + ([f"{checked['ui_tests']['pass']}/{checked['ui_tests']['total']} UI acceptance tests in Chromium, video recorded"] if ui_rows else [])
                   + [f"{sum(i['ok'] for i in checked['invariants'])}/{len(checked['invariants'])} money invariants hold"]
                   + [f"{n['title']}" for n in [i for i in items if i["kind"] == "note"]],
        "not_checked": [n["title"] + " — " + n["detail"] for n in notes]
                       + [f"{e['ac']}: no acceptance test" for e in evidence if e["status"] == "no test"]
                       + ["Performance under load, concurrency between simultaneous requests, production config"],
        "residual_risk": danger["reasons"],
        "questions": [{"q": i["ask"], "owner": i["owner"], "rule": i["rule"], "file": i["file"], "line": i["line"]}
                      for i in items if i["kind"] == "refusal"],
    }

    trailer = {
        "pr": {k: v for k, v in pr.items() if k != "dir"}, "requirement": req,
        "diff": [{"path": d["path"], "status": d["status"], "added": len(d["added"]), "removed": len(d["removed"]),
                  "unified": d["unified"]} for d in diffs],
        "lines_changed": diffing.lines_changed(diffs),
        "evidence": evidence, "video": video,
        "before_after": ["evidence/before.png", "evidence/final.png"] if video else None,
        "sequence": None if touches_ui and not any(d["path"].endswith(".py") for d in diffs) else sequence_diagram(head, changed),
        "findings": [i for i in items if i["kind"] == "finding"],
        "refusals": [i for i in items if i["kind"] == "refusal"],
        "notes": [i for i in items if i["kind"] == "note"] + notes,
        "checked": checked, "danger": danger, "decision": decision, "signoff": signoff,
        "test_rows": rows + ui_rows,
    }
    (out / "trailer.json").write_text(json.dumps(trailer, indent=2, default=list))
    shutil.rmtree(base.parent, ignore_errors=True)
    return trailer
