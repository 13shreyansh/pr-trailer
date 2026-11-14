"""Ask Gemini, once, what design decisions the agent took in each PR and why (cached in app/llm/decisions.json).

Advisory only: the app labels it as the model's reading of the PR, and each item must quote the agent's own words
(PR description or code comment) or say no reason was given. Run: python3 app/llm_decisions.py
"""
import json
import os
import re
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent
OUT = APP.parent / "out"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
PROMPT = """You are reading a pull request written by an AI coding agent at a bank. List the design decisions the agent made
(at most 3), the reason the agent gave, and what the automated review found about each one.

Rules:
- "decision": what the agent chose to do, in plain words, max 15 words. Choices, not restatements of the title.
- "agent_reason": an exact quote from the PR description or a code comment in the diff that explains the choice. If the agent gave no reason, null.
- "review": what the REVIEW FINDINGS say about this decision, max 25 words, or "Nothing flagged." Use only the findings below.
- "file": the file where the decision lives.
Reply with JSON only: {"decisions": [{"decision": "...", "agent_reason": "..." or null, "review": "...", "file": "..."}]}

PR TITLE: {title}
PR DESCRIPTION: {desc}
DIFF:
{diff}

REVIEW FINDINGS AND OPEN QUESTIONS:
{findings}
"""


def ask(prompt):
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 4096, "responseMimeType": "application/json"}}).encode()
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent", data=body,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    j = json.loads(urllib.request.urlopen(req, timeout=120).read())
    txt = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"] if not p.get("thought"))
    return json.loads(txt[txt.index("{"): txt.rindex("}") + 1])


def main():
    res = {}
    for f in sorted(OUT.glob("PR-*/trailer.json")):
        t = json.loads(f.read_text())
        fnd = [f"- [{x['severity']}{', reproduced' if x.get('verified') else ''}] {x['title']}: {x.get('detail') or ''} ({x.get('file')}:{x.get('line')})"
               for x in t["findings"] + t["refusals"]] or ["(none)"]
        prompt = PROMPT.replace("{title}", t["pr"]["title"]).replace("{desc}", t["pr"].get("description") or "").replace(
            "{diff}", "\n".join(d.get("unified", "") for d in t["diff"])[:8000]).replace("{findings}", "\n".join(fnd))
        out = ask(prompt)["decisions"][:3]
        src = (t["pr"].get("description") or "") + "\n" + "\n".join(d.get("unified", "") for d in t["diff"])
        for d in out:  # keep a quote only if it really appears in the agent's words
            q = d.get("agent_reason")
            if q and re.sub(r"\s+", " ", q.strip(" .\"'")).lower() not in re.sub(r"\s+", " ", src).lower():
                d["agent_reason"] = None
                d["quote_dropped"] = True
        res[t["pr"]["id"]] = out
        print(t["pr"]["id"], json.dumps(out)[:400])
    (APP / "llm").mkdir(exist_ok=True)
    (APP / "llm" / "decisions.json").write_text(json.dumps({"model": MODEL, "decisions": res}, indent=1))


if __name__ == "__main__":
    main()
