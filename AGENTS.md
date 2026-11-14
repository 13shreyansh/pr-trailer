# Junction 2026 rules for Codex (shared by every entry, dated Sat 14 Nov 19:45)

Goal: win the sponsor prizes at Junction 2026. Final deadline Sun 15 Nov 10:00 Helsinki.
Shreyansh decides taste and direction. The Chief (Claude) writes each job. You decide how to build it.

## Work rules
- Work only inside this entry's folder. Do not read other entries.
- Read only what the job needs. The entry AGENTS.md and STATUS.md carry the context.
- Before you build, write a 5-line paraphrase of the goal, scope and acceptance cases at the top of STATUS.md.
- Prove it works on the real artifact: the live URL, a real browser, real data. "It compiles" is not done.
- Every bug you find becomes a regression test before you move on.
- Label every number as measured, inferred or guess.
- For any UI work, read ~/Documents/ChatGPT/Junction/DESIGN-FLOOR.md and this entry's DESIGN-DIRECTION.md first.
- Before reporting, have a separate reviewer (6 Astra) run two passes, one on spec fit and one on build quality. It reruns the quality commands itself.

## Allowed without asking
Create repos under 13shreyansh, Vercel projects and env vars, API keys on his signed-in accounts, dataset downloads, deploys to this entry's own Vercel project or VPS.

## Never without "APPROVED BY SHREYANSH" in the job
Discord posts, video uploads, portal submissions, purchases, deletions, messages to people. Never write a key or password into a file, log or reply.

## End every job by overwriting STATUS.md, with your final reply the same text
```
ENTRY / time / commit / live URL
DONE: up to 3 bullets
NUMBERS: dev / held-out / baseline, each labelled measured, inferred or guess
SCREENSHOTS: 2-3 paths (desktop first screen, 390px first screen, key moment)
REVIEW: reviewer verdict in one line, plus what it flagged
NEXT: the next goal you propose
NEEDS DECISION: a taste or direction question, or "none"
BLOCKED: or "none"
```

## Browser and tools
- Do not use sub-agents unless necessary.
- Use Codex's inbuilt browser for all web, account and UI actions. Use IAB through cua_repl. Never open, attach to or control Shreyansh's personal browser windows or profiles. Do not launch an external browser as a workaround.
- Local tools remain appropriate when necessary for coding, builds, tests, SSH and secret-safe operations.

---

# Tieto: "Every line earns its place" (dated Sat 14 Nov 21:35)

Why it exists: coding agents now open PRs faster than any engineer can read them, and the engineer who merges is still accountable. Tieto's challenge is earned trust in AI-written code: the human must be able to say "it does what it's supposed to do, nothing else, and I can sleep well if I merge this".
The judge: Tieto engineers. Booth notes: the human is the accountable approver; review in a narrative order (behaviour first, then the few risky spots); keep "does it work" and "only what was asked" as separate checks; contrast with plain Copilot-style review comments.
Wins if: in 2 minutes a judge sees (1) ~10,000 lines of agent code collapse to the ~100 that need a human, with clean PRs finished in one tap each; (2) a real PR trimmed live to what the ask needs while tests stay green, then sent back as a clean minimal PR; (3) the funny intern PR ("Make our company the best in the world. Make no mistakes.") blocked with the exact changes that would break production.
The spine: a PR should do only what was asked. Trim delta-debugging style: remove each part, re-run the tests. Every line lands in "the ask needs this" (a test breaks without it) or "nothing checks this" (extra OR untested; say both honestly).
Out of scope: chat, opinions without a test run, scores, the old per-PR section pile, Linux kernel builds.
Hard constraints: every number on screen comes from a real test run, labelled measured. Real agent PRs from AIDev (hf.co/datasets/hao-li/AIDev) in repos with fast tests for the hero PRs; a realistic synthetic bank repo is fine for the inbox filler and the intern PR. Never merge or comment on real GitHub PRs.
Existing code: github.com/13shreyansh/pr-trailer (live https://pr-trailer.vercel.app, sandbox runner, Gemini via GEMINI_API_KEY). Keep the URL; rebuild the UI from DESIGN-DIRECTION.md.
Sponsor brief and booth notes: ../context/tieto.md (read once at the start).
Design: DESIGN-DIRECTION.md. Decisions: DECISIONS.md.

## Real product, never a scripted demo (Shreyansh, Sat 21:46 — applies to every entry)
- The site is a professional, real product. No "Play the story" mode, no auto-appearing cards, no seeded events that fire by themselves, no "demo" banners on the main flow.
- Entry: a clean start screen with one small "Try the demo account" option that drops you into a normal account (e.g. Hotel Aurora). No password fields. Inside, everything behaves like the real thing.
- Every step of the video is done by a real user action on the live site (typing, speaking, uploading, clicking). Videos are recorded by an agent (Manus) actually using the live site, so the full flow must really work end to end.
- Prove it: an end-to-end browser test (Playwright, headless Chromium) runs the whole video flow on the DEPLOYED URL as a user would, at 1440x900 and 390 px, and saves screenshots. That test is the acceptance check.
- Sample inputs a tester needs (e.g. a whiteboard photo) live at a separate unlinked /samples path, never inside the product UI.
## Exact spec and taste gate (Shreyansh, Sat 22:10 — applies to every entry)
- DESIGN-DIRECTION.md is the exact screen spec written by the Chief: placement, sizes, colours, fonts, copy, states. Follow it exactly; engineering is yours. Where it is silent, pick the plainest consistent option and list it under "Spec gaps I filled" in STATUS.md.
- Before reporting, loop on the DEPLOYED site until every item in ../kit/TASTE-GATE.md is a yes: build, deploy, run the E2E test, look at every screenshot, fix, repeat. Report each item's yes/no with its screenshot in STATUS.md.
