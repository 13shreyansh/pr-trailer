"""Build app/data.json (and app/api/_context.json) from out/PR-*/trailer.json, the bank code and bench results.

python3 app/build_data.py   (run after python3 -m bench.run)
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
OUT = ROOT / "out"
BANK = ROOT / "bank"
CODE_GLOBS = ["ledger/*.py", "web/*", "migrations/*.sql"]
OWNERS = [l.split() for l in (BANK / "CODEOWNERS").read_text().splitlines() if l.strip() and not l.startswith("#")]


def owner_of(path):
    for prefix, who in OWNERS:
        if prefix == "*" or path.startswith(prefix):
            return who
    return None


def head_tree(pid):
    pr = json.loads((ROOT / "prs" / pid / "pr.json").read_text())
    files = {}
    for g in CODE_GLOBS:
        for p in sorted(BANK.glob(g)):
            if p.name == "__init__.py":
                continue
            files[str(p.relative_to(BANK))] = p.read_text()
    over = ROOT / "prs" / pid / "files"
    for p in over.rglob("*"):
        if p.is_file():
            files[str(p.relative_to(over))] = p.read_text()
    for d in pr.get("deleted", []):
        files.pop(d, None)
    return pr, files


def changed_lines(unified):
    added, removed_at, n = set(), set(), 0
    for line in unified.splitlines():
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            n = int(m.group(1))
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added.add(n); n += 1
        elif line.startswith("-"):
            removed_at.add(n)
        else:
            n += 1
    return added, removed_at


def window(lines, center, k=3):
    lo, hi = max(1, center - k), min(len(lines), center + k)
    return list(range(lo, hi + 1))


def build_pr(t):
    pid = t["pr"]["id"]
    pr, files = head_tree(pid)
    diff = {d["path"]: d for d in t["diff"]}
    state = {}  # path -> {line: kind}
    removed = {}
    for path, d in diff.items():
        if path in files:
            a, r = changed_lines(d.get("unified", ""))
            if d.get("status") == "added":
                a = set(range(1, len(files[path].splitlines()) + 1))
            state[path] = {n: "changed" for n in a}
            removed[path] = sorted(r)
    changed_mods = {Path(p).stem for p in diff if p.startswith("ledger/")}
    danger = t["danger"]
    affected = {}
    for path, text in files.items():
        if path in diff:
            continue
        why = []
        if path.endswith(".py"):
            for mod in changed_mods:
                if re.search(rf"from \.{mod} import|from \. import .*\b{mod}\b", text):
                    why.append(f"imports {mod}.py")
        for fn in danger.get("callers", []):
            for i, l in enumerate(text.splitlines(), 1):
                if re.match(rf"\s*def {re.escape(fn)}\(", l):
                    state.setdefault(path, {})[i] = "caller"
                    why.append(f"{fn}() calls the changed code")
        if path.startswith("web/"):
            for s in danger.get("surfaces", []):
                route = s.split(" ")[-1]
                if route in text:
                    why.append(f"calls {s}")
        if path.startswith("migrations/") and danger.get("tables"):
            for tb in danger["tables"]:
                if re.search(rf"\b{tb}\b", text):
                    why.append(f"defines table {tb}")
        if why:
            affected[path] = sorted(set(why))
    # spots with code
    read = {}
    spots = []
    for s in t.get("spots", []):
        f, ln = s.get("file"), s.get("line")
        snippet, hl = None, []
        if f and f in files:
            lines = files[f].splitlines()
            if ln:
                nums = window(lines, ln)
                hl = [ln]
            else:
                ch = sorted(state.get(f, {}).keys())
                ch = [n for n in ch if state[f][n] == "changed"]
                nums = sorted({x for n in ch[:12] for x in window(lines, n, 1)})[:14] if ch else list(range(1, min(len(lines), 8) + 1))
                hl = ch[:12]
            snippet = [{"n": n, "text": lines[n - 1], "changed": state.get(f, {}).get(n) == "changed", "hl": n in hl}
                       for n in nums]
            read.setdefault(f, set()).update(nums)
            for n in nums:
                if state.get(f, {}).get(n) != "changed":
                    state.setdefault(f, {}).setdefault(n, "read")
            for n in hl:
                state.setdefault(f, {})[n] = "spot" if state.get(f, {}).get(n) != "changed" else "changed-spot"
        spots.append({**s, "owner": owner_of(f) if f else None, "snippet": snippet})
    total = sum(len(v.splitlines()) for v in files.values())
    to_read = sum(len(v) for v in read.values())
    cmap = []
    for path, text in files.items():
        lines = text.splitlines()
        cmap.append({"path": path, "n": len(lines), "status": "changed" if path in diff else ("affected" if path in affected else "untouched"),
                     "why": affected.get(path, []), "owner": owner_of(path),
                     "lines": [[min(len(l.rstrip()), 90), len(l) - len(l.lstrip()), state.get(path, {}).get(i + 1, "")] for i, l in enumerate(lines)],
                     "removed": removed.get(path, [])})
    for d in pr.get("deleted", []):
        cmap.append({"path": d, "n": 0, "status": "deleted", "why": [], "owner": owner_of(d), "lines": [], "removed": []})
    media = None
    ev = OUT / pid / "evidence"
    if t.get("video") and ev.exists():
        dst = APP / "media" / pid
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("walkthrough.mp4", "before.png", "final.png"):
            shutil.copy(ev / name, dst / name)
        media = {"video": f"media/{pid}/walkthrough.mp4", "before": f"media/{pid}/before.png", "after": f"media/{pid}/final.png"}
    return {
        "id": pid, "title": t["pr"]["title"], "author": t["pr"].get("author"), "description": t["pr"].get("description"),
        "behavior_change": t["pr"].get("behavior_change"),
        "requirement": t["requirement"], "decision": t["decision"], "outcome": t["outcome"],
        "danger": danger, "confidence": t["confidence"], "scope": t["scope"],
        "evidence": t["evidence"], "checked": t["checked"], "signoff": t["signoff"],
        "findings": t["findings"], "refusals": t["refusals"], "notes": t.get("notes", []),
        "sequence": t.get("sequence"), "media": media, "spots": spots,
        "diff": [{"path": d["path"], "status": d.get("status"), "added": d["added"], "removed": d["removed"], "unified": d.get("unified", "")}
                 for d in t["diff"]],
        "lines_changed": t["lines_changed"], "map": cmap,
        "stats": {"codebase_lines": total, "files": len(files), "files_changed": len(diff),
                  "files_affected": len(affected), "lines_to_read": to_read},
    }


def base_tree():
    files = {}
    for g in CODE_GLOBS:
        for p in sorted(BANK.glob(g)):
            if p.name != "__init__.py":
                files[str(p.relative_to(BANK))] = p.read_text()
    return files


def run_module(src, calls):
    """Execute a self-contained module (fees.py / money.py import only decimal) and call functions on sample inputs."""
    ns = {}
    exec(compile(src, "<pr>", "exec"), ns)
    out = []
    for fn, args in calls:
        try:
            out.append(repr(ns[fn](*args)))
        except Exception as e:  # noqa: BLE001
            out.append(f"error: {type(e).__name__}")
    return out


SAMPLES = {
    "ledger/fees.py": [("transfer_fee", (a, "instant")) for a in (10_000, 25_000, 57_250, 75_250, 250_000, 400_000)]
                      + [("transfer_fee", (57_250, "sepa"))],
    "ledger/money.py": [("to_cents", (x,)) for x in ("19.99", "0.29", "12,34", "19985.01")]
                       + [("format_amount", (123456,))],
}


def before_after(pid, files):
    """Inputs where main and this PR give different answers, computed by running both versions of the code."""
    base = base_tree()
    tables = []
    for path, calls in SAMPLES.items():
        if path in files and files[path] != base.get(path):
            a, b = run_module(base[path], calls), run_module(files[path], calls)
            rows = [{"call": f"{fn}({', '.join(repr(x) for x in args)})", "main": x, "pr": y, "differs": x != y}
                    for (fn, args), x, y in zip(calls, a, b)]
            tables.append({"file": path, "rows": rows})
    return tables


def sandbox_card(t):
    c = t["checked"]
    st = c.get("spec_tests") or {}
    items = [f"{st.get('total', 0)} acceptance tests ran on main and on this PR in a throwaway copy of the repo ({st.get('seconds', 0)} s): "
             f"{st.get('regressions', 0)} broke, {st.get('pass', 0)} pass, {st.get('already_failing', 0)} fail on both (features not built yet)"]
    if c.get("ui_tests"):
        u = c["ui_tests"]
        items.append(f"UI tests in a real browser (Chromium), with a recorded video: {u if isinstance(u, str) else json.dumps(u)}")
    inv = c.get("invariants") or []
    if inv:
        items.append(f"{sum(1 for i in inv if i['ok'])} of {len(inv)} money invariants hold: " + ", ".join(i["id"].replace("_", " ") for i in inv))
    rules = c.get("rules") or []
    if rules:
        items.append("Checks run on the diff: " + ", ".join(rules))
    return {"items": items, "regressions": st.get("regressions", 0)}


def formats(p, tables):
    """Pick how a human should look at this change, and say which rule picked it."""
    out = []
    tier = p["decision"]["tier"]
    ui = [d["path"] for d in p["diff"] if d["path"].startswith("web/")]
    if p.get("media"):
        out.append({"kind": "video", "title": "Watch the screen",
                    "rule": f"It changes what customers see ({', '.join(ui)}). A recording of the real page before and after says more than the diff."})
    if tables and any(r["differs"] for tb in tables for r in tb["rows"]):
        out.append({"kind": "table", "title": "Compare the numbers",
                    "rule": "It changes how money is calculated. We ran main and this PR on the same amounts; the rows that differ are what customers would feel."})
    elif tables:
        out.append({"kind": "table", "title": "Compare the numbers",
                    "rule": "It touches money code. We ran main and this PR on the same amounts to show nothing moved that should not."})
    d = p["danger"]
    if p.get("sequence") and (d.get("callers") or len(d.get("changed_functions", [])) > 1):
        out.append({"kind": "diagram", "title": "Follow the call path",
                    "rule": f"It changes code that other code calls ({', '.join((d.get('callers') or d.get('changed_functions'))[:3])}). A diagram shows the path a request takes through it."})
    qs = [s for s in p["spots"] if s["kind"] == "refusal"]
    if qs and tier != "return":
        out.append({"kind": "audio", "title": "Listen to the briefing",
                    "rule": f"It has {len(qs)} question{'s' if len(qs) != 1 else ''} only a person can answer. A short spoken briefing lets the owner think about them away from the screen."})
    if tier == "return":
        out.append({"kind": "fixlist", "title": "Nothing for you yet",
                    "rule": "A problem was reproduced, so the agent gets a fix list first. You review the fixed version."})
    elif p["stats"]["lines_to_read"]:
        out.append({"kind": "read", "title": f"Read {p['stats']['lines_to_read']} lines",
                    "rule": "Only the lines tied to an open question or an unproven claim. The rest is covered by the evidence above."})
    return out


def briefing(p):
    """Spoken briefing, built only from trailer fields (no model writes it)."""
    o = p["outcome"]
    words = {"yes": "yes", "no": "no", "unproven": "not proven"}
    parts = [f"{p['id']}. {p['title']}. Written by the agent {(p.get('author') or '').replace('agent:', '')}.",
             f"It is meant to do this: {p['requirement']['intent']}",
             f"Does it do that? {words.get(o['does_it']['verdict'], o['does_it']['verdict'])}. {o['does_it']['why']}",
             f"Does it do anything else? {'no' if o['nothing_else']['verdict'] == 'yes' else 'possibly'}. {o['nothing_else']['why']}"]
    qs = [s for s in p["spots"] if s["kind"] == "refusal"]
    if qs:
        parts.append(f"There {'is one question' if len(qs) == 1 else f'are {len(qs)} questions'} for you.")
        for i, q in enumerate(qs, 1):
            parts.append(f"Question {i}: {q['what']}. {q['why']}")
    parts.append(f"Can it be undone? {p['danger']['door']}. {' '.join(p['danger'].get('reasons') or [])}")
    parts.append(f"Lane: {p['decision']['label']}. The decision is yours.")
    return " ".join(x.strip() for x in parts if x.strip())


def main():
    if (APP / "media").exists():
        shutil.rmtree(APP / "media")
    prs = []
    decisions = json.loads((APP / "llm" / "decisions.json").read_text())["decisions"] if (APP / "llm" / "decisions.json").exists() else {}
    for f in sorted(OUT.glob("PR-*/trailer.json")):
        t = json.loads(f.read_text())
        p = build_pr(t)
        files = head_tree(p["id"])[1]
        p["tables"] = before_after(p["id"], files)
        p["sandbox"] = sandbox_card(t)
        p["formats"] = formats(p, p["tables"])
        p["briefing"] = briefing(p)
        p["agent_decisions"] = decisions.get(p["id"])
        prs.append(p)
    bench = json.loads((OUT / "bench.json").read_text())
    ai = OUT / "ai_compare.json"
    data = {"prs": prs, "bench": {"samples": bench["samples"]["summary"], "rows": bench["samples"]["rows"],
                                  "mutants": bench.get("mutants", {}).get("summary"), "heldout": bench.get("heldout", {}).get("summary"),
                                  "baselines": bench.get("baselines"), "assumptions": bench.get("assumptions")},
            "ai": json.loads(ai.read_text()) if ai.exists() else None,
            "effort": json.loads((OUT / "effort.json").read_text()) if (OUT / "effort.json").exists() else None,
            "chat_eval": json.loads((OUT / "chat_eval.json").read_text()) if (OUT / "chat_eval.json").exists() else None}
    (APP / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    ctx = {p["id"]: {k: p[k] for k in ("id", "title", "description", "requirement", "decision", "outcome", "danger",
                                       "evidence", "checked", "signoff", "findings", "refusals", "notes", "spots", "diff", "stats", "tables")}
           for p in prs}
    for p in ctx.values():
        for s in p["spots"]:
            s.pop("snippet", None)
    (APP / "api" / "_context.json").write_text(json.dumps(ctx, separators=(",", ":")))
    for p in prs:
        s = p["stats"]
        print(f"{p['id']}: {[x['kind'] for x in p['formats']]} tables={[(t['file'], sum(r['differs'] for r in t['rows'])) for t in p['tables']]}")
        print(f"   {p['decision']['tier']:8} files {s['files_changed']}+{s['files_affected']}/{s['files']}  read {s['lines_to_read']}/{s['codebase_lines']}")


if __name__ == "__main__":
    main()
