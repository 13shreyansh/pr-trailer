# Eval spec: what "it works" means, checked

Each criterion comes from the Tieto brief, the mentors at the booth (docs/CONCEPT.md) or the judging rubric. Each one has a check that can fail.

| # | Criterion (source) | Check | Result |
|---|---|---|---|
| 1 | The approver reads a few lines, not everything, and the bugs are in those lines (booth: "which lines are worth a human look") | Effort-aware recall over the 13-PR sprint (bench/effort.py): lines read before every planted bug is in front of the reader | 37 lines, vs 183 reading the diff top to bottom, 209 smallest-PR-first, 290 at random. The whole reading list is 66 of 290 lines |
| 2 | Only proof may block, so people keep trusting the lane (mentors: no false alarms) | Clean PRs blocked | 0% of 5 |
| 3 | It catches what matters, not just what we planted | Held-out mutants we did not write and never tuned on | 100% located: 12 sent back with proof, 6 put in front of a human |
| 4 | Better than the AI reviewers teams use today (rubric: comparison) | The same 13 PRs reviewed by Devin and Codex (bench/ai_reviewers.json) | 8/8, vs 4/8 visible for Devin and 3/8 for Codex. Copilot refused because it was out of quota |
| 5 | "Does it do what it should, and nothing else?" (booth) | Outcome verdicts per PR, from tests on main vs the PR and the scope of the changed units | Shown first on every PR page |
| 6 | Some changes need a video, a diagram, numbers or audio rather than code (Shreyansh's brief) | Format router that shows its rule. Numbers tables come from running main and the PR on the same inputs | 13/13 PRs get at least one format: 3 sandbox tables, 3 videos |
| 7 | The AI never approves; a person signs with a reason (mentors: accountability) | Code check on every chat answer. The UI requires a reason and ticked risks | 0 approvals in 192 graded chat answers from the live version |
| 8 | The assistant is grounded (rubric: trust) | docs/CHAT_EVAL.md | v5: dev 98%, held-out 96%, held-out 2 100% |
| 9 | A judge with no context understands it in a minute (rubric: clarity) | Fresh-eyes walkthroughs of the deployed site by an independent model (docs/JUDGE_WALKTHROUGH.md) | See that file |

Honest limits:
- The bank is small and synthetic: about 400 lines of product code, with 290 changed lines in the sprint.
- We wrote the planted bugs and the checks ourselves. That is why the held-out mutants and a second held-out chat set exist.
- Review minutes are modelled, not timed.
