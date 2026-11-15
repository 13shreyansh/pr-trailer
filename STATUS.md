UI REBUILD / Sun 15 Nov 2026 02:40 UTC (04:40 Helsinki) / https://pr-trailer.vercel.app / served build a4f5fd2 (Vercel deployment dpl_HEczMGmL9B8XPXhPg6Eqk84m9B65; build.json, 7 static files and worker /health all match that commit; later commits touch only STATUS, screenshots and scripts)

WHAT CHANGED:

- "/" is now a long static landing page (problem, how it works on the real fee-cap PR, proof from the 14 Nov recorded runs with GitHub links, limits, one entry "Open the demo workspace"). No script, no worker call.
- "/workspace" paints a skeleton from static HTML, renders the inbox from the worker's in-memory state (POST /api/enter), then syncs with GitHub in the background. Returning visitors paint from a localStorage snapshot; if the worker is unreachable it shows a baked start-state snapshot with actions paused.
- Visitor sessions (product/visitors.py): a new visitor gets the true start state unless someone else polled in the last 90 s; a used workspace nobody polls for 10 min restores itself; account menu has "Reset workspace" (asks first) and "Sign out", both real.
- Rows and ledgers show real provenance: PR number linked to GitHub, age, author, branch, head commit, repository line. Untrimmed ledgers draw their bar. Mobile rows no longer overlay the state on the bar.
- The junior PR is retitled "Improve login, pricing and statement storage" on GitHub (#21, own repo, title only), in var/workspace.json and app/evidence/manifest.json. Its ticket text is unchanged.
- Static files now come from the Vercel deployment (the daily cap had reset); project routes forward only /api to the worker. Fonts are also served as woff2 (189 KB instead of 659 KB).

SPEED (measured, headless Playwright Chromium on this Mac against the deployed URL, cold context per run, median of 5; FCP is the browser's first-contentful-paint entry):

| | before (1 run, 1440) | after 1440 | after 390 |
|---|---|---|---|
| Landing FCP | 312 ms | 116 ms | 112 ms |
| Workspace first paint | 6,120 ms (blank until then) | 104 ms (skeleton) | 112 ms |
| Workspace first real PR rows | 6,394 ms | 254 ms | 258 ms |
| Worker calls made by the landing page | 1 | 0 | 0 |

Reset: a session that only trimmed restores in about 10 s (measured 9 to 10 s); after merges, a full GitHub restore took 55 s and 57 s (measured in the two E2E runs). Numbers are from the same machine that hosts the worker; a remote visitor adds their own network latency to the /api/enter round trip.

TESTS (all measured): 42/42 Python; 4/4 Node suites; deployed Playwright E2E 2/2 (390 and 1440x900, 12.8 min, 0 console errors): landing, open workspace, Trim all, Stop, Trim all, 19 real merges, public patch download, fee-cap ledger and panel, Send back trimmed, Block, add Reduino #26 by link, GitHub verification, Reset workspace from the menu, Sign out. Separate deployed check: a second visitor arriving 95 s after a first visitor left the workspace trimmed got the start state in 10 s.

SCREENSHOTS: screenshots/fable/ (1440-* and 390-*: 00-landing, 00-landing-full, 01-inbox … 12-reset), before/ for the old site, CRITIQUE.md, perf-after.json.

SPEC GAPS I FILLED / DEVIATIONS: inbox rows are two lines (44 px desktop, 64 px mobile) to carry provenance, so the 23-row inbox scrolls at 1440x900; start screen replaced by the landing page and its entry is a link; top bar shows the repository and an account menu instead of "Merging as"; tests updated to match (test_dom.js, client-regressions.js, e2e.spec.js, and the no-network test now checks for cross-origin loads instead of any https link).

FRAGILE: everything under /workspace still depends on the worker and Cloudflare quick tunnel on this Mac (launchd xyz.thecsguy.tieto-worker and tieto-awake). With the Mac off, the landing page works fully; the workspace shows the baked snapshot with actions paused. A worker restart changes the tunnel address and republishes the /api route automatically.

---- previous status (job 03) below ----

Tieto / 2026-11-15 00:41 EET / 4081abc served; Vercel base 7ad09d9 / https://pr-trailer.vercel.app

DONE:

- Published the v2 product with real trim, merge, trimmed return, block and public-PR measurement. No story mode.
- Verified both deployed viewport flows and extra Undo/Revert controls; preserved the real run evidence.
- Reconciled duplicate PRs and reset the workspace twice consecutively. It is ready for recording.

NUMBERS: dev measured: 42/42 Python tests, 4/4 Node suites, 2/2 deployed flows, zero browser errors; scope measured: 5,741 implementation lines to 25 selected review lines; held-out measured: rounding defect reproduced, 0/1 passing; baseline measured: 3/3 safety checks, accepted bank 48/48.

SCREENSHOTS: [Desktop first screen](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-01-inbox.png) · [390 px first screen](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/390-01-inbox.png) · [Risk panel](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-06-risk.png). [All screens and evidence](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/index.html).

REVIEW: Separate gpt-6-astra PASS on spec fit and build quality. Merge races, state recovery, mobile type and proof-label findings are fixed.

TASTE GATE:

| Item | Result | Screenshot |
|---|---|---|
| 1. Professional product | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-01-inbox.png) |
| 2. Real working features | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-06-risk.png) |
| 3. Clean start | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-00-start.png) |
| 4. Working controls | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-08-blocked.png) |
| 5. Measured numbers | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-05-fee-ledger.png) |
| 6. Spec layout and type | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/390-05-fee-ledger.png) |
| 7. Prescribed primary action | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-03-trimmed.png) |
| 8. Plain domain copy | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-07-junior.png) |
| 9. Clear next action | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-00-start.png) |
| 10. Calm density | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-01-inbox.png) |
| 11. No default decoration | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-04-merged.png) |
| 12. Themed and unclipped | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/390-06-risk.png) |
| 13. Full deployed flow | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-09-public.png) |
| 14. Visible proof moments | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-06-risk.png) |
| 15. Smooth, honest progress | Yes | [View](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/artifacts/e2e/1440-02-queue.png) |

Spec gaps I filled:

- The mobile header uses two rows; its long start label wraps at the prescribed type size. Ledger spacing preserves visible Proof and actions.
- Reset creates fresh PRs for already-merged cases and closes generated trimmed PRs.
- Publication uses managed routes after the deployment cap. Served files and worker match the committed source; the supervised worker/tunnel must remain running.

NEXT: Record the real flow in [DEMO_SCRIPT.md](/Users/shreyansh/Documents/ChatGPT/Junction/tieto/DEMO_SCRIPT.md).

NEEDS DECISION: none

BLOCKED: none
