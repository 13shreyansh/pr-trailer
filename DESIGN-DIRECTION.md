# Tieto design spec: The Measure

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
1. Top bar, 44 px: product name; "Mon 16 Nov · 09:00"; reviewer initials.
2. Counter block, 124 px: counter sentence left, "Trim all" right on the same baseline, one sub-line.
3. Key line, 24 px: two 24 px sample bars with their phrases left; scale caption right.
4. Rows, 26 px, arrival order (intern PR last). Columns: title 300 · track 624 · count 112 · state 116; gaps 16.
5. Foot line: "19 finished · Undo last".

**Opened ledger, 1440 × 900** (content 960, never scrolls):
1. Top bar: "← Inbox · 4 left".
2. Title 28 px; under it agent, repository, time, "Check on GitHub".
3. The bar, 40 px, a label under each block, scale caption right.
4. Five lines, 44 px each, label column 120 px: Asked, Did, Extra, Read these, Proof.
5. Risky-lines panel opens under Read these and pushes Proof down.
6. Action bar, 72 px: one saffron primary right.

**390 px.** Inbox rows 48 px: title and count, then the bar; the list scrolls; numeral 44 px. Ledger is one screen, bar 32 px; Read these swaps the five lines for the panel with "Back to ledger". Primary fixed at the bottom, 56 px.

## 4. The story, beat by beat

Easing `cubic-bezier(0.16,1,0.3,1)`. Reduced motion: 150 ms opacity, counter jumps. No entrance animation.

**Play the story.** `?story=1` loads a stored fixture of measured results: no network, clock frozen at 09:00, waits for fonts, hides the cursor. Space plays the next beat, 1–5 jump to a beat, R restarts. `?story=auto` runs all five on the video timings. No story controls on screen.

**1. Cold open (0:00).** Every bar hatched end to end; the intern bar is a four-line block at the bottom. "10,214 lines written overnight." Nothing moves. Eye: numeral, then the wall of hatching.

**2. Wow 1 (0:15).** "Trim all" (T).
- Rows resolve top to bottom, 90 ms apart: the needed part turns solid (clip-path from the left, 240 ms).
- At 2.3 s the hatched ends of the 19 proven rows leave together (translateX 32 px, opacity 0, 480 ms). The other four keep their hatching.
- The numeral counts 10,214 → 96 across the 2.8 s; the words swap to "lines need you." (opacity, 150 ms). Finish replaces "Trim all".
- Enter ×19: the stub folds into a tick (scaleX to 0 from the left, 160 ms; tick stroke, 160 ms), the row closes (height, 180 ms). A new Enter completes a running fold at once.
- Eye: numeral, then the column emptying to four rows.

**3. Wow 2 (0:45).** Open "Cap instant-transfer fees" (O).
- Its bar grows into the ledger bar (transform, 360 ms); other rows fade (160 ms).
- First open only, skippable: "Retry rewrite · 610" lifts out (translateY −20 px, opacity 0, 320 ms), the lamps sweep once (600 ms) and stay lit; 500 ms later "Currency cache · 318" does the same. The gap closes (width, 400 ms), leaving "The cap · 212", a fifth of the width. Both blocks appear as chips in the Extra line.
- N or the notch opens the panel (grid row 0fr→1fr, 240 ms): six lines, the rounding line marked.
- "Send back trimmed" (S): the bar leaves left (translateX −48 px, opacity, 320 ms); in the inbox its row closes and the numeral drops by 6.
- Eye: the lifting block, the lamps, the marked line.

**4. Wow 3 (1:20).** Open the intern PR: hatched end to end. Three breaks open in turn (gap 0→8 px, 200 ms, 250 ms apart) as three lamps turn red. "Block and ask what they meant" (B): stripes and outline turn red (colour, 240 ms), the barrier closes (scaleY, 200 ms), the sent message replaces the button. Eye: the Asked line, then the barrier.

**5. Close (1:50).** Story mode only: crossfade (300 ms) to the closing line, centred, 40 px.

## 5. Components

**PR bar row.** Title 14 px 500, one line. Count "1,140", then "212 of 1,140" after trim. State: saffron Finish (24 px) on the current proven row only; otherwise "Proven", "Needs you · 6", or red "Blocked". Current row on orchid-wash. Click opens; O opens the first row that needs you. Loading: stripes at 40 % opacity, "Trimming…". Error: "Couldn't run tests · Retry". Empty: "Nothing to sign. New agent PRs appear here, measured."

**Counter.** One sentence: numeral 64 px, words 20 px, same baseline. Always the sum of Read-these lines in PRs still in the inbox.

**Opened ledger.** Each line: 14 px 600 label, one 16 px sentence, numbers 600, at most two lines.

**Named blocks.** Label under each: name · line count. Under 60 px wide, the label hangs on a leader line. Extra-line chips are 20 px hatched bars with the same label; clicking one shows it back in the bar and changes nothing.

**Test lamps.** 8 px circles, 4 px apart, in Proof. Lit: aubergine. Running: orchid-deep outline, pulsing. Failed: red ring with a diagonal. One per test up to 48, then one per test file, and the sentence says so.

**Risky-lines panel.** White, JetBrains Mono 13/22, aubergine only. Path and line numbers aubergine-2. Up to 8 lines, then pages ("1–8 of 22"). A marked line sits on saffron-wash with a one-sentence Archivo note under it.

**Finish.** 40 px, saffron, aubergine 16 px 600, 1 px saffron-deep border; hover 2 px border; disabled rule fill; busy "Finishing…"; failed "Couldn't merge. Check on GitHub, then try again." Enter is Finish wherever Finish shows and does nothing elsewhere.

**Send back trimmed.** Same button. Above it, the one-sentence note to the agent, editable in place.

**Blocked state.** Red-striped bar with barrier, row on red-wash, "Blocked", the sent message and "Undo block".

## 6. Copy

- Counter: "{n} lines written overnight." → "{n} lines need you." Sub-line: "23 PRs from agents. None checked yet." → "19 of 23 proven. 4 need you."
- Key line: "The ask needs this" · "Nothing checks this".
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
- Close: "Every line earns its place, or it doesn't ship."

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
4. After Finish ×19: four rows and "19 finished · Undo last".
5. Fee-cap ledger: block counts sum to the PR total; after the replay one solid block a fifth wide, two chips in Extra, all lamps lit.
6. Panel open: six mono lines, one on saffron-wash with its note; Proof and the primary visible without scrolling.
7. Intern ledger: no solid part, three breaks, three red lamps; after Block, a red bar with barrier and the sent message.
8. Red appears only on the intern PR.
9. 390 px: no horizontal scroll, primary fixed at the bottom, caption reads "600 lines".
10. Text contrast at least 4.5:1; hatch outline at least 3:1.
11. Only Archivo and JetBrains Mono load; counts align in their column.
12. `?story=1`: Space five times gives the same five frames on every run.
