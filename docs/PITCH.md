# PR Trailer: 2-minute video and 5-minute live pitch

Live app: https://pr-trailer.vercel.app (the demo path below takes about 90 seconds of clicking).

## The one sentence

AI agents write pull requests faster than anyone can read them, but at a bank a person still signs every merge. PR Trailer runs each PR in a sandbox first, sends the broken ones back with proof, and shows the approver the few lines only a person can judge.

## 2-minute video (shot list)

| Time | Screen | Voice |
|---|---|---|
| 0:00–0:12 | Landing page, hero | "AI agents now write pull requests faster than anyone can read them. But at a bank, a person still signs every merge, and gets the 3 a.m. call." |
| 0:12–0:35 | Sprint card: click "Run PR Trailer on the sprint" and let the squares fade | "This sprint, Nordbank's coding agent changed 290 lines. PR Trailer ran every PR in a sandbox. Seven went straight back to the agent with the failure reproduced. Two were proven by tests and a recorded video. Four need Aino, the payments owner: 66 lines, not 290." |
| 0:35–1:05 | PR-109: outcome verdicts, the agent's decisions row "Remove user_id filtering… The agent gave no reason", the format cards, play 3 s of the audio briefing, then the spot at transfers.py:25. Ask: "Explain in plain words what the risk is at line 25" | "Start from the outcome, not the code. Did it do what the requirement says? Not proven. The agent quietly dropped a user filter and gave no reason. So Aino reads 11 lines, can listen to a briefing on the way to a meeting, and can ask anything. The assistant answers only from the evidence, with the exact line." |
| 1:05–1:20 | PR-110: the "Same inputs, main vs this PR" table, the 75,250-cent row highlighted | "The agent called this a pure refactor. The sandbox ran old and new code on the same amounts: a customer sending 752.50 euros now pays one cent less. Sent back without a human reading a line." |
| 1:20–1:45 | Proof page: the effort chart, then the reviewer table, then the chat ledger | "Does it work? All 8 planted bugs are in front of you after 37 lines. Reading the diff top to bottom, you'd need 183. Devin found 4 of 8 and Codex 3 of 8 on the same PRs. No clean PR was wrongly blocked. And the assistant itself is graded: 98% on 36 questions, 96% on questions we never tuned on." |
| 1:45–2:00 | PR-109 decide: tick the boxes, type a reason, Approve, then the receipt | "The AI never approves. Aino does, in minutes, with the proof attached. PR Trailer: approve the outcome, not the diff." |

## 5-minute live pitch (for Sunday peer review)

1. **0:00–0:30 Problem.** Tieto's mentors told us the person who merges is no longer really a reviewer. They are the approver, accountable that the change does what it should and nothing else. Nobody can read every line an agent writes. Hypothesis from the mentors: three days of reading down to half an hour.
2. **0:30–1:30 Live: the sprint.** Landing, then run the narrowing: 290 → 66 lines. Explain the four lanes in one breath each.
3. **1:30–3:00 Live: one PR end to end.** Use PR-109: outcome first, the agent's decisions with quotes (no reason = flag), the format router ("why this format"), play the audio briefing for 5 seconds, open the impact map, read the spot, and ask the assistant one question live. Then flash PR-110's numbers table and PR-108's video.
4. **3:00–4:00 Proof.** The effort chart, the AI reviewers on the same PRs, 0 of 5 clean PRs blocked, 18/18 held-out mutants located. Then how we graded the assistant: read every answer, grouped the failures, one pass/fail check each, judge checked against hand labels (94%), six versions, held-out sets. Say what still fails.
5. **4:00–4:40 Why it holds up.** Only a reproduced failure may block; opinions, including an LLM's, can only point a human somewhere. The quick-check lane is earned per area and closed by one escaped bug.
6. **4:40–5:00 Ask.** Pilot on one real Tieto repository and time real approvers, which is the number we can't fake here.

## Likely questions

- **"Your codebase is tiny."** Yes: about 400 lines and a 290-line sprint, synthetic so we can plant bugs and know the truth. The method is per line and per PR, so the ratio is the claim. Held-out mutants we did not write show it isn't tuned to our own bugs.
- **"Isn't this just another AI reviewer?"** No. AI reviewers post opinions you have to re-check. We only block on a failure we reproduced in a sandbox, and we tell you what not to read. On the same PRs, Devin found 4 of 8 bugs and Codex found 3 of 8.
- **"Can the chat hallucinate?"** It is graded on 64 questions with traps. Version 1 cited wrong line numbers in a quarter of answers; numbering the diff lines fixed that. The live version passes 98% on dev and 96% held-out, and never approves (0 approvals in 192 answers).
- **"Where do the minutes come from?"** They are modelled with stated assumptions, not timed. That is why the ask is a pilot with real approvers.
