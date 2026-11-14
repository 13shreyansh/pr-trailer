# Tieto decisions (newest last)
- 21:06 Old UI rejected: too many sections, no flow, 290->66 too small. Supersedes the v2 per-PR format router and section pile.
- 21:10 Home = one review inbox; one short ledger per PR; Finish / Send back trimmed.
- 21:15 Spine = only what was asked, proven by trimming + re-running tests; two groups: needed / nothing checks it.
- 21:18 Story: Monday 09:00 Nordic bank, ~10k lines -> ~100 need you; fee-cap PR trimmed; intern PR blocked. Intern PR is synthetic (no need to run an agent on that prompt).
- 21:35 UI = Option B "The Measure" (DESIGN-DIRECTION.md). Inbox scale linear at 1,200 lines per full width, longer PRs wrap (stated on screen).
- 21:35 Finish merges the trimmed PR (solid part). Hatched "nothing checks this" parts are not silently dropped: they go back to the agent as one follow-up ("add a test or a reason, or it stays out"), shown in the ledger.
- 21:46 No scripted "Play the story" mode (supersedes that part of DESIGN-DIRECTION.md). Real product: a clean start screen with a small "Try the demo account" that opens a normal engineering inbox. Everything in the video happens by real clicks; trims shown come from real recorded test runs, and Finish / Send back trimmed really act.
- Build: measured totals replace the illustrative story counts. Candidate line counts are actual added plus removed implementation lines; published head tests are fixed oracles and are excluded.
- Build: removal trials produce a block-minimal passing candidate, not a mathematical proof of specification completeness. Import/collection failures count as failing checks, not behavioural proof.
- Build: the real half-cent counterexample is 200.5 cents rounded to 200 instead of policy-required 201. The hard €5 ceiling still holds; the earlier suggested over-cap explanation was incorrect.
- Build: Finish builds and tests a downloadable Git branch in the synthetic bank. Send back prepares a real minimal patch and a draft note. No GitHub merge, comment or message is sent.
- Build: normal Trim all executes allowlisted source snapshots. Story mode uses the recorded fixture and makes no check API calls.
- Sat 22:43: job 02 running as NEW session 01a1dbcb-fbee-76b2-9484-96cc316b4dea (resume of job01 failed: active writer).

- Job 03 (Sat 23:33): sole owner reconciles all inherited work. Active implementation is `product/` with `app/app.js`; the alternate implementation is archived under ignored `var/alternate-v2/`.
- Job 03: keep the 21 managed PRs in `13shreyansh/tieto-nordbank-payments` (initial #1-21), with real fetched GitHub sources and tests. Close both duplicate sets in `13shreyansh/nordbank-payments` (#1-42), each with a short redirect comment; exact receipts are in `evidence/reconciliation-job03.json`.
- Job 03 supersedes the older Build entries about export-only Finish, draft-only comments, and recorded UI modes. Finish now tests the minimal candidate on current main, pushes it to the owned request branch and merges that real PR. Return opens a real trimmed PR. Block posts a real question on the owned PR. Public repositories are read-only and compatible Python tests run in an OS sandbox.
- Job 03: the retained bank cap PR has a measured cap-guard defect: 500.5 cents rounds down for the guard, then rounds up to 501 for the returned fee. A separate held-out test fails while the request suite passes. The older job01 rounding evidence is retained as historical evidence, not replayed in the active product.
- Job 03 spec reconciliation: desktop columns total exactly 1,200 px including gaps (300 + 624 + 112 + 116 + 48). The earlier 1,300 px note was incorrect. Mobile top-bar content uses two rows to fit the PR field and real account.
