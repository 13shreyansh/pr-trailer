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
