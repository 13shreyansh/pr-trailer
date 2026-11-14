"""Optional LLM reviewer (Gemini). Its findings are advice: they can route attention, never block.

Every LLM finding must quote the exact code it is about. The grounding filter checks that the quote
exists in the PR head within 3 lines of the cited line. Findings that fail are dropped and counted
as hallucinations, so the trailer can report the reviewer's hallucination rate.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

from .checks import item

PROMPT = """You are reviewing an AI-written pull request for a retail bank.
Requirement {rid} "{title}": {intent}
Acceptance criteria:
{acs}
PR description (written by the coding agent, may be wrong): {desc}

Diff:
{diff}

List real defects only: correctness, security, privacy, money handling, data loss.
Do not comment on style. If you are not sure, leave it out.
Answer with JSON only: {{"findings": [{{"file": "...", "line": <int, line in the NEW file>,
"quote": "<exact code copied from that line>", "claim": "<one sentence>", "severity": "high|medium|low"}}]}}"""


def ground(findings: list, head: Path):
    kept, dropped = [], []
    for f in findings:
        path = head / str(f.get("file", ""))
        quote = " ".join(str(f.get("quote", "")).split())
        ok = False
        if path.is_file() and quote:
            lines = path.read_text().splitlines()
            n = int(f.get("line") or 0)
            window = " ".join(" ".join(l.split()) for l in lines[max(0, n - 4): n + 3])
            ok = quote in window
        (kept if ok else dropped).append(f)
    return kept, dropped


class Gemini:
    def __init__(self, model=None, replay_dir=None):
        self.key = os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        self.replay_dir = Path(replay_dir) if replay_dir else None
        self.stats = {"raw": 0, "grounded": 0, "hallucinated": 0}

    def _ask(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.key})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    def review(self, pr, req, diffs, head: Path) -> list:
        cache = (self.replay_dir / f"{pr['id']}.json") if self.replay_dir else None
        if cache and cache.exists():
            raw = cache.read_text()
        else:
            if not self.key:
                raise RuntimeError("Set GEMINI_API_KEY (or pass a replay dir) to use the LLM reviewer")
            acs = "\n".join(f"- {a['ac']}: {a['text']}" for a in req["acceptance"])
            prompt = PROMPT.format(rid=req["id"], title=req["title"], intent=req["intent"], acs=acs,
                                   desc=pr["description"], diff="\n\n".join(d["unified"] for d in diffs))
            try:
                raw = self._ask(prompt)
            except (TimeoutError, OSError):
                raw = self._ask(prompt)  # one retry on a slow answer
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(raw)
        m = re.search(r"\{.*\}", raw, re.S)
        findings = json.loads(m.group(0)).get("findings", []) if m else []
        kept, dropped = ground(findings, head)
        self.stats["raw"] += len(findings)
        self.stats["grounded"] += len(kept)
        self.stats["hallucinated"] += len(dropped)
        out = [item("finding", "L-LLM", f"LLM reviewer: {f['claim']}", f"Quoted: `{f['quote']}`",
                    file=f["file"], line=f.get("line"), severity="warn", verified=False,
                    verification=None, evidence=f"model={self.model}, grounded quote, not reproduced")
               for f in kept]
        if dropped:
            out.append(item("note", "L-DROPPED", f"{len(dropped)} LLM finding(s) dropped as ungrounded",
                            "; ".join(f"{d.get('file')}:{d.get('line')} “{str(d.get('quote'))[:60]}”" for d in dropped)))
        return out
