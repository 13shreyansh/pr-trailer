"""Run UI acceptance tests and record a captioned video against a live server for base or head."""
import contextlib
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ui_spec.js"


def _free_port():
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_ui(ws: Path, out_dir: Path, captions: dict | None = None) -> list[dict]:
    port = _free_port()
    cov_file = out_dir / "_server_coverage.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    srv = subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve().parent / "_cover_server.py"),
                            str(ws), str(port), str(cov_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        p = subprocess.run(["node", str(SCRIPT), f"http://127.0.0.1:{port}/", str(out_dir), json.dumps(captions or {})],
                           capture_output=True, text=True, timeout=180)
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-800:])
        results = json.loads(p.stdout.strip().splitlines()[-1])
    finally:
        srv.terminate()
        srv.wait()
    run_ui.last_coverage = [tuple(x) for x in json.loads(cov_file.read_text())] if cov_file.exists() else []
    cov_file.unlink(missing_ok=True)
    webm = out_dir / "walkthrough.webm"
    if webm.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), "-movflags", "+faststart",
                        "-pix_fmt", "yuv420p", "-vf", "scale=640:-2", str(out_dir / "walkthrough.mp4")], check=False)
        webm.unlink()
    return results
