"""File-level diff with added/removed line numbers."""
import difflib
from pathlib import Path


def diff_pr(base: Path, head: Path, files: list[str]) -> list[dict]:
    out = []
    for rel in files:
        a = (base / rel).read_text().splitlines() if (base / rel).exists() else []
        b = (head / rel).read_text().splitlines() if (head / rel).exists() else []
        added, removed = [], []
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("replace", "delete"):
                removed += [(i + 1, a[i]) for i in range(i1, i2)]
            if tag in ("replace", "insert"):
                added += [(j + 1, b[j]) for j in range(j1, j2)]
        unified = "\n".join(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}", lineterm="", n=2))
        out.append({
            "path": rel, "status": "added" if not a else ("deleted" if not b else "modified"),
            "added": added, "removed": removed, "unified": unified,
        })
    return out


def lines_changed(diffs) -> int:
    return sum(len(d["added"]) + len(d["removed"]) for d in diffs)
