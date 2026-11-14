# Job 02 independent review

Reviewer: separate 6 Astra agent. Scope: active product source, design v2, independently executed quality checks, then deployed browser evidence when the owner signals readiness. No GitHub mutations or resets were run by this reviewer.

## Pass 1: spec and source

The active implementation has the v2 entry, owned workspace, outside-PR boundary, live queue, sandboxed test runner, real merge/return/block functions, and measured result files. The GitHub broker rejects writes outside `13shreyansh/tieto-nordbank-payments`. Test subprocesses receive a restricted environment and Seatbelt denies broker-file access and network access. The isolated-run regression passed during this review.

Three reproducible defects require fixes before acceptance:

1. **P1, Stop never settles a queued batch.** `product/service.py:measure` returns before the `finally` block when STOP is already set. A mocked queued job left its batch at `running=True`, `completed=0`, `total=1`. Remaining queued jobs therefore prevent the UI from leaving its active-run state.
2. **P1, Enter can merge from the start screen.** `app/app.js` handles Enter by selecting the first proven row without checking the active view. A JSDOM reproduction loaded a proven row, clicked Tieto to return home, then sent Enter on the body. It requested `/api/finish` even though no Finish button was visible. This violates the explicit keyboard contract.
3. **P2, editable return note is lost.** `app/app.js:render` retains editor text only while the editor has focus. A JSDOM reproduction edited the note, focused the risky-lines button, and opened the panel. The note reverted to its original value. Polling after blur has the same cause.

The owner accepted these findings and is adding permanent regressions and fixes. This reviewer edits only this document.

Two smaller source-level mismatches were also reported. Outside-PR `riskPosition` is the constant `.3`, while the design requires a notch at the actual changed line. The general outside-PR risk note mentions hardware even for unrelated public Python repositories. Position should come from the measured changed block, and hardware wording should remain specific to Reduino.

The archived alternate implementation was not treated as active source. The current source does not autoplay the workflow. The ledger's recorded-result animation follows the explicit v2 interaction.

## Pass 2: independent build checks

Measured on the active source before the three fixes:

- `.venv312/bin/python -m unittest discover -s tests -v`: 25 tests passed, 6.943 seconds.
- `npm test`: both suites passed. These cover review helpers and the clean entry DOM, not the complete live workflow.
- `node --check app/app.js`, `node --check app/review.js`, `node --check app/api/bridge.js`: passed.

These passing commands did not cover the three findings above. Each was separately reproduced without live writes.

## Deployed acceptance

Pending the owner's readiness signal. This reviewer has not yet independently inspected deployed screenshots or run deployed read-only browser assertions. Full mutation flow and reset remain the owner's responsibility. `playwright.config.js` names `scripts/e2e.spec.js`; that test file was not present at the initial review checkpoint.

Verdict: changes required. Local tests pass; the three reproduced defects and deployed spec/taste acceptance remain open at this checkpoint.

## Job 03 source checkpoint

Separate gpt-6-astra independently reran the current quality commands on `d5c46b8`: measured 40 Python tests passed in 6.656 seconds; all four Node suites and JavaScript syntax checks passed. It reviewed the bounded GitHub 405/409 retry, rejection of foreign branch updates, revalidation of pending candidates on changed main, and use of the merge's actual first parent for Revert. No source blocker remains at that checkpoint.

The reviewer has also inspected deployed desktop start, cold inbox, active queue, trimmed inbox and outside-PR ledger screenshots. Remaining fee/junior/mobile screenshots, full action receipts and final production commit verification are pending.
