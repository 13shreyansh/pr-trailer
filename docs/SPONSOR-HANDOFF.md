# Sponsor integration handoff

The feature branch adds real provider paths but production has not been changed. The previous Mac worker and tunnel remain running.

## What is ready

- `product/modal_runner.py` creates a fresh Modal sandbox for each fixed-test rerun. It uploads only the fetched public tree, blocks network, injects no secrets, runs as an unprivileged user against read-only source, bounds source size/runtime/result files and transport, and terminates the sandbox. Provider failure never silently reruns locally.
- `product/runlog.py` persists metadata-only test and acknowledged human review decision events through an idempotent Atlas outbox. It distinguishes the current event's actual delivery from other items in the batch. No source, stdout, reviewer notes or credentials enter Atlas.
- `product/provenance.py` invokes Entire Graph against the actual fetched PR-head tree. Local analysis snapshots disable hooks/global filters. Proof links reach `/api/context` with source lines pinned to the measured GitHub SHA; `/api/run-log` retrieves remote records.
- `Dockerfile.worker` prepares the trusted broker for a VPS canary. The broker alone receives the GitHub token. Sandboxes never receive it. The worker port and reset helper agree through `PORT`.

## Real-provider verification

Run `.venv312/bin/python scripts/product/verify_sponsors.py` in this worktree. Supply a JSON object through stdin from memory with `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` and optionally `MONGODB_URI`, `MONGODB_DATABASE`. Do not write a secrets file or paste values into a command line. The script reads the owned KASSA-CAP PR, runs actual tests through Modal and verifies Entire Graph and Atlas receipts. It does not merge, return or block a GitHub PR.

The root agent holds the Modal credentials in memory and owns provider UI provisioning. MongoDB Atlas login/provisioning is still pending. No credentials were recorded in this worktree. Entire Graph works without a hosted account or transcript export. No Entire Sessions capture is claimed.

## Canary deployment

Build a Docker context containing the committed `product/`, `scripts/`, `app/runtime/`, `app/evidence/manifest.json`, `app/requirements.txt`, `LICENSE`, `Dockerfile.worker`, the nonsecret `var/workspace.json` and a `release-commit` text file with the tested Git commit. The Dockerfile deliberately does not copy credentials or the local `.git` directory.

Suggested container port is 4326. Supply secrets using process memory and `docker run -e NAME`, never literal values or an env file. Set `TIETO_GITHUB_TOKEN`, `TIETO_TEST_RUNNER=modal`, `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `MONGODB_URI`, `MONGODB_DATABASE=pr_trailer`. `ENTIRE_BIN` is set by the image. Persist `/app/var/product` for state and the retry outbox.

A separately owned canary bank repo can be selected with `TIETO_WORKSPACE_REPO=tieto-nordbank-payments-sponsors`. Only that validated namespace is writable. To bootstrap it, use `scripts/product/workspace.py setup` with a fresh workspace config while the canary worker is available. Do not run setup/reset against the original live bank during acceptance. Keep the existing public Vercel route untouched until independent review and deployed wide/phone flows pass.

## Validation status

Measured locally: 58 Python checks and four Node suites pass. Sixteen new checks cover provider/security and cloud regressions. The first CRACI feature build succeeded at https://github.com/13shreyansh/pr-trailer/actions/runs/43685139962. New follow-up commits rerun CI. Separate real-provider, deployed browser and independent reviewer acceptance remain required before merge or release.

Draft PR: https://github.com/13shreyansh/pr-trailer/pull/14 . No Junction portal or submission description was touched.
