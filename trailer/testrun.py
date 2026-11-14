"""Run spec tests on base and head; derive per-AC evidence and changed-line coverage."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "_runner.py"
AC_RE = re.compile(r"^(REQ_[A-Z]+_\d+)\.test_(ac\d+)_")


def run_suite(ws: Path) -> dict:
    t0 = time.time()
    p = subprocess.run([sys.executable, "-I", str(RUNNER), str(ws)], capture_output=True, text=True, timeout=120)
    if p.returncode != 0 and not p.stdout:
        raise RuntimeError(p.stderr)
    data = json.loads(p.stdout)
    data["seconds"] = round(time.time() - t0, 2)
    return data


def ac_key(test_id: str):
    m = AC_RE.match(test_id)
    if not m:
        return None
    return m.group(1).replace("_", "-"), m.group(2).upper()


def compare(base: dict, head: dict) -> list[dict]:
    b = {t["id"]: t for t in base["tests"]}
    rows = []
    for t in head["tests"]:
        before = b.get(t["id"], {}).get("status", "absent")
        key = ac_key(t["id"])
        rows.append({
            "id": t["id"], "req": key[0] if key else None, "ac": key[1] if key else None,
            "base": before, "head": t["status"], "detail": t["detail"],
            "regression": before == "pass" and t["status"] != "pass",
            "fixed": before != "pass" and t["status"] == "pass",
        })
    return rows


def covered_lines(head: dict) -> dict:
    cov = {}
    for path, line in head.get("import_lines", []):
        cov.setdefault(path, {}).setdefault(line, set()).add("<import>")
    for t in head["tests"]:
        for path, line in t["lines"]:
            cov.setdefault(path, {}).setdefault(line, set()).add(t["id"])
    return cov
