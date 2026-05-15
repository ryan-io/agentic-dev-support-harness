# Learning Pipeline Investment Plan

Date: 2026-06-04
Status: Phases 0-4 implemented 2026-06-05; verification windows open; Phase 5 evaluation gate due four to six weeks after Phase 2
Governing ADRs: `adr-learn-capture-corrections-via-transcript-parse` (Proposed), `adr-learn-establish-shared-project-memory` (Active), `adr-learn-replace-wall-clock-decay-with-evidence-based-staleness` (Proposed)

The pipeline's governance layer works: human-gated proposals, confidence thresholds, decay. Its signal layer does not: `observe.py` sees only tool metadata, so the detector cannot see the corrections it is named for. The one rejected proposal (`consistent-edit-pattern-on-md`, 0.90 confidence from a docs session containing zero corrections) is the proof. This plan implements the corrections ADR and matures the loop around it, in five phases. Each phase has exit criteria; no phase starts until the prior one meets them.

## Cross-cutting constraints

These hold in every phase, inherited from the two governing ADRs and `agent-guardrails`:

- Privacy boundary: only derived fields reach `observations.jsonl`. Raw transcript text never leaves the machine and never enters git.
- Hooks fail closed: any parse error is swallowed, the hook exits zero, the agent is never blocked.
- Instruction files stay human-gated. Pipeline output proposes; the developer applies.
- The capability is Claude Code only. Copilot contributors produce no correction signal; this is accepted, not solved here.

## Phase 0: Clear the decks

Goal: start from a clean, measured baseline. Effort: hours.

1. Review remaining pending proposals via the `continuous-learning` skill. Reject proxy artifacts; they predate the hardened detector.
2. Run the first memory curation pass. `memory.instructions.md` is still placeholders; promote durable facts from `session-delta.md` so the digest does its job and the curation step is exercised end to end.
3. Snapshot baseline metrics: observation count, instincts by confidence, proposals created/applied/rejected. Phase 5 measures against this.

Exit: no stale proposals pending, digest populated, baseline recorded at the bottom of this file.

## Phase 1: Transcript-parse correction capture

Goal: implement the corrections ADR. The detector consumes actual user language instead of inferring from tool repetition. Effort: the bulk of the plan.

1. Schema. Add the `correction` observation type with exactly three derived fields: target file or topic, normalized change description, trigger-phrase category. Document it in `.github/scripts/learning/README.md`.
2. Parser. In the Stop branch of `observe.py`: read the transcript path Claude Code passes, walk user turns, classify each as corrective or not. Conservative by construction: ambiguous is not a correction. Pair a corrective turn with the prior agent action. Wrap the whole path so read or parse errors fail closed. Pin the expected transcript format and degrade quietly if it shifts.
3. Validation. Add a `validate-system.py` check asserting the correction path emits no raw transcript content (fixture-driven).
4. Tests. Mock transcripts covering: clear correction, ambiguous turn, no corrections, malformed JSON, oversized file. Tests live in a dedicated test directory, no network, temp filesystem only.
5. Flip the ADR to `Active` per its own enforcement clause.

Exit: one week of real sessions with zero hook failures, `correction` observations present in the log, validation check green, ADR flipped.

Status 2026-06-05: implemented (parser in `observe.py` on SessionEnd, schema documented in the learning README, privacy check in `validate-system.py`, mock-transcript tests). ADR flipped to Active; the one-week zero-failure window and first-batch precision review are still open.

## Phase 2: Consumption and seeding

Goal: the analyze/propose stages treat real corrections as the strong evidence they are, and proposals become actionable. Effort: medium.

1. `analyze.py`: correction instincts seed above the 0.30 proxy and need fewer reinforcements to promote. Every instinct carries provenance: `user-correction`, `self-correction`, or `frequency`. The two are never conflated (ADR requirement).
2. `propose.py`: add a quality gate. A proposal's Suggested Change must contain actionable rule text, not a pattern description. Template the section; a proposal that fails the template is held as an instinct, not promoted.
3. `continuous-learning` skill: the review surface shows provenance and the derived change description. Per the ADR, the developer reviews the first batches of correction instincts before the seed confidence is trusted.
4. `config.json`: seed value and reinforcement count for corrections live here, not hardcoded.
5. Staleness model. Done 2026-06-05 per the dedicated plan, `2026-06-05-evidence-based-staleness-plan.md`: session-clock decay, relevance check, `confirmed` permanence marker, archive reasons, config migration, and the contradiction reducer wired to the Phase 1 correction signal. Both governing ADRs are Active.

Exit: first correction-derived proposal reviewed; developer judges first-batch precision acceptable (target: most flagged corrections are real; a second false-positive saga sends this phase back, not forward). Session-clock and relevance check live, date-based decay code removed, staleness ADR flipped to Active.

Status 2026-06-05: implemented. Correction instincts seed at `correction_seed_confidence` (0.45) with provenance frontmatter; the reducer skips correction-derived instincts so they are not reduced by their own evidence; `propose.py` holds instincts without actionable rule text; the review surface shows provenance and derived change descriptions. Exit still gated on the first real correction-derived proposal review.

## Phase 3: Explicit developer signal

Goal: the high-precision supplement the ADR specifies but defers. Effort: small.

1. Recognize a marker phrase or slash command at submit time (UserPromptSubmit hook) and write a high-precision `correction` observation, labeled as developer-flagged.
2. Document the marker in the learning README. If it earns an instruction-file mention, route that through a proposal.

Exit: marker produces a correctly labeled observation end to end; recall supplement exists for corrections the parser would miss.

Status 2026-06-05: implemented. `#correction` at prompt start (UserPromptSubmit hook, registered in `.claude/settings.json`) records a `developer-flagged` observation paired with the session's last mutating action; the prompt text itself is never logged. Documented in the learning README.

## Phase 4: Memory maturity

Goal: close the memory ADR's technical debt now that better signal feeds curation. Effort: small to medium.

1. Define the curation cadence trigger in `config.json` (e.g., nudge when `session-delta.md` exceeds N session blocks). Today curation is purely manual and has run zero times.
2. Decide the confirmed-instinct serialization: whether the instinct store is committed and whether confidence and decay state travel with it. Record the decision as an amendment to the project-memory ADR.
3. Record the 4,000-char ceiling revisit trigger (the pointer-file fallback) in the same amendment, so it is hit by plan rather than by a failed sync.
4. Correction-derived durable facts become memory-digest candidates during curation.

Exit: cadence trigger live, both ADR debts resolved on paper, digest updated at least once during the phase.

Status 2026-06-05: implemented. Cadence trigger is `memory_curation_nudge_blocks` (5) with a session-start nudge; both debts resolved in the project-memory ADR amendment (instincts stay local including confirmed ones, ceiling revisit at 3,500 chars during curation); correction-derived facts added as digest candidates in the skill; first curation pass ran and the digest is populated.

## Phase 5: Evaluation gate

Goal: judge the investment on evidence, four to six weeks after Phase 2 ships. Effort: calendar time plus one review session.

Measure against the Phase 0 baseline: proposals created/applied/rejected by provenance, classifier precision on the reviewed batches, time from first correction to applied rule, and hook overhead. Three outcomes:

- Calibrate: precision is good but seeds or thresholds are off. Tune `config.json`, continue.
- Extend: the loop earns its keep. Candidates: the deferred real-time classification variant, richer trigger-phrase categories, a Copilot-side story.
- Stop: signal is still thin after real corrections flow. Revisit the strip-it option with evidence in hand.

Record the outcome as an audit note referenced from both ADRs.

## Baseline (filled in Phase 0)

| Metric | Value | Date |
|---|---|---|
| Observations recorded | 551 total: 262 PostToolUse, 265 PreToolUse, 16 legacy Stop, 8 analysis markers; 0 corrections | 2026-06-05 |
| Instincts (by provenance) | 3, all pre-provenance frequency proxies: 2 at 0.75, 1 at 0.62 | 2026-06-05 |
| Proposals created / applied / rejected | 3 / 1 / 2 | 2026-06-05 |

Session counter at baseline: 0 (clock started 2026-06-05). The two rejected proposals are the false-positive proxy artifacts that motivated this plan; the applied one is `skill-post-save-revision`. No instinct or proposal has been archived. Phase 5 measures against these numbers.
