"""Render a trailer as a Markdown PR comment."""

ICON = {"pass": "✅", "fail": "❌", "error": "❌", "no test": "⚪", "absent": "·"}


def markdown(t: dict) -> str:
    pr, req, d, s = t["pr"], t["requirement"], t["danger"], t["signoff"]
    L = [f"## PR trailer · {pr['id']} · {req['id']} {req['title']}", "",
         f"**Routing: {t['decision']['label']}.** {t['decision']['why']}", "",
         f"> {pr['description']}", "",
         "### Evidence per acceptance criterion", "", "| AC | Criterion | Claimed | Evidence | Result |", "|---|---|---|---|---|"]
    for e in t["evidence"]:
        ev = "<br>".join(f"`{x['id']}` {ICON.get(x['base'],'')}→{ICON.get(x['head'],'')}" for x in e["tests"]) or "none"
        L.append(f"| {e['ac']} | {e['text']} | {'yes' if e['claimed'] else ''} | {ev} | {ICON[e['status']]} {e['status']} |")
    if t.get("video"):
        L += ["", f"🎬 UI walkthrough: `{t['video']}` (before/after stills in `evidence/`)"]
    if t.get("sequence"):
        L += ["", "### What the changed code does", "", "```mermaid", t["sequence"], "```"]
    L += ["", "### What the AI found"]
    if not t["findings"]:
        L.append("Nothing. That is not proof of correctness; see *Not checked* below.")
    for f in t["findings"]:
        tag = "verified" if f["verified"] else "unverified, advice only"
        loc = f" `{f['file']}:{f['line']}`" if f["file"] else ""
        L.append(f"- **{f['title']}**{loc} ({tag}). {f['detail']}")
        if f.get("verification"):
            L.append(f"  - How it was verified: {f['verification']}")
        if f.get("evidence"):
            L.append(f"  - Evidence: `{str(f['evidence'])[:220]}`")
    L += ["", "### What the AI refused to decide"]
    if not t["refusals"]:
        L.append("Nothing open.")
    for r in t["refusals"]:
        loc = f" `{r['file']}:{r['line']}`" if r["file"] else ""
        L.append(f"- **{r['title']}**{loc}. {r['detail']}".replace("\n", " "))
        L.append(f"  - ❓ {r['ask']} → {r['owner']}")
    L += ["", "### Merge danger", "",
          f"- **Door:** {d['door']}. " + " ".join(d["reasons"]),
          f"- **Blast radius:** {d['blast_radius']}. Changed: {', '.join(d['changed_functions']) or 'no Python functions'}"
          + (f"; reached from {', '.join(d['surfaces'])}" if d["surfaces"] else "")]
    L += ["", "### Sign-off card", "",
          f"**Owner:** {s['owner']}" + (f" · co-sign: {', '.join(s['co_signers'])}" if s["co_signers"] else ""), "",
          "**Checked**"] + [f"- {x}" for x in s["checked"]]
    L += ["", "**Not checked**"] + [f"- {x}" for x in s["not_checked"]]
    L += ["", "**Residual risk the owner accepts**"] + [f"- {x}" for x in s["residual_risk"]]
    if s["questions"]:
        L += ["", "**Must be answered before merge**"] + [f"- [ ] {q['q']} ({q['owner']})" for q in s["questions"]]
    L += ["", f"- [ ] I, {s['owner']}, accept this change and the residual risk above. The AI review was advice, not approval."]
    return "\n".join(L) + "\n"
