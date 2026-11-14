# Tieto design spec: The Measure (v2, real product, Sat 22:20)

v2 changes from v1: section 4 rewritten (no story mode; every beat is a real feature), start screen, PR-link field, no wall clock, real merges and pushes only on our own bank repo, acceptance 12 replaced. Everything else in v1 stands.

For Codex. DESIGN-FLOOR.md applies underneath. Numbers here are story targets; the build shows only numbers a real test run measured. Product name comes from config.

## 1. Direction contract

- **THESIS:** Every PR is a bar as long as the code the agent wrote. Trimming makes it shorter in front of you; what is left is what ships.
- **OWN-WORLD:** A workshop measure: one column of lengths on a clean bench, each cut to what the ask needs. Monday 09:00, office daylight, so light and calm.
- **STORY:** 10,214 lines written → Trim all → 96 need you → Finish ×19 → fee cap sent back trimmed → intern PR blocked → closing line.
- **FIRST VIEWPORT (hero frame, after Trim all):** counter sentence, key line, 23 bars in one column (solid stubs, one long part-hatched bar, one four-line block of hatching), one saffron Finish.
- **SIGNATURE:** the bar. Solid for "the ask needs this", hatched for "nothing checks this", to scale.
- **RISK:** reads as a chart. Counter: no axis or percentages; every bar has a title, a count and a state word; Enter acts on the current bar.

**Button meaning:** Finish merges the solid part only. A PR is "proven" when its solid part passes every test without the hatched part and has no risky lines.

## 2. Tokens

**Font:** Archivo variable, self-hosted: width 68 for the counter numeral, width 100 elsewhere, weights 400/500/600/700. JetBrains Mono 400, self-hosted, only in the risky-lines panel. `tabular-nums` everywhere; counter digits sit in fixed 0.56em slots.

**Type (px, fixed):** 12 caption (minimum) · 14 rows, labels · 16 ledger sentences, buttons · 20 counter words · 28 PR title · 40 closing line · 64 counter numeral (700). Code 13/22.

| Token | Hex | Job |
|---|---|---|
| ground | #FAFAF7 | page |
| panel | #FFFFFF | risky-lines panel only |
| aubergine | #3A1D4D | text, solid bar, lit lamps |
| aubergine-2 | #6B5578 | secondary text |
| rule | #E4E1E8 | 1 px rules |
| orchid | #B690D6 | hatch stripes only |
| orchid-deep | #7A4BA6 | hatch outline, hatched-block labels |
| orchid-wash | #F3ECF9 | current row, hover, selection |
| saffron | #F0A818 | the one button; the notch |
| saffron-deep | #B8790A | button border; pressed #D99310 |
| saffron-wash | #FDF1D2 | the marked bug line |
| block red | #C8281E | blocked PR only: breaks, barrier, failed lamps |
| red-wash | #FBEAE8 | blocked row |

Button text is aubergine on saffron. Saffron and orchid never carry text.

**Spacing:** 4, 8, 12, 16, 24, 32, 48. **Radii:** 2 bars, 6 buttons and panel. **Elevation:** none, except the panel `0 8px 24px rgba(58,29,77,.10)`. **Icons:** Lucide, 1.75 px, 16 px. Focus ring 2 px aubergine, 2 px offset.

**The bar, exactly.**
- **Solid:** aubergine fill. **Hatched:** no fill, 1 px orchid-deep outline, 45° orchid stripes 1.5 px wide every 6 px.
- Solid left, hatched right, 2 px gap. Ledger blocks are separated by 2 px gaps.
- **Notch (risky lines):** saffron slice 4 px wide, 3 px taller than the bar top and bottom, 1 px ground gap each side, at its true position on the solid part. One per PR in the inbox; one per risky hunk in the ledger.
- **Break (blocked PR):** 8 px gap crossed by a 2 px red diagonal.
- **Barrier:** 4 px red end-stop, 8 px taller than the bar, at its right end.

**Inbox scale (shared, linear).** Full track = 1,200 lines: 624 px on desktop (0.52 px per line), 358 px = 600 lines at 390. A longer PR wraps onto more lines of the same row: 4,800 lines is four full lines, 40 lines is 21 px. Minimum stub 6 px (under 12 lines). Bar 12 px high, wrapped lines 2 px apart.

**Ledger scale.** Full width (960 px) = that PR's lines written. Block minimum 6 px.

Both scales are printed on screen (section 6).

## 3. Screen anatomy

**Inbox, 1440 × 900** (content 1200, no scroll with 23 PRs):
1. Top bar, 44 px: as in section 4 (product name, workspace, PR-link field, "Synced", "Merging as").
2. Counter block, 124 px: counter sentence left, "Trim all" right on the same baseline, one sub-line.
3. Key line, 24 px: two 24 px sample bars with their phrases left; scale caption right.
4. Rows, 26 px, arrival order (intern PR last). Columns: title 300 · track 624 · count 112 · state 116; gaps 16.
5. Foot line: "19 merged · Revert last merge".

**Opened ledger, 1440 × 900** (content 960, never scrolls):
1. Top bar: "← Inbox · 4 left".
2. Title 28 px; under it agent, repository, time, "Check on GitHub".
3. The bar, 40 px, a label under each block, scale caption right.
4. Five lines, 44 px each, label column 120 px: Asked, Did, Extra, Read these, Proof.
5. Risky-lines panel opens under Read these and pushes Proof down.
6. Action bar, 72 px: one saffron primary right.

**390 px.** Inbox rows 48 px: title and count, then the bar; the list scrolls; numeral 44 px. Ledger is one screen, bar 32 px; Read these swaps the five lines for the panel with "Back to ledger". Primary fixed at the bottom, 56 px.

## 4. Real product, beat by beat (v2, Sat 22:20: replaces the story mode)

Everything below is a real working feature on the live site. There is no story mode, no fixture replay, no frozen clock and no auto-play. The video is recorded by someone actually using the site. Easing `cubic-bezier(0.16,1,0.3,1)`. Reduced motion: 150 ms opacity, counter jumps. No entrance animation.

**0. Start screen ("/").** Ground colour, a left-aligned 480 px column in the inbox's grid: product name 28 px 700, then a primary saffron button "Try the demo workspace (Nordbank payments)" (40 px), and under it a 14 px aubergine-2 link "Measure any public GitHub PR". No password fields.

**Top bar (every screen), 44 px:** product name left; workspace "Nordbank · payments" next to it in aubergine-2; right side: a 360 px inline field "Paste a GitHub PR link" (32 px, 1 px rule border, Enter submits), then 12 px aubergine-2 "Synced 09:12" (last fetch from GitHub), then "Merging as @{account}" (the real GitHub account the workspace writes with). No wall clock, no invented initials. Why: a real tool needs a way in for new work, and judges can paste their own PR.

**1. Inbox on arrival.** The workspace's open agent PRs come from a real repository we own (a Nordic-bank payments repo with its own fast test suite) plus 2–3 real AIDev PRs measured in their own repos. PRs not yet trimmed are hatched end to end with the state "Not trimmed". Counter: "{n} lines written by agents in {p} open PRs." Sub-line: "None trimmed yet." Rows show the PR number after the title in aubergine-2 ("#482"). Outside PRs (AIDev and ones added by link) sit below a 1 px rule labelled 12 px aubergine-2 "Outside this workspace", with "owner/repo #91" after the title.

**2. Wow 1: "Trim all" (T).** Really runs the trim on every unmeasured PR: removes each block, re-runs that PR's tests, classifies every line. Rows resolve as their real runs finish (needed part turns solid, clip-path from the left, 240 ms). Only rows actually running show stripes at 40 % with "Trimming…"; waiting rows say "Queued". The sub-line shows real progress, "Trimming 7 of 23 · 212 tests run", and "Trim all" becomes a quiet text button "Stop". When the run starts, the counter words become "lines still to check." and the numeral counts down as real results land; at the end the words swap to "lines need you." (opacity, 150 ms). When every run is done, the proven rows' hatched ends leave together (translateX 32 px, opacity 0, 480 ms), the Trim-all slot becomes quiet 14 px text "Trimmed 09:12 · Run again", and the only saffron button is Finish on the current proven row, with its hint always visible beside it: "Merges 212 of 1,140 lines into main". If a full live run takes longer than 20 s, the video speeds it up in editing; the product never fakes it. Finish ×19 behaves as in v1: Enter folds each proven row into a tick and really merges the solid part into the bank repo (our own repo). On AIDev PRs from other people's repos, Finish is replaced by "Download trimmed patch" and nothing is pushed there.

**3. Wow 2: open "Cap instant-transfer fees" (O).** Its bar grows into the ledger bar (transform, 360 ms). The first time a PR's ledger opens, its extra blocks lift out one by one as their recorded test results show (translateY −20 px, opacity 0, 320 ms, 500 ms apart), the lamps show the real per-test results, and the gap closes (width, 400 ms). "Re-run tests" (a quiet text button in the Proof line) runs them again live. N or the notch opens the risky-lines panel. "Send back trimmed" (S) really pushes a trimmed branch to the bank repo and opens a new PR there with the editable note as its description; the inbox row closes and the numeral drops.

**4. Wow 3: the intern PR.** A real PR in the bank repo by a first-week junior's agent (the UI never says "intern"), opened from a ticket that says "Make our company the best in the world. Make no mistakes.", touching login, pricing and a database migration. Its ledger shows the real failing checks (three breaks, three red lamps). "Block and ask what they meant" (B) really posts the message on that PR in our bank repo and marks it blocked.

**5. Add a PR.** Pasting a link into the top-bar field and pressing Enter fetches the PR and adds its row under "Outside this workspace", hatched and "Trimming…" while it runs in our sandbox. Errors inline under the field, 12 px: "Not a public PR link." If the repo's tests can't run here, the row says "Can't run this repo's tests here" and only shows lines written. Why: judges can try their own PR, which proves nothing is staged.

**Close.** The closing line is not a screen in the product. It goes on the video's last frame in editing.

## 5. Components

**PR bar row.** Title 14 px 500, one line. Count "1,140", then "212 of 1,140" after trim. State: saffron Finish (24 px) on the current proven row only; otherwise "Proven", "Needs you · 6", or red "Blocked". Current row on orchid-wash. Click opens; O opens the first row that needs you. Loading: stripes at 40 % opacity, "Trimming…". Error: "Couldn't run tests · Retry". Empty: "Nothing to sign. New agent PRs appear here."

**Counter.** One sentence: numeral 64 px, words 20 px, same baseline. Always the sum of Read-these lines in PRs still in the inbox.

**Opened ledger.** Each line: 14 px 600 label, one 16 px sentence, numbers 600, at most two lines.

**Named blocks.** Label under each: name · line count. Under 60 px wide, the label hangs on a leader line. Extra-line chips are 20 px hatched bars with the same label; clicking one shows it back in the bar and changes nothing.

**Test lamps.** 8 px circles, 4 px apart, in Proof. Lit: aubergine. Running: orchid-deep outline, pulsing. Failed: red ring with a diagonal. One per test up to 48, then one per test file, and the sentence says so.

**Risky-lines panel.** White, JetBrains Mono 13/22, aubergine only. Path and line numbers aubergine-2. Up to 8 lines, then pages ("1–8 of 22"). A marked line sits on saffron-wash with a one-sentence Archivo note under it.

**Finish.** 40 px, saffron, aubergine 16 px 600, 1 px saffron-deep border; hover 2 px border; disabled rule fill; busy "Finishing…"; failed "Couldn't merge. Check on GitHub, then try again." Enter is Finish wherever Finish shows and does nothing elsewhere.

**Send back trimmed.** Same button. Above it, the one-sentence note to the agent, editable in place.

**Blocked state.** Red-striped bar with barrier, row on red-wash, "Blocked", the sent message and "Undo block".

## 6. Copy

- Counter: "{n} lines written by agents since yesterday." → "{n} lines need you." Sub-line: "{p} PRs. None checked yet." → "{a} of {p} proven. {b} need you."
- Key line: "Needed: a test breaks without it" · "Unchecked: every test passes without it".
- Key hints: 12 px aubergine-2 beside each button ("Trim all  T", "Finish  Enter"). In the video, the first use of each action is a visible mouse click.
- Scale: "Full width is {1,200} lines. Longer PRs wrap. Under {12} lines is drawn at 6 px." Ledger: "Full width is the {n} lines this PR wrote."
- Buttons: "Trim all" · "Finish" · "Send back trimmed" · "Block and ask what they meant".
- Finish hint: "Merges {kept} of {written} lines."
- Asked: the ticket text in quotes.
- Did: "Did it in {n} lines. {t} tests break without them."
- Extra: "{n} lines nothing checks: {block}, {block}. All {t} tests pass without them." / "Nothing extra."
- Read these: "{n} lines to read. {m} looks wrong." / "Nothing risky."
- Proof: "{p} of {t} tests pass on the trimmed PR."
- Bug note: "Rounds half a cent down, so a fee can pass the cap by 1 cent."
- Sent back: "Kept the cap. Removed the retry rewrite and currency cache; nothing tested them. Fix the rounding on line {n}."
- Blocked: Asked adds "This can't be checked. No test can tell when it's done." Extra: "Nothing is provably needed." Read these: "3 changes break production.", one line each ("Drops a column that payments reads."). Sent: "Asked the author: what should this change? Name one thing we can test."
- Close (video end frame only): "Every line earns its place, or it doesn't ship."

## 7. Don't

1. No red and green for the two line groups; no diff view.
2. No dark theme, glow, gradient or blur.
3. No axis, gridlines, percentages or legend box.
4. No logarithmic or per-row scale in the inbox.
5. No filled orchid.
6. No red on a PR that is not blocked.
7. No second saffron button on a screen.
8. No cards, stat tiles, rings, trend lines or pill badges.
9. No monospace outside the panel; no syntax colours in it.
10. No scrolling ledger, modal, tabs or file tree.
11. No unmeasured number; hide a line that has no data.
12. No "AI", "confidence", "score" or "insight"; no chat bubbles, sparkles or thinking dots.
13. No kicker above a heading; no section numbers.
14. No row reordering, bounce, confetti or load choreography.
15. No avatars or logos.
16. No text under 12 px.

## 8. Acceptance checks (screenshots)

1. 1440 × 900 cold open: 23 rows, all hatched, intern bar on four lines, "Trim all" the only saffron, no scroll.
2. After trim: 19 solid stubs, 4 rows with hatching, exactly one saffron Finish, both key phrases and the scale caption visible.
3. Any single-line bar's width ÷ its line count = 0.52 px (±1 px), or 6 px under 12 lines.
4. After Finish ×19: four rows and "19 merged · Revert last merge".
5. Fee-cap ledger: block counts sum to the PR total; after the replay one solid block a fifth wide, two chips in Extra, all lamps lit.
6. Panel open: six mono lines, one on saffron-wash with its note; Proof and the primary visible without scrolling.
7. Intern ledger: no solid part, three breaks, three red lamps; after Block, a red bar with barrier and the sent message.
8. Red appears only on the intern PR.
9. 390 px: no horizontal scroll, primary fixed at the bottom, caption reads "600 lines".
10. Text contrast at least 4.5:1; hatch outline at least 3:1.
11. Only Archivo and JetBrains Mono load; counts align in their column.
12. A Playwright headless test on the DEPLOYED URL does the whole flow as a user at 1440 × 900 and 390 px: demo workspace → Trim all (real runs) → Finish on every proven PR → open the fee-cap PR → panel → Send back trimmed (a new trimmed PR exists in the bank repo) → open the intern PR → Block (the message exists on that PR) → Add a PR with a public PR link. Screenshots saved in artifacts/e2e/, no console errors.
13. No `?story` parameter, fixture replay, frozen clock or auto-play exists anywhere in the code.
14. A reset script restores the demo workspace (reopens the PRs, removes the trimmed PRs and messages) so the flow can be recorded again.
