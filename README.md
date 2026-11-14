# Tieto: every line earns its place

Live: https://pr-trailer.vercel.app

A code-review rehearsal for the accountable human. Remove a change block, re-run a fixed test oracle, and keep deleting until no remaining block can be removed on its own without failing a check. The result is block-minimal for those tests. Unchecked blocks may be extra **or untested**.

The inbox contains 19 small synthetic bank changes, a fee-cap change with a real half-cent rounding failure, two public Codex PRs from AIDev, and an intentionally vague intern change with three independently reproduced bank regressions. Counts come from recorded execution, not the illustrative design totals. Counts include added and removed implementation lines; oracle tests are held fixed and excluded.

Normal **Trim all** runs the engine on packaged source snapshots in Python functions. Each response must match the recorded patch hash, test counts, failing removal controls and special regression checks. **Finish** applies the selected proven bank patches to a real Git branch, tests the combined branch, and returns a downloadable Git repository. **Send back trimmed** prepares a minimal patch and an editable follow-up draft. This app sends no messages, comments or merges to real GitHub repositories.

## Run and verify

Requires Python 3.12 and Node 24. Install Python dependencies from `app/requirements.txt` into `.venv312`.

```sh
npm ci
npm test
.venv312/bin/python -m unittest discover -s tests -v
node app/dev.js
```

The dev server is http://localhost:4321. Python runtime code is `app/runtime/`; fixed source packages are in `app/runtime/sources/`. Test logs and complete compressed archives are under `app/evidence/`. Read `fullLogArchive` in a summary JSON for the full log download. Live reruns include a gzip archive encoded in their JSON response.

To rebuild all measured evidence:

```sh
.venv312/bin/python scripts/measure/fetch_real.py
.venv312/bin/python scripts/measure/record.py bank
.venv312/bin/python scripts/measure/record.py 9
.venv312/bin/python scripts/measure/record.py 24
.venv312/bin/python scripts/measure/record.py assemble
.venv312/bin/python scripts/measure/package_runtime.py
.venv312/bin/python scripts/measure/compact_reports.py
```

`evidence/source/reduino-*/provenance.json` pins the AIDev row, original PR, base SHA and head SHA. Source tarballs are included for rechecking. Both PRs are in Jackhammer9/Reduino: [serial monitor #9](https://github.com/Jackhammer9/Reduino/pull/9) and [servo support #24](https://github.com/Jackhammer9/Reduino/pull/24). Their published head test suites are the oracles. Physical Arduino hardware was not tested.

## Recording

- `?story=1`: fixed fixture, no check requests, clock frozen. Space advances; 1–5 jump; R restarts. T trims, Enter finishes, O opens the next change needing a person, N opens risky lines, S prepares the trimmed return, B blocks the intern.
- `?story=auto`: timed playback with the final frame after 110 seconds.
- Story controls are hidden during playback. Archivo and JetBrains Mono are self-hosted.

## Limits and provenance

Removing a block can fail through imports or collection, not only through behaviour. The UI calls these failing checks. Passing fixed tests cannot establish that the ask is complete, that unchecked code is unnecessary, or that production is safe. The named approver still owns the residual risk. Host-side hardware checks remain explicit human tasks.

The bank is synthetic, with no customer data. Public Reduino sources retain their upstream GPL-3.0-or-later license inside source archives. AIDev attribution: Hao Li and collaborators, [AIDev dataset](https://huggingface.co/datasets/hao-li/AIDev), CC BY 4.0. Font license files are in `app/fonts/`. Original PRs are read-only throughout this project.

Review evidence: [docs/MEASURE-REVIEW.md](docs/MEASURE-REVIEW.md). DOM tests are not substitutes for the required deployed browser screenshots and console checks.
