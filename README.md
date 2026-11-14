# PR Trailer: earned trust for AI-written pull requests

Junction 2026 · Tieto challenge "Earned Trust in AI Code" · team The CS Guy · MIT

Every agent-written PR ships with a **trailer**: evidence per requirement ID (test runs, a captioned UI video, a sequence diagram), what the AI checked, **what it refused to decide and why**, a merge-danger note (one-way vs two-way door, blast radius), and a sign-off card for a named human. The AI never approves. Only reproduced problems can block.

- Concept card: [docs/CONCEPT.md](docs/CONCEPT.md)
- Measured results: [docs/RESULTS.md](docs/RESULTS.md)
- Lessons log and decisions: [docs/LESSONS.md](docs/LESSONS.md)

## Run it

Needs Python 3.11+, plus Node with Playwright for the UI evidence. There are no Python dependencies.

```bash
python3 -m trailer PR-109                # one trailer -> out/PR-109/trailer.md + trailer.json
python3 -m trailer --no-ui               # all 13 sample PRs, backend evidence only
python3 -m bench.run && python3 -m bench.report   # full measurement: samples + 49 mutants -> docs/RESULTS.md
python3 site/build.py                     # static walkthrough page -> site/index.html
GEMINI_API_KEY=... python3 -m trailer --llm gemini --llm-replay out/llm   # optional advisory LLM reviewer
python3 -m unittest tests.test_trailer
```

## Layout

| Path | What |
|---|---|
| `bank/` | **Kassa**, a synthetic retail-banking service: transfers, fees, daily limits, idempotency, audit log, statement export, transfer form |
| `bank/requirements.json` | 13 requirements with acceptance criteria |
| `bank/tests/spec/` | Acceptance tests, one per criterion (`REQ_PAY_210.test_ac2_*`) |
| `bank/invariants.py` | Team-owned money invariants run on every PR |
| `bank/CODEOWNERS` | Who signs for what |
| `prs/PR-1xx/` | 13 agent-written PRs, 8 with planted bugs |
| `bench/ground_truth.json` | The planted bugs (never read by the trailer) |
| `trailer/` | The generator: diff, test runs with per-test coverage, rules, probes, differential testing, merge danger, routing, sign-off |
| `bench/` | Measurement: catch rate, false alarms, lanes, minutes, trust ledger, mutants |
| `scripts/ui_spec.js` | UI acceptance tests and the captioned video recorder (Playwright) |

## Checks and how each one is verified

| Rule | Catches | Verified by |
|---|---|---|
| T-REGRESSION / T-CLAIM-UNMET | A criterion broken, or claimed but not met | Acceptance tests on main vs PR (Python and Chromium) |
| I-INVARIANT | Team money invariants broken | Executing the invariants on the PR head |
| M-FLOAT | Money passing through float | Invariant counterexample (`to_cents('19985.01')`) |
| P-PII-LOG | Full IBAN written to logs | Log capture during the test run |
| S-AUTHZ | Handler reads `account_id` without an ownership check | Runtime probe: user B reads user A's account |
| D-DANGLING | Dropped column still read | Static reference plus the export test |
| B-DIFFERENTIAL | "No behaviour change" that changes behaviour | 4000 inputs, main vs PR, with a counterexample |
| D-SCOPE, D-DESTRUCTIVE, B-STATEFUL, B-TOPLEVEL, S-POLICY, S-NEW-SURFACE, T-NO-ORACLE | Things the AI **refuses** to decide | Each becomes a question with a named owner |
