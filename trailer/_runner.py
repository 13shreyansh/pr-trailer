"""Run the spec suite inside a workspace and record per-test line coverage of ledger/.

Invoked as: python3 -I _runner.py <workspace>  -> JSON on stdout.
"""
import io
import json
import sys
import threading
import unittest
from pathlib import Path

ws = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ws))
prefix = str(ws / "ledger")
current = {"lines": set()}


def tracer(frame, event, arg):
    fn = frame.f_code.co_filename
    if not fn.startswith(prefix):
        return None
    if event == "line":
        current["lines"].add((str(Path(fn).relative_to(ws)), frame.f_lineno))
    return tracer


def global_trace(frame, event, arg):
    if frame.f_code.co_filename.startswith(prefix):
        current["lines"].add((str(Path(frame.f_code.co_filename).relative_to(ws)), frame.f_lineno))
        return tracer
    return None


class Result(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.records = []

    def startTest(self, test):
        super().startTest(test)
        current["lines"] = set()
        sys.settrace(global_trace)

    def _rec(self, test, status, detail=""):
        sys.settrace(None)
        tid = f"{type(test).__name__}.{test._testMethodName}"
        self.records.append({"id": tid, "status": status, "detail": detail[-600:],
                             "lines": sorted(current["lines"])})

    def addSuccess(self, test):
        self._rec(test, "pass")

    def addFailure(self, test, err):
        self._rec(test, "fail", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        self._rec(test, "error", self._exc_info_to_string(err, test))


import logging


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append({"logger": record.name, "level": record.levelname, "msg": record.getMessage()})


cap = Capture()
logging.getLogger().addHandler(cap)
logging.getLogger().setLevel(logging.DEBUG)

# The module import itself counts as coverage of top-level lines.
sys.settrace(global_trace)
suite = unittest.defaultTestLoader.discover(str(ws / "tests"), top_level_dir=str(ws))
sys.settrace(None)
import_lines = sorted(current["lines"])
res = Result()
real_stderr = sys.stderr
sys.stderr = io.StringIO()
suite.run(res)
sys.stderr = real_stderr
inv = []
try:
    import invariants
    for fn in invariants.ALL:
        try:
            inv.append({"id": fn.__name__, "result": fn()})
        except Exception as e:  # an invariant that crashes is a failure too
            inv.append({"id": fn.__name__, "result": f"crashed: {type(e).__name__}: {e}"})
except ImportError:
    pass
json.dump({"tests": res.records, "import_lines": import_lines, "logs": cap.messages, "invariants": inv}, sys.stdout)
