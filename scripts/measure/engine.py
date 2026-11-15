"""Removal trials against a fixed test oracle. Labels are block-level, not proofs of intent."""
import dataclasses
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
# Follow the active environment in clean CI checkouts as well as a local venv.
PYTHON = sys.executable


def digest(data):
    return hashlib.sha256(data).hexdigest()


@dataclasses.dataclass
class Block:
    id: str
    path: str
    name: str
    start: int
    end: int
    old: list
    new: list

    @property
    def lines(self):
        return sum((j-i)+(b-a) for tag,i,j,a,b in difflib.SequenceMatcher(None,self.old,self.new,autojunk=False).get_opcodes() if tag != "equal")


def blocks_for(path, before, after, whole=False):
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    if whole:
        return [Block(path + ':0', path, Path(path).stem.replace('_', ' ').capitalize(), 0, len(old), old, new)] if old != new else []
    out = []
    for tag, i, j, a, b in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag != 'equal':
            out.append(Block(f'{path}:{i}', path, Path(path).stem.replace('_', ' ').capitalize(), i, j, old[i:j], new[a:b]))
    return out


def materialize(base, work, blocks, selected):
    by_path = {}
    for block in blocks:
        by_path.setdefault(block.path, []).append(block)
    for path, pieces in by_path.items():
        target = work / path
        original = base / path
        lines = original.read_text().splitlines(keepends=True) if original.exists() else []
        for block in sorted(pieces, key=lambda b: b.start, reverse=True):
            if block.id in selected:
                lines[block.start:block.end] = block.new
        if not lines and not original.exists():
            if target.exists():
                target.unlink()  # disposable trial file, never a user artifact
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(''.join(lines))


def run_check(work, tests, log_dir, label, python=None, timeout=45, command_prefix=(), env_overrides=None):
    python = python or PYTHON
    log_dir.mkdir(parents=True, exist_ok=True)
    report = log_dir / (label + '.xml')
    command = [*command_prefix, python, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--junitxml=' + str(report.resolve()), *tests]
    started = time.monotonic()
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'SYSTEMROOT', 'TMPDIR') if k in os.environ}
    env.update(PYTHONPATH=os.pathsep.join([str(work / 'src'), str(work), *sys.path]), PYTHONDONTWRITEBYTECODE='1')
    env.update(env_overrides or {})
    try:
        proc = subprocess.run(command, cwd=work, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output, code = proc.stdout, proc.returncode
    except subprocess.TimeoutExpired as exc:
        output, code = str(exc), 124
    cases = []
    if report.exists():
        for c in ET.parse(report).iter('testcase'):
            bad = c.find('failure') if c.find('failure') is not None else c.find('error')
            cases.append({'name': c.get('classname', '') + '.' + c.get('name', ''), 'passed': bad is None and c.find('skipped') is None, 'skipped': c.find('skipped') is not None, 'failure': '' if bad is None else (bad.text or '')})
    result = {'label': label, 'command': command, 'exitCode': code, 'seconds': round(time.monotonic() - started, 4), 'tests': len(cases), 'passed': sum(c['passed'] for c in cases), 'cases': cases, 'output': output, 'outputSha256': digest(output.encode()), 'measured': True}
    (log_dir / (label + '.json')).write_text(json.dumps(result, indent=2))
    return result


def trim(base, head, work, paths, tests, logs, whole_paths=(), runner=None, on_check=None, cancelled=None):
    def check(work, tests, logs, label):
        if cancelled and cancelled():
            raise InterruptedError("Trim stopped")
        result = (runner or run_check)(work, tests, logs, label)
        if on_check:
            on_check(result)
        if cancelled and cancelled():
            raise InterruptedError("Trim stopped")
        return result
    shutil.copytree(base, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '.git', '.pytest_cache'))
    blocks = []
    for path in paths:
        a, b = base / path, head / path
        blocks.extend(blocks_for(path, a.read_text() if a.exists() else '', b.read_text() if b.exists() else '', path in whole_paths))
    active = {b.id for b in blocks}
    materialize(base, work, blocks, active)
    runs = [check(work, tests, logs, 'head')]
    if runs[0]['exitCode'] != 0 or not runs[0]['tests']:
        raise RuntimeError('Head oracle must pass nonempty tests: ' + str(logs) + '\n' + runs[0]['output'][:2000])
    # Greedy deletion to a fixed point. The final kept set is 1-minimal at this block granularity.
    removed = set()
    changed = True
    last_pass = []
    while changed:
        changed = False
        last_pass = []
        for block in blocks:
            if block.id not in active:
                continue
            selected = active - {block.id}
            materialize(base, work, blocks, selected)
            run = check(work, tests, logs, f'trial-{len(runs):03d}')
            run['removedBlock'] = block.id
            runs.append(run)
            last_pass.append(run)
            if run['exitCode'] == 0 and run['tests'] == runs[0]['tests'] and run['passed'] == run['tests']:
                active = selected
                removed.add(block.id)
                changed = True
    materialize(base, work, blocks, active)
    final = check(work, tests, logs, 'trimmed')
    runs.append(final)
    if final['exitCode'] or final['tests'] != runs[0]['tests']:
        raise RuntimeError('Final trimmed result changed the oracle')
    # The last pass made no deletions, so each failed trial used this exact final set.
    # Reuse those real runs as necessity controls; repeating them adds no new evidence.
    controls = last_pass
    if any(c['exitCode'] == 0 for c in controls):
        raise RuntimeError('Stable pass contains a removable kept block')
    materialize(base, work, blocks, active)
    patch = ''
    for path in paths:
        before = (base / path).read_text() if (base / path).exists() else ''
        after = (work / path).read_text() if (work / path).exists() else ''
        patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + path if (base / path).exists() else '/dev/null', tofile='b/' + path if (work / path).exists() else '/dev/null'))
    result = {'granularity': 'diff block; each count includes added and removed lines', 'written': sum(b.lines for b in blocks), 'kept': sum(b.lines for b in blocks if b.id in active), 'unchecked': sum(b.lines for b in blocks if b.id not in active), 'blocks': [{**dataclasses.asdict(b), 'lines': b.lines, 'needed': b.id in active} for b in blocks], 'runs': runs, 'controls': controls, 'final': final, 'patch': patch, 'patchSha256': digest(patch.encode())}
    return result
