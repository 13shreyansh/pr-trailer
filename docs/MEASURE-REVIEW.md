# The Measure: independent review

Reviewer: separate GPT-6 Astra agent. Scope: this entry only; source, recorded artifacts and independently rerun local quality commands. No real GitHub merge, comment or message was performed.

## Pass 1: specification fit

The implementation has the requested measured inbox and removal-test spine: 19 synthetic clean bank PRs, the fee-cap case, two pinned public AIDev/Codex PRs, and the intern case. The real samples are Jackhammer9/Reduino PRs 9 and 24. Their published head tests are held fixed outside the candidate delta. This is evidence relative to that oracle, not a complete specification or physical-device validation.

Final recorded totals are **5,741 changed lines**, **25 selected review lines/checks**, **19 proven PRs**, **23 PRs**. These values were read from the rebuilt manifest and reconciled with its cases. The selected review surface is curated; it is not a demonstrated general risk detector.

The final fee cap measures 37 changed lines, with 7 retained; its ask suite passes 6/6 and its held-out rounding check fails 0/1 with 200 rather than 201 cents. The ceiling still holds. The baseline now uses half-up rounding: an independently rerun regression confirms the baseline passes and the PR introduces the half-down failure. The marked-line position is computed from the changed-line rank and covered by a regression. The intern measures 3,830 changed lines, no retained portion, three independently failing checks and 0/3 combined. Independent fresh runtime reruns matched the intern counts; the final cap evidence and baseline regression passed the final suite.

Finish now builds a real local synthetic-bank Git branch and exports it. External PRs stay untouched. Send-back prepares a patch and note for download; it does not send a message. Story mode was assessed against the current job.

## Pass 2: independently rerun build quality

- Final frozen-code `.venv312/bin/python -m unittest discover -s tests -v`: **20/20 passed**, measured runtime **6.375 s**. The recorded-count test verifies every non-intern row's elapsed metadata against its unique recorded runs; the new intern regression verifies each shown source line and its file location.
- Final `npm test`: state transitions, exact patch/control/held-out response validation and JSDOM interaction checks at configured widths of 1440 and 390 passed. JSDOM checks covered cold inbox, trim, 19 finishes, cap panel, intern/block, story reset, Finish export, Undo invalidation and the persistent pending-Finish/Undo race regression. They do not establish real-browser layout or deployed behavior.
- `node --check` on `app/app.js`, `app/review.js`, and `app/dev.js`: passed.
- Independent fresh runtime AIDev 9 before the control-reuse optimization: **202 → 179 changed lines**, **67/67 tests**, **9 failing removal controls**, exact recorded patch SHA match; measured local elapsed **15.28 s**. This timing is historical, not the final optimized runtime.
- Independent fresh runtime AIDev 24 before the control-reuse optimization: **627 → 566 changed lines**, **85/85 tests**, **36 failing removal controls**, exact recorded patch SHA match; measured local elapsed **57.81 s**. This timing is historical, not the final optimized runtime.
- Fresh all-19 Finish export: extracted the ZIP, then independently used system Git to verify `tieto/approved`, HEAD equal to the returned receipt, **20 commits** including baseline, and a clean worktree. No unchecked config JSON was present. The exported repo's selected ask tests plus safety tests independently passed **48/48**. Combined export/check elapsed was measured at **1.02 s**.
- Primary-agent production verification is now recorded in `evidence/live-verification.json`: **23/23 API cases** matched expected results and the exported bank passed **48/48**, with Git HEAD checked by the primary agent. This reviewer independently reconciled that receipt against the final manifest for all IDs, changed/retained counts, pass/test totals, patch hashes and control counts. Recorded measured production durations were **63.751 s** for AIDev 9 and **135.573 s** for AIDev 24, within the configured 300-second limit. The reviewer did not repeat those live requests. The final presentation-only deployment is reported to retain the audited backend files and configuration unchanged.

Needed controls include test collection/import failures as well as assertion failures. The interface now accurately calls them failing checks. Removal is 1-minimal at the chosen block granularity, not globally minimal at arbitrary line granularity.

## Findings handled during review

- Intern recording reused a mutated worktree for its baseline: corrected by restoring the baseline before each cycle and covered by a two-cycle regression.
- Whole-file trial groups counted unchanged context as changed lines: corrected while preserving whole-file trial granularity and covered by a counting regression.
- Live rerun matching initially used totals only: now checks exact patch identity, failing controls, head/final success, cap held-out failure and independently failing intern checks.
- Finish initially only hid a row and logged a sign-off despite claiming a branch merge: replaced with a tested local Git branch export.
- Notches initially used a constant 55% position: source now uses selected source positions. Pixel positioning remains visually unverified.
- Undo initially retained a stale branch artifact and could race an in-flight Finish: corrected by clearing the artifact when undoing a Finish and refusing Undo during Finish. An independent Node VM execution of the actual app click handler verified both cases; the Node state/verifier suite and app syntax check were then rerun successfully. This is source-level handler evidence, not browser acceptance.
- The parent agent reported that the first deployed trim request failed because subprocesses lost the serverless parent's vendored dependency import paths. Inspected the correction in both identical engine copies: the child `PYTHONPATH` now includes the candidate source paths followed by parent `sys.path`; the existing environment allowlist remains in place. Independently reran the new vendored-import regression alone (**1/1 passed**, measured **0.199 s**) and in the final full suite. The regression exercises a dependency supplied only through a parent-added import path. The later primary-agent production audit confirms API recovery.
- The parent subsequently reported AIDev 24 exceeding the deployed 120-second function limit. The engine now reuses the real failing trials from its last no-deletion pass as necessity controls, and the configured limit is 300 seconds. Source inspection confirms every such trial removes one retained block from the identical final active set; the fixed-point loop is retained. A regression proves an earlier block is revisited after a later removal. An additional independent case confirmed reused controls are the actual final-pass run objects, cover each retained block exactly and fail. This removes duplicate work without weakening the recorded necessity condition. The later primary-agent production audit records AIDev 24 completing in 135.573 seconds.
- Control reuse initially exposed double-counting in elapsed metadata. The source now sums runs once, assembly refreshes every non-intern row, and the final recorded-count regression confirms that all those rows match their recorded runs. The stale bank metadata finding is resolved. These elapsed values are not displayed in the interface.
- Both self-hosted fonts are preloaded and explicitly awaited before story initialization. This was inspected in the frozen source; actual font rendering remains unverified without the real browser.
- Each intern risk panel now shows the actual changed source line, selected from the base/head diff. Source inspection and the permanent regression confirm all three file locations and lines. Blocking centrally closes the open panel; the DOM flow now opens an intern risk panel, blocks, and asserts that the risk-open state clears and the barrier exists. Real mobile rendering remains unverified.

## Remaining acceptance limits

**Real-browser acceptance remains unverified.** The in-app browser host was unavailable, including the primary agent's final retry; no external-browser fallback was used. API recovery and production timing have primary-agent evidence as described above. This reviewer has not inspected 1440×900 or 390 px screenshots, run the deployed whole-video flow, or confirmed no-scroll/contrast/motion acceptance. Source, JSDOM, local runtime and production API checks cannot substitute for those visual interaction requirements.

Verdict: **local review passes with 20/20 tests and npm/DOM checks; primary production evidence verifies 23/23 API cases and the 48/48 exported branch. Deployed desktop/mobile real-browser acceptance remains blocked by browser-host availability.**
