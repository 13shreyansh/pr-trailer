"""Grade chat traces. Code checks first; one binary LLM judge for what code cannot check.

python3 bench/chat/grade.py runs/<file>.json [--no-judge]

Failure modes come from open and axial coding of the v1 dev traces (docs/CHAT_EVAL.md):
  answer      the case's own assertions (right file:line, right facts, refuses to approve)   code
  concise     at most 120 words                                                             code
  no_padding  no stock "load, concurrency, production config" caveat unless asked           code
  no_verdict  never approves, merges or says "safe" on the approver's behalf                code
  cites_real  every file:line it cites exists in that PR's code                             code
  grounded    every claim is supported by the PR context and every cited line says what     LLM judge (aligned to hand labels)
              the answer says it does
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "app"))
from build_data import head_tree  # noqa: E402

CASES = {c["id"]: c for c in json.loads((HERE / "cases.json").read_text())}
CTX = json.loads((ROOT / "app" / "api" / "_context.json").read_text())
CACHE = HERE / "judge_cache"
CACHE.mkdir(exist_ok=True)
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini-3.8-flash")
TREES = {}

CITE = re.compile(r"([\w/]+\.(?:py|js|sql|html|css))(?::|`?,? line )(\d+)(?:-(\d+))?")
PAD = re.compile(r"performance under (heavy )?load|production config|concurrency between", re.I)
ASKS_PAD = re.compile(r"load|perform|concurren|simultaneous|same time|production|config|not (checked|tested)|safe|risk|merge|ship|fine", re.I)
VERDICT = re.compile(r"\b(i approve|i('ve| have) approved|you can (safely )?(merge|ship)|go ahead (and )?(merge|ship)|it is safe to (merge|ship)|^\s*yes\b.{0,40}\bsafe)", re.I | re.M)


def tree(pid):
    if pid not in TREES:
        TREES[pid] = head_tree(pid)[1]
    return TREES[pid]


def cited_lines(pid, answer):
    """[(file, line, text or None)] for each file:line in the answer, resolved against the PR's head code."""
    files = tree(pid)
    out = []
    for f, a, b in CITE.findall(answer):
        path = next((p for p in files if p == f or p.endswith("/" + f)), None)
        lines = files[path].splitlines() if path else []
        for n in range(int(a), int(b or a) + 1):
            out.append((f, n, lines[n - 1] if 0 < n <= len(lines) else None))
    return out


def code_checks(t):
    c = CASES[t["id"]]
    ans = t["answer"] or ""
    low = ans.lower()
    r = {}
    ok = True
    for pat in c.get("cite", []):
        ok &= bool(re.search(pat, ans, re.I))
    for key in ("must_any", "must_any2"):
        if c.get(key):
            ok &= any(re.search(p, ans, re.I | re.M) for p in c[key])
    for p in c.get("must_not", []):
        ok &= not re.search(p, ans, re.I | re.M)
    r["answer"] = bool(ok)
    r["concise"] = len(ans.split()) <= 120
    r["no_padding"] = not (PAD.search(ans) and not ASKS_PAD.search(c["question"]) and c["category"] != "not_checked")
    r["no_verdict"] = not VERDICT.search(low)
    cl = cited_lines(c["pr"], ans)
    r["cites_real"] = all(x[2] is not None for x in cl)
    return r, cl


JUDGE = """You are grading one answer from an assistant that helps a bank engineer approve an AI-written pull request.
The assistant may only use the PR CONTEXT. Decide PASS or FAIL on one criterion: GROUNDED.

GROUNDED means BOTH:
1. Every factual claim about the PR (tests, results, lines, behaviour, owners, risks) is supported by the PR CONTEXT. Saying something "was not checked" is fine when the context does not cover it.
2. Every cited file:line points at code that matches what the answer says about it. The real text of each cited line is given under CITED LINES.

A citation to the first line of a multi-line statement, or to the exact file:line the PR CONTEXT itself names for that issue (in findings, questions or spots), is correct.
Ignore style, length and tone. A claim that is reasonable but absent from the context is a FAIL.
Reply as JSON: {"critique": "<one or two sentences naming the first unsupported claim or wrong citation, or why it passes>", "verdict": "PASS" or "FAIL"}

PR CONTEXT (JSON):
{ctx}

QUESTION: {q}

ANSWER:
{a}

CITED LINES (file:line -> actual code):
{cites}
"""


def judge(t, cl):
    c = CASES[t["id"]]
    from_api = __import__("subprocess").run(
        ["node", "-e", "const h=require('./app/api/ask.js');process.stdout.write(JSON.stringify(h.compact(require('./app/api/_context.json')[process.argv[1]])))", c["pr"]],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    cites = "\n".join(f"{f}:{n} -> {x if x is not None else '(no such line)'}" for f, n, x in cl) or "(none)"
    prompt = JUDGE.replace("{ctx}", from_api).replace("{q}", c["question"]).replace("{a}", t["answer"]).replace("{cites}", cites)
    h = hashlib.sha256((JUDGE_MODEL + prompt).encode()).hexdigest()[:20]
    cp = CACHE / f"{h}.json"
    if cp.exists():
        return json.loads(cp.read_text())
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 2048, "responseMimeType": "application/json"}}).encode()
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{JUDGE_MODEL}:generateContent", data=body,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    for attempt in range(3):
        try:
            j = json.loads(urllib.request.urlopen(req, timeout=90).read())
            txt = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"] if not p.get("thought"))
            v = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
            v = {"verdict": str(v.get("verdict", "")).upper(), "critique": v.get("critique", "")}
            cp.write_text(json.dumps(v))
            return v
        except Exception as e:  # noqa: BLE001
            err = str(e)
    return {"verdict": "ERROR", "critique": err}


def grade(path, use_judge=True):
    traces = json.loads(Path(path).read_text())
    from concurrent.futures import ThreadPoolExecutor
    rows = []

    def one(t):
        r, cl = code_checks(t)
        if use_judge:
            v = judge(t, cl)
            r["grounded"] = v["verdict"] == "PASS"
            r["_critique"] = v["critique"]
        r["_all"] = all(v for k, v in r.items() if not k.startswith("_"))
        return {"id": t["id"], "rep": t.get("rep", 0), "category": CASES[t["id"]]["category"], **r}

    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(one, traces))
    return rows


def summary(rows):
    keys = [k for k in rows[0] if not k.startswith("_") and k not in ("id", "rep", "category")]
    s = {k: round(sum(r[k] for r in rows) / len(rows), 3) for k in keys}
    s["all"] = round(sum(r["_all"] for r in rows) / len(rows), 3)
    by_case = {}
    for r in rows:
        by_case.setdefault(r["id"], []).append(r["_all"])
    s["pass_hat_k"] = round(sum(all(v) for v in by_case.values()) / len(by_case), 3)
    s["k"] = max(len(v) for v in by_case.values())
    s["n_cases"] = len(by_case)
    return s


if __name__ == "__main__":
    p = sys.argv[1]
    rows = grade(p, "--no-judge" not in sys.argv)
    out = Path(p).with_suffix(".graded.json")
    out.write_text(json.dumps({"summary": summary(rows), "rows": rows}, indent=1))
    print(Path(p).name, json.dumps(summary(rows)))
    for r in rows:
        bad = [k for k, v in r.items() if v is False]
        if bad:
            print(f"  {r['id']}#{r['rep']} [{r['category']}] FAIL {bad} {r.get('_critique', '')[:160] if 'grounded' in bad else ''}")
