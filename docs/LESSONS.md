# Lessons log, failure modes and decisions

## Failure modes we actually hit while building (14 Nov 2026)

1. **A vacuous "no behaviour change" proof.** The differential tester guessed that a parameter named `iban` was an integer, because the name ends in "n". Every call raised the same error on main and on the PR, so a real masking bug (`s[:4]` → `s[:5]`, which leaks a digit) "matched on 4000 inputs". *Fix:* use type annotations first, and draw strings from a corpus of the repo's own literals. *Lesson:* equivalence evidence can be empty. A trailer should say how many inputs actually reached the changed code.
2. **A red test on main hides regressions.** The premium-limit acceptance test fails on main because the feature isn't built yet. A mutant that changed the basic daily limit by one cent broke the same test, so no *new* failure appeared. *Fix:* a separate rule flags module-level constant changes in "no behaviour change" PRs. *Lesson:* main must be green, or each criterion needs its own test.
3. **Random inputs can be too random.** Banker's rounding in PR-110 passed one fuzz run, because the corpus rarely picked `"instant"`. *Fix:* weight the changed module's own literals. *Lesson:* use a fixed seed and report the number of inputs.
4. **Input-validation boundaries survive.** Mutants on IBAN length limits (15 and 34 characters) passed as light checks: no valid 15-character IBAN exists in the test corpus. The trust ledger then withdrew trust for that area. *Lesson:* domain-specific generators (valid IBANs per country) would close this gap.
5. **Our own bugs flatter our checks.** The strict catch rate is 88% on hand-planted bugs but lower on mechanical mutants (see RESULTS.md). We report both.
6. **Coverage was blind to the browser.** Lines run only by UI tests looked untested, which pushed clean UI PRs into targeted review. *Fix:* the API server now runs under line tracing during the browser tests.
7. **The temptation to block on opinion.** The new `/api/metrics` endpoint (PR-111) is not a bug, but it is new attack surface. We made it a refusal for the security owner, not a finding.

## Decision log

| # | Decision | Why | Trade-off |
|---|---|---|---|
| D1 | Deterministic checks first; LLM optional and advisory | Verification beats confidence; the demo runs with no API key | Narrower semantic coverage |
| D2 | Findings block only when reproduced | Zero false blocks keeps the lane credible | Some real issues only route attention |
| D3 | Add a "Return to agent" lane | Humans should not spend time on verifiably broken PRs | The second review after the fix is not saved |
| D4 | Synthetic banking domain, synthetic data only | Tieto's banking clients; the brief requires cleared data | Small codebase |
| D5 | Name tests `REQ_<ID>.test_ac<N>` | Free traceability from evidence to requirement | Convention must be enforced |
| D6 | Every untested criterion becomes a refusal, even if the PR doesn't claim it | No silent passes | Fewer light checks (PR-101 goes to targeted) |
| D7 | Benchmark on mechanical mutants as well as planted bugs | Unbiased estimate | Includes equivalent mutants that count as misses |
| D8 | Model review minutes with explicit assumptions | No real reviewers available at the hackathon | Must be validated with a timer |
| D9 | LLM findings need a verbatim quote, or they are dropped and counted | Makes hallucination measurable | A correct finding with a sloppy quote is lost |
| D10 | Trust ledger per area: 3 clean PRs to earn the light lane; an escape means 5 full reads | "Trust is earned per area, withdrawn after escapes" | Slower start in new areas |
