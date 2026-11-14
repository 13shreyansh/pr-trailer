"""Build the static walkthrough page from out/ (run bench.run first)."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT, SITE = ROOT / "out", ROOT / "site"


def main():
    trailers = []
    for f in sorted(OUT.glob("PR-*/trailer.json")):
        t = json.loads(f.read_text())
        t.pop("test_rows", None)
        trailers.append(t)
        ev = f.parent / "evidence"
        if ev.exists():
            dst = SITE / "media" / t["pr"]["id"]
            dst.mkdir(parents=True, exist_ok=True)
            for name in ("walkthrough.mp4", "before.png", "final.png"):
                shutil.copy(ev / name, dst / name)
    bench = json.loads((OUT / "bench.json").read_text())
    data = json.dumps({"trailers": trailers, "bench": bench}).replace("</", "<\\/")
    html = (SITE / "template.html").read_text().replace("/*DATA*/", data)
    (SITE / "index.html").write_text(html)
    print(f"site/index.html: {len(html) // 1024} KB, {len(trailers)} trailers")


if __name__ == "__main__":
    main()
