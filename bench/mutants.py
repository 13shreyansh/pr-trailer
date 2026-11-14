"""Generate unbiased synthetic 'agent PRs' by mutating the sample bank.

Hand-planted bugs are written by the same people who wrote the checks, so they flatter the checks.
Mutants are generated mechanically, so the catch rate on them is a fairer estimate.
"""
import ast
import json
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"
FILE_REQ = {"ledger/fees.py": "REQ-PAY-204", "ledger/transfers.py": "REQ-PAY-210", "ledger/money.py": "REQ-MNY-220",
            "ledger/auth.py": "REQ-SEC-301", "ledger/audit.py": "REQ-OBS-401", "ledger/iban.py": "REQ-PAY-201",
            "ledger/statements.py": "REQ-DATA-502"}
SWAP = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "==", "+": "-", "-": "+", "*": "//"}


def _op_site(src_lines, left, right):
    if left.end_lineno != right.lineno:
        return None
    line = src_lines[left.end_lineno - 1]
    seg = line[left.end_col_offset:right.col_offset]
    tok = seg.strip()
    if tok in SWAP:
        start = left.end_col_offset + seg.index(tok)
        return left.end_lineno, start, start + len(tok), tok, SWAP[tok]
    return None


def sites(rel: str):
    src = (BANK / rel).read_text()
    lines = src.splitlines()
    tree = ast.parse(src)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            s = _op_site(lines, n.left, n.comparators[0])
            if s:
                out.append(("op",) + s)
        elif isinstance(n, ast.BinOp):
            s = _op_site(lines, n.left, n.right)
            if s:
                out.append(("op",) + s)
        elif isinstance(n, ast.Constant) and type(n.value) is int and n.lineno == n.end_lineno and n.value not in (0, 1):
            seg = lines[n.lineno - 1][n.col_offset:n.end_col_offset]
            out.append(("const", n.lineno, n.col_offset, n.end_col_offset, seg, str(n.value + 1)))
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and n.lineno == n.end_lineno:
            line = lines[n.lineno - 1]
            out.append(("delete", n.lineno, n.col_offset, len(line), line[n.col_offset:], "pass"))
        elif isinstance(n, ast.Raise) and n.lineno == n.end_lineno:
            line = lines[n.lineno - 1]
            out.append(("delete", n.lineno, n.col_offset, len(line), line[n.col_offset:], "pass"))
    return out


def heldout_sites(rel: str):
    """Operator families never used while the checks were tuned. Frozen: do not tune checks on these."""
    src = (BANK / rel).read_text()
    lines = src.splitlines()
    tree = ast.parse(src)
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                  and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.BoolOp) and len(n.values) == 2 and n.lineno == n.end_lineno:
            a, b = n.values
            seg = lines[n.lineno - 1][a.end_col_offset:b.col_offset]
            tok = seg.strip()
            if tok in ("and", "or"):
                c0 = a.end_col_offset + seg.index(tok)
                out.append(("bool", n.lineno, c0, c0 + len(tok), tok, "or" if tok == "and" else "and"))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings \
                and n.lineno == n.end_lineno and n.value:
            seg = lines[n.lineno - 1][n.col_offset:n.end_col_offset]
            if " AND " in n.value:  # neutralise the second WHERE predicate
                head, rest = seg.split(" AND ", 1)
                cut = min([i for i in (rest.find(" AND "), rest.find(seg[-1])) if i >= 0])
                out.append(("sql-pred", n.lineno, n.col_offset, n.end_col_offset, seg, head + " AND 1 = 1" + rest[cut:]))
            elif n.value.isidentifier() and len(n.value) < 20:
                out.append(("str", n.lineno, n.col_offset, n.end_col_offset, seg, seg[0] + n.value + "_x" + seg[-1]))
        elif isinstance(n, ast.Call) and len(n.args) == 2 and all(isinstance(x, ast.Name) for x in n.args) \
                and n.lineno == n.end_lineno:
            a, b = n.args
            line = lines[n.lineno - 1]
            out.append(("arg-swap", n.lineno, a.col_offset, b.end_col_offset, line[a.col_offset:b.end_col_offset],
                        f"{b.id}, {a.id}"))
    return out


def generate(dest: Path, n=60, seed=11, family="dev"):
    rng = random.Random(seed)
    finder = sites if family == "dev" else heldout_sites
    all_sites = [(rel, s) for rel in FILE_REQ for s in finder(rel)]
    rng.shuffle(all_sites)
    chosen = all_sites[:n]
    if dest.exists():
        shutil.rmtree(dest)
    truth = {}
    for i, (rel, (kind, line, c0, c1, old, new)) in enumerate(chosen, 1):
        pid = f"{'MUT' if family == 'dev' else 'HLD'}-{i:03d}"
        lines = (BANK / rel).read_text().splitlines(keepends=True)
        text = lines[line - 1]
        lines[line - 1] = text[:c0] + new + text[c1:] if kind != "delete" else text[:c0] + "pass\n"
        f = dest / pid / "files" / rel
        f.parent.mkdir(parents=True)
        f.write_text("".join(lines))
        (dest / pid / "pr.json").write_text(json.dumps({
            "id": pid, "requirement": FILE_REQ[rel], "title": f"Small cleanup in {rel}",
            "author": "agent:mutator", "description": "Tidy-up; no functional change intended.",
            "behavior_change": False, "files": [rel], "deleted": [], "claims_acs": []}, indent=2))
        truth[pid] = {"file": rel, "line": line, "mutation": f"{kind}: {old.strip()} -> {new}"}
    (dest / "truth.json").write_text(json.dumps(truth, indent=2))
    return truth
