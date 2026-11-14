"""Serve a workspace's API while recording which ledger/ lines run (python3 -I _cover_server.py <ws> <port> <out.json>)."""
import json
import signal
import sys
import threading
from pathlib import Path

ws = Path(sys.argv[1]).resolve()
port, out = int(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(ws))
prefix = str(ws / "ledger")
lines = set()


def tracer(frame, event, arg):
    if event == "line":
        lines.add((str(Path(frame.f_code.co_filename).relative_to(ws)), frame.f_lineno))
    return tracer


def global_trace(frame, event, arg):
    if frame.f_code.co_filename.startswith(prefix):
        lines.add((str(Path(frame.f_code.co_filename).relative_to(ws)), frame.f_lineno))
        return tracer
    return None


def dump(*_):
    out.write_text(json.dumps(sorted(lines)))
    sys.exit(0)


signal.signal(signal.SIGTERM, dump)
threading.settrace(global_trace)
sys.settrace(global_trace)
from ledger import api  # noqa: E402

api.serve(port)
