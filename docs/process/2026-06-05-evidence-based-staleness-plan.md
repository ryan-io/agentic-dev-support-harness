# Evidence-Based Staleness Implementation Plan

Date: 2026-06-05
Status: Implemented (all phases shipped 2026-06-05; ADR Active; Phase 3 real-session verification window open)
Governing ADR: `adr-learn-replace-wall-clock-decay-with-evidence-based-staleness` (Active)
Parent plan: `2026-06-04-learning-signal-fidelity-plan.md` (Phase 2, item 5)
Prerequisite: the contradiction reducer (Phase 4) is gated on `adr-learn-capture-corrections-via-transcript-parse` shipping (fidelity plan Phase 1). Per the ADR's enforcement clause it does not gate the ADR flip; the ADR goes Active after Phase 3.

The ADR replaces wall-clock decay with three rules: a session-clock timer, evidence-based confidence reduction, and structural permanence for confirmed knowledge. Today `propose.py` decays proposals on `proposal_decay_days` and instincts on `instinct_decay_per_month`, both date arithmetic against `last_seen`. This plan lands the replacement in five phases. Each phase has exit criteria; no phase starts until the prior one meets them.

## Cross-cutting constraints

- Hooks fail closed: the session counter must never block the agent. Any error exits zero.
- Date-based decay code is removed, not flagged off (ADR enforcement clause).
- No instinct or proposal is ever discarded without a recorded, readable archive reason.
- Migration must handle existing installs: current `config.json`, instinct YAML, and proposal files keep working mid-migration.

## Phase 0: Session clock foundation

Goal: a reliable session counter, the load-bearing primitive everything else reads. Effort: small.

1. Counter. `observe.py` increments a monotonic counter in `.claude/learning/session-counter.json` in its SessionEnd branch. One increment per session, idempotent against duplicate events, fail-closed.
2. Boundary correction. The ADR names the Stop hook as the session boundary. Stop fires after every assistant turn; `observe.py` already treats SessionEnd as the boundary for delta generation. Use SessionEnd. Record the wording fix as an ADR amendment at the Phase 4 flip.
3. Backfill. On first run after migration, stamp every existing instinct with `last_seen_session` equal to the current counter, and every pending proposal with `created_session` likewise. Nothing decays retroactively; the clock starts now.
4. Undercount note. A killed session never fires SessionEnd and is not counted. Acceptable per the ADR: undercounting delays decay, it never accelerates loss.

Exit: counter increments exactly once per session across several real sessions, zero hook failures, backfill stamped on all existing instincts and proposals.

## Phase 1: Config migration and permanence marker

Goal: the new schema and the structural exemption, before any decay logic changes. Effort: small.

1. Schema. `staleness.proposal_decay_days` and `staleness.proposal_archive_days` become `staleness.proposal_decay_sessions` (default 15) and `staleness.proposal_archive_sessions`. `instinct_decay_per_month` becomes `instinct_decay_per_sessions`. Add `thresholds.pending_proposal_soft_cap` (default 10).
2. Migration. A one-shot, idempotent pass: if old keys exist, write new keys with defaults, drop old keys, preserve everything else. Runs automatically at the top of `propose.py` and `analyze.py`; never errors on an already-migrated file.
3. Permanence marker. Applied proposals, confirmed instincts, and curated memory entries carry `confirmed: true`. Every staleness pass checks the marker first and skips. Exemption is structural, not convention.
4. Validation. `validate-system.py` asserts the config schema has session keys and no date keys, and that the marker check precedes every decay branch (fixture-driven).

Exit: migration verified against a copy of the real `config.json`, validation check green, a `confirmed` fixture survives a dry-run decay pass untouched.

## Phase 2: Session-clock decay, relevance check, archive hygiene

Goal: the replacement mechanics, with the old ones deleted. Effort: medium; the bulk of the plan.

1. `propose.py`. Proposal decay and archive compare `current_session - reinforced_session` (falling back to `created_session`) against the session thresholds. Instinct decay ticks on sessions since `last_seen_session`. All date-based decay code is deleted.
2. `analyze.py`. Relevance pass: an instinct whose `file_scope` glob matches no files, or whose target path no longer exists, archives with reason `irrelevant`. Reinforcement updates `last_seen_session`.
3. Archive reasons. Archived files record `decayed`, `irrelevant`, or `rejected` plus the session number and date. The archive is auditable; nothing disappears silently.
4. Soft cap. When pending proposals exceed `pending_proposal_soft_cap`, the existing SessionStart notice path nudges an oldest-first review. No auto-archive.
5. Tests. Fixtures cover: decay at threshold, no decay below it, confirmed skip, relevance archive, archive-reason recording, soft-cap nudge, dry-run parity. Dedicated test directory, temp filesystem only, no network.

Exit: dry-run against real `.claude/learning/` data shows expected behavior and only expected behavior, tests green, `git grep` finds no date-based decay code.

## Phase 3: Verification and ADR flip

Goal: judge on real sessions, then make it official. Effort: calendar time plus a review session.

1. Run one to two weeks of real sessions. Verify: counter accurate, no instinct or proposal lost without a recorded reason, confirmed items untouched, soft-cap nudge fires when expected.
2. Flip the staleness ADR to `Active`. Amend it in the same commit: Stop becomes SessionEnd as the session boundary, and the config migration is recorded as verified. Until Phase 4 lands, the ADR runs degraded as its technical-debt section already anticipates: session-clock plus relevance check, no contradiction reducer.
3. Update the fidelity plan: mark Phase 2 item 5 done, pointing here.

Exit: ADR Active, amendments recorded, fidelity plan updated, all validation checks green.

## Phase 4: Contradiction reducer (deferred, gated)

Goal: confidence falls on evidence, the third rule of the ADR. Blocked until transcript-parse correction capture ships (fidelity plan Phase 1, corrections ADR Active). Does not gate the ADR flip. Effort: small once unblocked.

1. Reducer. In `analyze.py`, a `correction` observation whose target matches an instinct's scope and contradicts its trigger reduces that instinct's confidence by a configured penalty. Provenance-aware: user-correction signal weighs heavier than self-correction.
2. Config. The penalty and the match rule live in `config.json`, not hardcoded.
3. Permanence holds. Confirmed instincts are exempt from the reducer like every other staleness mechanism. A contradicted confirmed instinct surfaces as a review nudge instead, since unconfirming is the developer's call.
4. Tests. Mock correction observations: matching contradiction reduces confidence, non-matching does not, confirmed instinct triggers nudge not reduction.

Exit: a synthetic contradiction reduces confidence end to end; the confirmed-instinct nudge fires; tests green.
