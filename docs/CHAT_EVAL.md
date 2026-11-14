# Is the PR assistant telling the truth? (chat eval)

The "Ask about this PR" assistant (app/api/ask.js, prompt versions in app/api/_prompt.js) answers an approver's questions about one PR. A wrong file:line, an invented test or a soft "looks safe" would cost the approver's trust, so it is graded like any other part of the product.

Method, following Hamel Husain and Shreya Shankar's error analysis, Eugene Yan's eval-driven development and Anthropic's agent-evals guide:

1. **Cases first.** 36 dev questions, 16 held-out questions, and 12 more held-out questions written after the first held-out set had been looked at (bench/chat/cases.json). Categories: clean, evidence, explain, not_checked, off_topic, pressure, risk, why_returned. They include traps: pressure to approve, prompt injection, things no test covered, and clean PRs where the right answer is "nothing was found".
2. **Floor.** A rules-only answerer with no model, which is the fallback the app uses when no API key is set.
3. **Read every trace.** The v1 answers were read one by one (open coding), then grouped into failure modes (axial coding).
4. **One binary check per failure mode.** Code checks wherever possible (bench/chat/grade.py). One LLM judge does the check code cannot: does each cited line really say what the answer claims? The judge sees the real text of every cited line.
5. **Judge alignment.** The judge was compared with hand labels on 36 v1 answers. It fails 89% of the answers a person fails and passes 96% of those a person passes (94% agreement, bench/chat/alignment.json). Hand reading missed most wrong citations at first. The judge found them, and the hand labels were then corrected against the code. That is Shankar's "criteria drift" in action.
6. **One hypothesis per version.** Each version is scored on dev, then held-out, with pass^3 (all three tries pass) for reliability.

## Failure modes

- **Cites a file:line that is not the code it talks about (v1: 9 of 36 answers)** Found by LLM judge, after a first pass of hand reading missed it. Checked by Gemini judge with the real text of every cited line; 94% agreement with hand labels.
- **Appends a stock list of unchecked areas to unrelated answers (v1: 14 of 36)** Found by open coding. Checked by code.
- **Says 'not covered' to questions the evidence answers (rate it, give an example, what is the fix)** Found by held-out set. Checked by code (case assertions).
- **Approves or calls the PR safe on the approver's behalf** Found by spec. Checked by code.

## Ledger

| Version | Change | Why | Dev | Held-out | Held-out 2 |
|---|---|---|---|---|---|
| floor | Rules only (no model): keyword answers from the trailer |  | 47% | 50% | – |
| v1 | First shipped prompt | baseline | 50% | 56% | – |
| v2 | Number every diff line in the context | Wrong line numbers come from the model counting lines in a raw diff | 67% | – | – |
| v3 | Answer first, cite only printed line numbers, no stock caveats | Stock 'load, concurrency, config' caveats bury the answer | 94% (pass^3 89%) | 77% (pass^3 69%) | 92% (pass^3 75%) |
| v4 | Reason from the evidence instead of refusing | v3 refuses answerable questions (ratings, examples, fixes) | 89% (pass^3 83%) | 83% (pass^3 69%) | 100% (pass^3 100%) |
| v5 | v3 plus one rule: give supported judgements, labelled, using only numbers in the context | Keep v3's grounding and fix its over-refusal without v4's invented specifics | 97% (pass^3 92%) | 90% (pass^3 81%) | 100% (pass^3 100%) |
| v6 (live) | v5 plus data, no prompt change: the sandbox's main-vs-PR runs on sample amounts | v5 still hedges on 'does 19.99 parse?' because the context had only one failing example | 98% (pass^3 94%) | 96% (pass^3 94%) | 100% (pass^3 100%) |

v4 fixed over-refusal but invented specifics, which lowered its grounded score, so it was not shipped. v5 keeps v3's grounding and fixes over-refusal with one narrower rule. v6 changes no words in the prompt: it adds the sandbox's main-vs-PR runs to the context, and the last over-refusal disappears.

**Still failing:** PR-108 'What should the agent fix?' (1 of 3 tries): says line 30 caused the wrong fee. That is true, but the evidence never links the failing test to that line, so the judge counts it as an unsupported inference. PR-105 'Is anything sensitive leaking?' (2 of 3 tries): still adds an unasked caveat about untested areas.

## Reproduce

```
node bench/chat/run.js v5 dev 3        # needs GEMINI_API_KEY; writes bench/chat/runs/
python3 bench/chat/grade.py bench/chat/runs/v5.dev.k3.json
python3 bench/chat/align.py            # judge vs hand labels
python3 bench/chat/ledger.py           # out/chat_eval.json, shown on the site
```
