"""Deterministic review checks. Each returns findings, refusals or notes.

A *finding* claims something is wrong. It is only allowed to block a merge when `verified` is true,
meaning a test, probe or counterexample reproduced it. Unverified findings are advice.
A *refusal* is a question the AI will not answer on its own, with the reason and who must answer it.
A *note* records something checked or not checked, for the sign-off card.
"""
import ast
import json
import random
import re
import subprocess
import sys
from pathlib import Path

from .workspace import owner_for

PROBE = Path(__file__).resolve().parent / "_probe.py"
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
PII_NAME = re.compile(r"iban|email|ssn|phone|full_name|password", re.I)
DESTRUCTIVE_SQL = re.compile(r"\b(DROP\s+(TABLE|COLUMN)|DELETE\s+FROM|TRUNCATE)\b", re.I)


def item(kind, rule, title, detail, file=None, line=None, severity="warn", verified=False,
         verification=None, ask=None, owner=None, evidence=None):
    return {"kind": kind, "rule": rule, "title": title, "detail": detail, "file": file, "line": line,
            "severity": severity, "verified": verified, "verification": verification, "ask": ask,
            "owner": owner or (owner_for(file) if file else None), "evidence": evidence}


def probe(ws: Path, mode: str, arg) -> list:
    p = subprocess.run([sys.executable, "-I", str(PROBE), str(ws), mode, json.dumps(arg)],
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-800:])
    return json.loads(p.stdout)


def _parse(path: Path):
    try:
        return ast.parse(path.read_text())
    except (SyntaxError, FileNotFoundError):
        return None


def _added_lines(d) -> set:
    return {n for n, _ in d["added"]}


def _functions(tree):
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def changed_functions(base: Path, head: Path, diffs) -> list[dict]:
    """Functions in head whose body contains an added line, or whose source differs from base."""
    out = []
    for d in diffs:
        if not d["path"].endswith(".py"):
            continue
        ht, bt = _parse(head / d["path"]), _parse(base / d["path"])
        if ht is None:
            continue
        hsrc = (head / d["path"]).read_text()
        bfuncs = _functions(bt) if bt else {}
        bsrc = (base / d["path"]).read_text() if bt else ""
        added = _added_lines(d)
        for name, fn in _functions(ht).items():
            span = set(range(fn.lineno, fn.end_lineno + 1))
            new_src = ast.get_source_segment(hsrc, fn)
            old_src = ast.get_source_segment(bsrc, bfuncs[name]) if name in bfuncs else None
            if span & added or (old_src is not None and old_src != new_src):
                out.append({"file": d["path"], "name": name, "line": fn.lineno, "new": name not in bfuncs,
                            "params": [a.arg for a in fn.args.args],
                            "annotations": {a.arg: ast.unparse(a.annotation) if a.annotation else None
                                            for a in fn.args.args}})
    return out


# ---------------------------------------------------------------- tests and acceptance criteria

def check_tests(pr, req, rows, ui_rows):
    out = []
    all_rows = rows + ui_rows
    for r in all_rows:
        if r["regression"]:
            out.append(item("finding", "T-REGRESSION", f"Acceptance test regressed: {r['id']}",
                            f"Passed on main, {r['head']} on this PR.", severity="block", verified=True,
                            verification="spec test run on base and head", evidence=r["detail"][-400:]))
    claimed = set(pr.get("claims_acs", []))
    for ac in req["acceptance"]:
        tests = [r for r in all_rows if r["req"] == req["id"] and r["ac"] == ac["ac"]]
        if not tests:
            if True:  # every untested criterion of the PR's own requirement is an open question
                out.append(item("refusal", "T-NO-ORACLE", f"{req['id']} {ac['ac']} has no acceptance test",
                                f"“{ac['text']}”. Without a test the AI cannot show this criterion holds, "
                                "and it will not vouch for it from reading code alone.",
                                ask=f"Confirm {ac['ac']} by hand, or add an acceptance test for it.",
                                owner=req.get("owner")))
            continue
        for t in tests:
            if ac["ac"] in claimed and t["head"] != "pass":
                out.append(item("finding", "T-CLAIM-UNMET", f"PR claims {ac['ac']} but its test fails",
                                f"“{ac['text']}”: {t['id']} is {t['head']}.", severity="block",
                                verified=True, verification="spec test run on head", evidence=t["detail"][-400:]))
    return out


def check_invariants(head_run):
    out = []
    for inv in head_run.get("invariants", []):
        if inv["result"]:
            out.append(item("finding", "I-INVARIANT", f"Team invariant broken: {inv['id']}", inv["result"],
                            severity="block", verified=True, verification="invariant executed on head",
                            evidence=inv["result"]))
    return out


def check_coverage(diffs, cov):
    """Changed executable lines that no test executed: the AI did not check these."""
    out = []
    for d in diffs:
        if not d["path"].endswith(".py"):
            continue
        hit = cov.get(d["path"], {})
        missed = [n for n, text in d["added"]
                  if text.strip() and not text.strip().startswith(("#", '"""', "'''")) and n not in hit
                  and not text.strip().startswith(("def ", "class ", "@", ")", "]", "}"))]
        if missed:
            out.append(item("note", "C-UNCOVERED", f"{len(missed)} changed line(s) in {d['path']} never ran in any test",
                            "Not checked by execution: " + ", ".join(f"L{n}" for n in missed[:12]),
                            file=d["path"], line=missed[0]))
    return out


# ---------------------------------------------------------------- static rules with runtime verification

def check_money_float(base, head, diffs, head_run):
    out = []
    inv_fail = {i["id"]: i["result"] for i in head_run.get("invariants", []) if i["result"]}
    for d in diffs:
        if not (d["path"].startswith("ledger/") and d["path"].endswith(".py")):
            continue
        tree = _parse(head / d["path"])
        added = _added_lines(d)
        for node in ast.walk(tree):
            bad = (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float")
            if bad and node.lineno in added:
                ver = inv_fail.get("parse_is_exact")
                out.append(item("finding", "M-FLOAT", "Money passes through float",
                                "Kassa's standard is integer cents end to end; float cannot represent most cent "
                                "values exactly.", file=d["path"], line=node.lineno,
                                severity="block" if ver else "warn", verified=bool(ver),
                                verification="invariant parse_is_exact" if ver else None, evidence=ver))
    return out


def check_pii_logs(base, head, diffs, head_run, base_run):
    out = []
    base_leaks = {m["msg"] for m in base_run.get("logs", []) if IBAN_RE.search(m["msg"])}
    leaks = [m for m in head_run.get("logs", []) if IBAN_RE.search(m["msg"]) and m["msg"] not in base_leaks]
    for d in diffs:
        if not d["path"].endswith(".py"):
            continue
        tree = _parse(head / d["path"])
        added = _added_lines(d)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.lineno in added and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("debug", "info", "warning", "error", "exception", "critical")):
                continue
            for a in node.args[1:]:
                if isinstance(a, ast.Name) and PII_NAME.search(a.id):
                    sample = leaks[0]["msg"] if leaks else None
                    out.append(item("finding", "P-PII-LOG", f"Log line writes `{a.id}` unmasked",
                                    "REQ-OBS-401 AC3: logs never contain a full IBAN. Use mask_iban().",
                                    file=d["path"], line=node.lineno, severity="block" if leaks else "warn",
                                    verified=bool(leaks),
                                    verification="captured logs during the spec run contain a full IBAN" if leaks else None,
                                    evidence=sample))
    if leaks and not out:
        out.append(item("finding", "P-PII-LOG", "A full IBAN appeared in logs during the test run",
                        "Source line not identified statically.", severity="block", verified=True,
                        verification="log capture", evidence=leaks[0]["msg"]))
    return out


def _route_handlers(tree):
    for fn in _functions(tree).values():
        for dec in fn.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "route":
                yield fn, f"{dec.args[0].value} {dec.args[1].value}", dec.args[1].value


def _calls(fn):
    return {n.func.id if isinstance(n.func, ast.Name) else n.func.attr
            for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}


def _reaches_owner_check(fn, ws: Path, depth=2) -> bool:
    calls = _calls(fn)
    if "require_owner" in calls:
        return True
    if depth == 0:
        return False
    for py in (ws / "ledger").glob("*.py"):
        tree = _parse(py)
        for name, f in (_functions(tree) or {}).items():
            if name in calls and name != fn.name and _reaches_owner_check(f, ws, depth - 1):
                return True
    return False


def check_authz(base, head, diffs):
    out = []
    for d in diffs:
        if d["path"] != "ledger/api.py":
            continue
        tree = _parse(head / d["path"])
        base_tree = _parse(base / d["path"])
        base_routes = {r for _, r, _ in _route_handlers(base_tree)} if base_tree else set()
        suspects, new_routes = [], []
        for fn, name, path in _route_handlers(tree):
            if name not in base_routes:
                new_routes.append((fn, name))
            takes_account = any(isinstance(n, ast.Constant) and n.value == "account_id" for n in ast.walk(fn))
            if takes_account and not _reaches_owner_check(fn, head):
                suspects.append((fn, name, path))
        if suspects:
            res = {r["route"]: r for r in probe(head, "idor", {"routes": [p for _, _, p in suspects]})}
            for fn, name, path in suspects:
                r = res.get(name, {})
                out.append(item("finding", "S-AUTHZ", f"{name} reads account_id without an ownership check",
                                "REQ-SEC-301 AC1: every handler taking account_id must call require_owner.",
                                file=d["path"], line=fn.lineno, severity="block" if r.get("answered") else "warn",
                                verified=bool(r.get("answered")),
                                verification="probe: called as u-ben against acc-anna" if r.get("answered") else None,
                                evidence=r.get("body")))
        for fn, name in new_routes:
            out.append(item("refusal", "S-NEW-SURFACE", f"New endpoint {name}",
                            "A new endpoint is new attack surface. The AI checked ownership rules, but deciding who "
                            "may call it and what it may reveal is a security decision.",
                            file=d["path"], line=fn.lineno,
                            ask=f"Who is allowed to call {name}, and is everything it returns safe for them to see?"))
    return out


def _sql_in(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("execute", "executemany"):
            if n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                out.append((n.lineno, " ".join(n.args[0].value.split())))
            elif n.args and isinstance(n.args[0], (ast.JoinedStr, ast.BinOp)):
                out.append((n.lineno, None))
    return out


def _sql_shape(sql):
    verb = sql.split()[0].upper()
    table = re.search(r"\b(?:FROM|INTO|UPDATE)\s+(\w+)", sql, re.I)
    where = re.split(r"\bWHERE\b", sql, flags=re.I)
    preds = []
    if len(where) > 1:
        clause = re.split(r"\b(ORDER BY|GROUP BY|LIMIT)\b", where[1], flags=re.I)[0]
        preds = sorted(p.strip() for p in re.split(r"\bAND\b", clause, flags=re.I) if p.strip())
    return verb, table.group(1) if table else None, preds


def check_sql(base, head, diffs):
    out = []
    for d in diffs:
        if not d["path"].endswith(".py"):
            continue
        ht, bt = _parse(head / d["path"]), _parse(base / d["path"])
        hs = _sql_in(ht) if ht else []
        bs = _sql_in(bt) if bt else []
        added = _added_lines(d)
        for line, sql in hs:
            if sql is None and line in added:
                out.append(item("finding", "S-SQL-BUILD", "SQL built from a formatted string",
                                "Use parameters (?) instead of string formatting.", file=d["path"], line=line,
                                severity="warn"))
        base_sqls = {s for _, s in bs if s}
        head_sqls = {s: l for l, s in hs if s}
        removed = [s for s in base_sqls if s not in head_sqls]
        for new, line in head_sqls.items():
            if new in base_sqls:
                continue
            v, t, p = _sql_shape(new)
            for old in removed:
                ov, ot, op = _sql_shape(old)
                if (ov, ot) == (v, t) and op and op != p:
                    lost = [x for x in op if x not in p]
                    gained = [x for x in p if x not in op]
                    out.append(item("refusal", "D-SCOPE", f"Rows selected by a {v} on `{t}` changed",
                                    f"Before: WHERE {' AND '.join(op)}\nAfter: WHERE {' AND '.join(p) or '(none)'}\n"
                                    f"Dropped: {', '.join(lost) or '(none)'}; added: {', '.join(gained) or '(none)'}. "
                                    "The AI can see that the rows changed. It cannot know whether the requirement "
                                    "means for them to change.",
                                    file=d["path"], line=line,
                                    ask="Is this change in which rows are counted or returned intended by the requirement?"))
    return out


def check_migrations(base, head, diffs):
    out, dropped = [], []
    for d in diffs:
        if not d["path"].startswith("migrations/"):
            continue
        sql = (head / d["path"]).read_text()
        for m in re.finditer(r"DROP\s+COLUMN\s+(\w+)", sql, re.I):
            dropped.append(m.group(1))
        if DESTRUCTIVE_SQL.search(sql):
            out.append(item("refusal", "D-DESTRUCTIVE", f"Destructive migration {d['path']}",
                            "This migration destroys stored data. Reverting the code will not bring the data back. "
                            "The AI will not decide whether losing it is acceptable.",
                            file=d["path"], line=1, ask="Has this data been backed up or confirmed unneeded?"))
    for col in dropped:
        for py in sorted((head / "ledger").glob("*.py")):
            tree = _parse(py)
            for line, sql in _sql_in(tree) if tree else []:
                if sql and re.search(rf"\b{col}\b", sql):
                    rel = str(py.relative_to(head))
                    out.append(item("finding", "D-DANGLING", f"Dropped column `{col}` is still read",
                                    f"{rel}:{line} still uses `{col}`: {sql[:120]}", file=rel, line=line,
                                    severity="block", verified=True, verification="static reference to dropped column"))
    return out


def check_security_policy(pr, req, diffs):
    sensitive = [d["path"] for d in diffs if d["path"] in ("ledger/auth.py", "ledger/ratelimit.py")]
    if req["area"] == "security" or sensitive:
        return [item("refusal", "S-POLICY", "Authentication or authorisation logic changed",
                     "Kassa policy: AI review is advice only for authn/authz. The AI ran the acceptance tests and "
                     "probes below, but it will not sign off on security logic.",
                     file=(sensitive or [diffs[0]["path"]])[0],
                     ask="Security owner: read the change in full and confirm the threat model still holds.",
                     owner="@mikko.security")]
    return []


# ---------------------------------------------------------------- "no behaviour change" claims

def _harvest_strings(ws: Path):
    """Input corpus: every short string literal in the repo (code, tests, seed data), plus numeric strings."""
    found = set()
    for py in list((ws / "ledger").glob("*.py")) + list((ws / "tests").rglob("*.py")):
        tree = _parse(py)
        for n in ast.walk(tree) if tree else []:
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and 0 < len(n.value) <= 40 and "\n" not in n.value:
                found.add(n.value)
    return sorted(found)


def _gen_value(name, ann, strings, rng, local=()):
    is_int = ann == "int" or (ann is None and name.endswith(("_cents", "_count")))
    if is_int:
        return rng.choice([rng.randint(1, 3_000_000), rng.randint(1, 500) * 250, rng.randint(1, 100), rng.randint(-5, 5)])
    r = rng.random()
    if local and r < 0.4:
        return rng.choice(local)  # literals the changed module itself compares against
    if r < 0.6:
        return rng.choice(strings)
    if r < 0.8:
        return f"{rng.randint(0, 99999)}.{rng.randint(0, 99):02d}"
    base = list(rng.choice(strings))  # small edits of real literals reach edge cases
    if base:
        base[rng.randrange(len(base))] = rng.choice("0123456789 ABCXYZ,.")
    return "".join(base)


def _toplevel_changes(base: Path, head: Path, d):
    """Added lines outside any function or class body (constants, module setup)."""
    tree = _parse(head / d["path"])
    if not tree:
        return []
    inside = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            inside |= set(range(n.lineno, n.end_lineno + 1))
    return [(n, t) for n, t in d["added"] if n not in inside and t.strip()
            and not t.strip().startswith(("#", "import ", "from ", '"""'))]


def check_no_behaviour_change(pr, base, head, diffs):
    if pr.get("behavior_change", True):
        return []
    out = []
    rng = random.Random(7)
    for d in diffs:
        if d["path"].endswith(".py"):
            top = _toplevel_changes(base, head, d)
            if top:
                n = top[0][0]
                out.append(item("refusal", "B-TOPLEVEL", "Module-level value changed in a 'no behaviour change' PR",
                                f"{len(top)} line(s) from L{n}, e.g. `{top[0][1].strip()[:100]}`. Constants change behaviour "
                                "everywhere they are read; the AI cannot tell whether the new value is intended.",
                                file=d["path"], line=n, ask="Is this new value intended, and which requirement sets it?"))
    strings = _harvest_strings(head)
    for fn in changed_functions(base, head, diffs):
        if fn["new"] or fn["name"].startswith("_"):
            continue
        if "db" in fn["params"]:
            out.append(item("refusal", "B-STATEFUL", f"Cannot prove `{fn['name']}` behaves as before",
                            "The PR says there is no behaviour change, but this function reads or writes the database, "
                            "so the AI cannot check equivalence by running it on random inputs.",
                            file=fn["file"], line=fn["line"],
                            ask=f"Confirm `{fn['name']}` returns the same results for every user and state as before."))
            continue
        tree = _parse(head / fn["file"])
        local = sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and 0 < len(n.value) <= 40 and n.value.isidentifier()})
        inputs = [[_gen_value(p, fn["annotations"].get(p), strings, rng, local) for p in fn["params"]]
                  for _ in range(4000)]
        mod = fn["file"][:-3].replace("/", ".")
        arg = {"module": mod, "function": fn["name"], "inputs": inputs}
        a, b = probe(base, "call", arg), probe(head, "call", arg)
        diffs_found = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
        if diffs_found:
            i, x, y = diffs_found[0]
            call = f"{fn['name']}({', '.join(map(repr, inputs[i]))})"
            out.append(item("finding", "B-DIFFERENTIAL", f"`{fn['name']}` behaves differently, despite 'no behaviour change'",
                            f"{len(diffs_found)} of {len(inputs)} random inputs differ. First: {call} was {x}, now {y}.",
                            file=fn["file"], line=fn["line"], severity="block", verified=True,
                            verification=f"differential test, {len(inputs)} inputs, base vs head", evidence=call))
        else:
            out.append(item("note", "B-EQUIVALENT", f"`{fn['name']}` matched main on {len(inputs)} random inputs",
                            "Evidence for the 'no behaviour change' claim. Not a proof.", file=fn["file"], line=fn["line"]))
    return out
