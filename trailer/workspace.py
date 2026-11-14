"""Materialise the base repo and the PR head into throwaway directories."""
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"
PRS = ROOT / "prs"


def load_pr(pr_id: str) -> dict:
    pr = json.loads((PRS / pr_id / "pr.json").read_text())
    pr["dir"] = PRS / pr_id
    return pr


def all_pr_ids() -> list[str]:
    return sorted(p.name for p in PRS.iterdir() if (p / "pr.json").exists())


def materialise(pr: dict) -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix=f"trailer-{pr['id']}-"))
    base, head = tmp / "base", tmp / "head"
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(BANK, base, ignore=ignore)
    shutil.copytree(BANK, head, ignore=ignore)
    for rel in pr["files"]:
        dst = head / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pr["dir"] / "files" / rel, dst)
    for rel in pr.get("deleted", []):
        (head / rel).unlink(missing_ok=True)
    return base, head


def requirement(req_id: str) -> dict:
    reqs = json.loads((BANK / "requirements.json").read_text())["requirements"]
    return next(r for r in reqs if r["id"] == req_id)


def all_requirements() -> list[dict]:
    return json.loads((BANK / "requirements.json").read_text())["requirements"]


def owner_for(path: str) -> str:
    rules = []
    for line in (BANK / "CODEOWNERS").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            pat, owner = line.split()
            rules.append((pat, owner))
    for pat, owner in rules:
        if pat == "*" or path.startswith(pat):
            return owner
    return "@unowned"
