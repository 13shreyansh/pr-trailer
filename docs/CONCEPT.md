# Concept card: PR Trailer

**Team:** The CS Guy · Junction 2026 · Tieto "Earned Trust in AI Code"

## Recommendation

The person who merges an AI-written PR is not a "reviewer". They are the **approver**: the owner who is accountable that the change does what it is supposed to do, and nothing else. Today the only way to carry that is to read every line. Stop asking for that. Make every agent PR ship with a **trailer**: a short, checkable story of the change, built from evidence and traced to the requirement ID. The trailer opens with the outcome ("Does it do REQ-X? Does it do anything else?"), shows confidence per area with the reason, and lists the few spots (at most 10) worth a human look. The owner approves or denies the outcome with a written reason. The AI collects evidence, attacks the change and asks questions. It never approves.

Hypothesis (from the Tieto booth, not yet measured with a stopwatch): this turns "three days reading code" into "half an hour approving an outcome", and lets the owner sleep without fearing a 3 a.m. call. The modelled review minutes in RESULTS.md are a first, partial test of it.

Every PR lands in one of four lanes:

| Lane | When | Human cost |
|---|---|---|
| **Return to agent** | A problem is *reproduced* (failing acceptance test, broken invariant, probe, counterexample) | ~1 min: read the evidence, bounce it |
| **Light check** | Every criterion has passing evidence, no open questions, two-way door | ~2 min: read the trailer, watch the clip, sign |
| **Targeted review** | The AI refused to decide something, or some changed lines never ran | Answer the named questions, read only the flagged hunks |
| **Full read** | One-way door, or security policy | The owner reads everything; the trailer is the map |

## What a trailer contains (per requirement ID)

0. **Outcome first:** two verdicts, "does it" (each acceptance criterion has passing evidence) and "does nothing else" (every changed function body is reached by the stated requirement's tests, or is flagged as outside the outcome). Then confidence per area (frontend, backend, data, security) with the reason, and "review these N spots".
1. **Evidence per acceptance criterion:** the test that proves it, run on main and on the PR (fail→pass, pass→pass, pass→fail). UI changes get a captioned Playwright video and before/after stills. Backend changes get a sequence diagram generated from the code that actually changed.
2. **What the AI found:** each finding says whether it was *verified* and how. Only verified findings can block.
3. **What the AI refused to decide, and why:** questions about intent, security and irreversible actions, each with a named owner. Example from PR-109: "Rows selected on `transfers` changed. Dropped `user_id = ?`. Is that intended?"
4. **Merge danger:** door type (two-way, two-way with residue, one-way), blast radius (changed functions → callers → API entry points → screens).
5. **Approver's decision:** what was checked, what was not checked, the residual risk the owner accepts, the questions they must answer, and one checkbox: "The AI review was advice, not approval." Approve or deny, always with a written reason, so the record says why.

## Principles

1. **Evidence over confidence.** There are no model confidence scores. The per-area confidence is derived only from evidence (verified problems, open questions, lines no test reached), and each level shows its reason. A claim is either backed by something the owner can re-run or marked as advice.
2. **Only reproduced problems block.** Static rules and LLM opinions route attention. Tests, probes, invariants and counterexamples decide.
3. **Trace everything to a requirement.** Acceptance tests are named `REQ_<ID>.test_ac<N>_*`, so evidence attaches to criteria automatically. A criterion without a test becomes an open question. It does not count as a silent pass.
4. **Refuse out loud.** The AI does not judge intent ("should this count fewer rows?"), authn/authz logic, data destruction, or equivalence it cannot demonstrate. Each refusal says why and who must answer.
5. **Depth follows danger, not diff size.** A 2-line migration that drops a column gets a full read. A 30-line metrics change gets a targeted one.
6. **Trust is earned per area and withdrawn after escapes.** A trust ledger allows light checks in an area only after a clean streak, and forces full reads for the next 5 PRs after a bug escapes.
7. **LLM output must be grounded.** Every LLM finding quotes the line it is about. If the quote isn't in the PR, the finding is dropped and counted as a hallucination.
8. **Measure outcomes, and test the reviewer.** Catch rate, false alarms, escapes and minutes, on hand-planted bugs *and* on mechanical mutants that we did not write.

## How it balances the five tensions

| Tension | Our choice |
|---|---|
| Risk | Lane by door type and blast radius; security and one-way doors always get a human read |
| Hallucination | LLM findings need a verbatim quote, cannot block, and are counted when dropped |
| Transparency | Every check is listed under *Checked* or *Not checked*, with its method |
| Confidence | Per area, derived from evidence with a stated reason; each item is verified, grounded-but-unverified, or refused |
| Quality | Acceptance tests, team invariants, differential testing for "no behaviour change" claims, runtime probes (IDOR, PII in logs) |

## Trade-offs we accept

- **Deterministic first means narrower coverage.** We accept missing some subtle logic bugs in exchange for zero false blocks. An LLM layer can widen coverage, but it is advisory only.
- **Refusals cost minutes.** PR-109 took slightly longer than a plain read, and that was exactly where the bug was.
- **Repo-specific rules.** The invariants file and the rule pack encode one bank's standards. Each team owns its own.
- **The acceptance tests are the oracle.** If they are wrong or red on main, the trailer is partly blind (see lessons log).

## Limits

- Synthetic sample: 13 PRs, 49 dev mutants and 18 held-out mutants on a small Python service. Not a field study.
- Review minutes are **modelled** with stated assumptions, not stop-watched.
- We wrote both the planted bugs and the checks. The mutants exist to correct for that, and the catch rate on them is lower.
- Not covered: concurrency, performance, infrastructure and configuration, and multi-PR interactions.
- "Matched main on 4000 inputs" is evidence, not proof. The video shows one scripted path.

## Questions judges will ask

**What would make you not trust your own output?** Any of these, which the ledger and bench track: a bug escaping in an area (trust is withdrawn automatically), mutant survival rising, acceptance tests red on main, the LLM hallucination rate climbing, or owners answering refusals in seconds (rubber-stamping). We also recommend spot-checking 10% of light-lane PRs with a full read to measure misses directly.

**Who owns the decision?** The CODEOWNERS-named engineer for the changed area. Each refusal adds a named co-signer (security, data). The AI's output is advice. Merge requires the owner's checkbox, and the card records what they accepted.

**How would this scale?** It runs as a CI job: about 0.5 s per backend PR and about 10 s with browser evidence. Human time scales with risk, not volume. In our sample, 7 of 13 PRs never needed a human read, because their defects were reproduced and sent back to the agent automatically. Rules are plugins per repo, and the trust ledger relaxes review only where it has been earned.
