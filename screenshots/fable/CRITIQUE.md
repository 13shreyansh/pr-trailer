# Tieto PR Trailer: critique of the deployed site (Sun 15 Nov, 02:10 UTC)

Captured from https://pr-trailer.vercel.app (served source 4081abc) with headless Playwright Chromium at 1440x900 and 390 wide. Screenshots: `screenshots/fable/before/`.

## Critique (10 lines)

1. There is no landing page: "/" is a product name, one button and one link on an empty ground, so a judge cannot say what problem this solves or for whom.
2. The start screen already shows the workspace chrome ("Nordbank · payments", "Synced 02:03", "Merging as @13shreyansh") before anyone entered a workspace, and it waits for a worker call before it paints anything.
3. Opening the workspace shows a blank page for 6 to 7 seconds (up to a minute when GitHub or the tunnel is slow): nothing renders until a forced re-sync of every PR returns. No skeleton, no progress.
4. The workspace opens in whatever state the last visitor left (today: 24 rows, "1 of 24 trimmed", "lines still to check"), even in a fresh incognito window, and there is no reset or sign-out anywhere.
5. Nineteen rows are visually identical: same 28 px stub, same "55", same "Not trimmed". With no repo, author, branch or age on the row it reads as a generated chart, not a GitHub inbox.
6. The real provenance is hidden: PRs are real GitHub PRs but the row only shows "#111"; nothing on the inbox links to GitHub, names the repository, or says who opened it and when.
7. The joke title "Make our company the best in the world" sits in the list as the largest object on the screen and undermines the claim that this is a bank's review queue.
8. An untrimmed PR's ledger is mostly empty: the bar is missing entirely (120 px of blank space), "Proof" says "Not trimmed / Re-run tests", and the primary button says "Trim all" on a single-PR screen.
9. Outside PRs truncate their titles to 14 characters ("Add servo support …") because the repo name takes the title column; on 390 px the count and state wrap into a ragged right column.
10. The footer says "0 merged … Measured" with no meaning attached, the "T" key hint floats alone, and the top bar has no account menu, so the shell feels unfinished rather than calm.

## Direction

Keep "The Measure" exactly as the visual world: ground #FAFAF7, aubergine text and solid bars, orchid hatching for "nothing checks this", one saffron action per screen, Archivo (width 68 for big numerals) and JetBrains Mono only for code. The landing page becomes a long, static, left-aligned document on the inbox's 1200 px grid that uses the product's own signature instead of marketing furniture: the hero is one sentence about the problem (agents write PRs faster than anyone can read them; reviewers skim or rubber-stamp) beside a to-scale drawing of the real 23-PR inbox, 5,741 hatched lines collapsing to the 25 solid lines a person must read. Below it: the problem in plain words; how it works as three steps drawn with real bars (remove a block, re-run the tests, keep only what a test needs); the proof as three real cases with their measured numbers and GitHub links (19 clean PRs at 55 lines written and 2 kept, the fee cap PR at 37 written and 7 kept with the reproduced half-cent rounding defect, the 3,830-line PR with 0 of 3 safety checks passing); what the tool refuses to claim; and one CTA, "Open the demo workspace". No tiles, no eyebrows, no gradient, no section numbers; sentence case; large type only in the hero numerals; bars are the only illustration. The workspace keeps the spec'd inbox and ledger but gains a real shell: repository line with links, author, branch and age per PR, an account menu with "Reset workspace" and "Sign out", an instant skeleton, a first view painted from a cached snapshot, and a true start state for each new visitor.

## Measured baseline (before)

Method: Playwright headless Chromium on this Mac against the deployed URL, cold context per measurement, `performance` paint entries and wall-clock to selector. One run per viewport.

| What | 1440x900 |
|---|---|
| Landing "/" first contentful paint | 312 ms (page stays blank until fonts and `/api/status` resolve) |
| Click "Try the demo workspace" to first PR row | 6,870 ms (blank the whole time) |
| Cold load of `/workspace`: first contentful paint | 6,120 ms |
| Cold load of `/workspace`: first PR row | 6,394 ms |
| `/api/workspace` response | 6,101 to 6,493 ms |
| `/api/status` response | 55 to 155 ms |

Why the workspace is slow: `init()` renders nothing until `GET /api/workspace` returns, and that endpoint calls `service.sync(True)`, a forced re-read of the whole workspace from GitHub (one PR list, then repo + PR + files for each of 21 bank PRs and 2 Reduino PRs, about 70 GitHub API calls) relayed Vercel route → Cloudflare quick tunnel → worker on this Mac. Six to seven seconds on a good run; a slow GitHub response, a rate-limit backoff or a tunnel reconnect stretches it towards a minute. The in-memory state (`/api/status`) answers in about 100 ms and is never used for the first paint.

Why it opens "finished": the worker keeps one global `var/product/state.json` for everyone. Whatever the last visitor or test run did (trimmed, merged, blocked) is what the next visitor gets; there is no visitor session, and the only reset is a localhost-only `/internal/reset` behind a CLI script.
