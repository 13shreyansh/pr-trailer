# Tieto recording flow

Use https://pr-trailer.vercel.app. Start with the real workspace restored by `.venv312/bin/python scripts/product/workspace.py reset`. The script touches only `13shreyansh/tieto-nordbank-payments`, whose data and PRs are synthetic. It keeps original PR branches, restores main, reopens the original PRs, closes generated trimmed PRs and removes Tieto's own block comments.

1. Click **Try the demo workspace (Nordbank payments)**. The inbox fetches the bank's current GitHub PRs and the live AIDev PRs. Show the hatched implementation lengths and the real GitHub account in the top bar.
2. Click **Trim all**. Show Queued, Trimming and Stop. The server executes fresh removal trials against the fixed acceptance tests. The progress line counts completed test runs. Wait until Finish appears. Speed this interval up in the edit if necessary; the product has no playback controls.
3. Click **Finish** on the current proven row. Show its merge hint. Each click reruns the bank checks, pushes the measured minimal implementation onto that request's branch and merges the real PR into the bank's main. Repeat on each proven row. Enter is available after the first visible click.
4. Click **Cap instant-transfer fees**. Show the retained cap, the unchecked retry rewrite and currency cache, and the passing ask-test lamps. Click the six lines to read. The marked line introduces half-down rounding: a raw fee of 500.5 cents passes the rounded cap guard and becomes 501 cents. The held-out cap check reproduces it. Click **Re-run tests** if desired; this runs fresh checks.
5. Edit the note above **Send back trimmed**, then click it. The server tests and pushes the minimal cap branch and opens a new PR with the note. This does not merge the rounding bug. The original request closes. The new PR can be verified on GitHub.
6. Open **Make our company the best in the world**. Read the vague ask and the three independently reproduced failures: account ownership bypass, dropped statement column, negative fees. Click **Block and ask what they meant**. A real question is posted on the owned bank PR and its block label persists on GitHub. No code merges.
7. Paste a public GitHub PR URL into the top bar and press Enter. The tool fetches its real additions and deletions. Python repositories with compatible tests run in the isolated sandbox. Repositories whose tests cannot run display **Can't run this repo's tests here** and retain only measured line counts. Outside PRs never get workspace write actions. Measured AIDev PRs offer **Download trimmed patch**.

Use the closing line only in video editing: "Every line earns its place, or it doesn't ship."

Run deployed acceptance with `npx playwright test`. Evidence is saved in `artifacts/e2e/`. This test resets the owned workspace before each viewport, performs real GitHub writes, then independently verifies the resulting PRs and block comment.
