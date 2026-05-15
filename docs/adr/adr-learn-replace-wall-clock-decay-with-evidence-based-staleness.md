# ADR-LEARN: Replace Wall-Clock Decay with Evidence-Based Staleness

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-04 |
| Authors | @ryan-io   |

Amended 2026-06-05: implemented per `docs/process/2026-06-05-evidence-based-staleness-plan.md`. The session boundary is the SessionEnd hook, not Stop (Stop fires after every assistant turn; `observe.py` already treats SessionEnd as the session boundary). The config migration was verified against the live `config.json` and existing instincts and proposals were backfilled with the current session count.

---

## Context

The learning pipeline expires its own output on a wall-clock timer. Proposals untouched for 30 days lose confidence and archive at 60. Instincts decay 0.05 per month. The settings live in `.claude/learning/config.json` and the passes run in `propose.py` and `analyze.py`.

That clock assumes team cadence: steady activity and a queue that rots if nobody tends it. The harness's primary users are solo developers and small teams who work in bursts. A solo developer who steps away for six weeks returns to find valid instincts weakened and pending proposals archived. No evidence against them arrived; time passed. Elapsed time is the staleness proxy, and for bursty cadence it is a bad one.

Doing nothing means the pipeline silently discards its highest-value output for exactly the users the harness targets. The failure is invisible: an archived proposal never reaches review, so the developer never learns a pattern was detected.

Two quality attributes conflict. Queue hygiene wants aggressive expiry so review stays short and instincts reflect current behavior. Signal preservation wants nothing developer-relevant discarded without a human seeing it. Wall-clock decay buys hygiene by sacrificing preservation. The replacement must keep hygiene without the sacrifice.

A third constraint comes from the project-memory ADR: developer-confirmed knowledge (applied proposals, curated memory entries, the planned confirmed-instinct store) is the system's durable layer. Any staleness mechanism that can erode confirmed knowledge contradicts that design.

---

## Decision

We will replace wall-clock decay with three rules: a session-clock timer, evidence-based confidence reduction, and a permanence guarantee for confirmed knowledge.

The only timer counts sessions worked, not days elapsed. A proposal decays after N sessions without reinforcement (default 15, in `config.json`); an instinct's decay ticks on sessions observed since `last_seen`. A repository nobody opens is frozen, so dormancy costs nothing. Genuinely abandoned patterns still fade, because continued work without reinforcement is itself evidence of abandonment.

Confidence falls only on evidence. A contradicting observation (the developer does the opposite of what the instinct claims, or a correction fires against the rule it suggests) reduces confidence. A failed relevance check (the instinct's target path no longer exists, or its glob matches no files) archives it. `analyze.py` gains the relevance pass; the contradiction signal arrives with the transcript-parse correction capture already planned.

Confirmed knowledge never decays. Applied proposals, curated memory entries, and confirmed instincts are exempt from every staleness mechanism. The system may forget its guesses; it never forgets the developer's decisions.

This trades the simplicity of date arithmetic for a model where staleness means "the evidence changed," which matches what staleness actually is.

---

## Other Considerations

**Keep wall-clock decay (status quo).** Simple, already implemented, and adequate for teams with steady activity. It is the problem statement for solo cadence: it conflates elapsed time with weakened evidence and silently discards signal. Rejected as the default; the session-clock subsumes it.

**Session-clock decay alone.** The smallest change: swap the date comparison for a session-count comparison. It fixes dormancy but still expires proposals no human reviewed, keeping the silent-discard failure at a slower rate. Adopted as a component, not the whole answer.

**Contradiction-based invalidation alone.** No timer at all; confidence is monotonic until contradicted. Strongest preservation, but zombie instincts about deleted files and dead conventions persist until something happens to contradict them, which for dead code is never. The relevance check covers that gap, but without any timer, weak instincts that were never wrong and never useful accumulate. Adopted as a component, paired with the session-clock.

**No expiry, explicit queue states.** Proposals never expire; they hold states (`pending`, `snoozed`, `rejected`, `applied`) and only the developer moves them. Honest about who reviews, but it trades silent expiry for unbounded queue growth, and a dreaded queue is reviewed no more often than an expiring one. Not adopted; the soft-cap nudge below captures its useful part.

**Burst-aware adaptive decay rates.** Scale the decay rate by observed activity density. More machinery to approximate what the session-clock gives directly. Rejected for complexity.

---

## Consequences

**Pros**

- Dormant repositories lose nothing. Solo developers and small teams keep their full signal across gaps.
- Nothing developer-relevant is discarded on a timer alone; archive requires rejection, contradiction, or irrelevance.
- Confirmed knowledge is structurally permanent, aligning the pipeline with the project-memory ADR's durable layer.
- Hygiene survives: abandoned patterns fade against the session-clock, dead targets archive on the relevance check.

**Cons**

- Session counting requires a reliable session boundary. The SessionEnd hook provides it under Claude Code; a session that never fires SessionEnd (crash, kill) under-counts. Acceptable: under-counting delays decay, it never accelerates loss.
- The pending queue can grow larger than under wall-clock expiry. A soft cap (default 10 pending proposals) triggers an oldest-first review nudge instead of auto-archiving.
- Contradiction detection depends on the transcript-parse correction capture (separate ADR, Proposed). Until it ships, the only reducers are the relevance check and explicit rejection.
- Three rules replace one timer. `analyze.py`, `propose.py`, and `config.json` all change, and the config schema needs migration for existing installs.

**Technical debt**

The contradiction reducer is specified here but cannot be built before the correction capture ships. Until then this ADR runs degraded: session-clock plus relevance check only. The config migration (`proposal_decay_days` to `proposal_decay_sessions`, removal of `instinct_decay_per_month`) must handle existing `config.json` files rather than break them.

---

## Enforcement / Guidance

- `config.json` replaces `staleness.proposal_decay_days` and `staleness.proposal_archive_days` with `staleness.proposal_decay_sessions` and `staleness.proposal_archive_sessions`, and replaces `instinct_decay_per_month` with `instinct_decay_per_sessions`. `propose.py` and `analyze.py` must read only the session-based keys; date-based decay code is removed, not flagged off.
- Confirmed knowledge is exempt structurally, not by convention: applied proposals, curated memory entries, and confirmed instincts carry a `confirmed` marker that every staleness pass checks first and skips.
- The relevance check runs in `analyze.py` on each pass: an instinct whose target path is gone or whose glob matches nothing is archived with reason `irrelevant`, distinct from `decayed` and `rejected`, so the archive is auditable.
- Archive reasons are recorded on the archived file. A proposal must never disappear without a recorded reason a developer can read.
- The pending-proposal soft cap and nudge threshold live in `config.json` (`thresholds.pending_proposal_soft_cap`, default 10).
- Implemented 2026-06-05: session clock (`session_clock.py`, counter ticked by `observe.py` on SessionEnd), relevance check in `analyze.py`, config migration verified. The contradiction reducer lands with the correction-capture ADR and does not gate this one.

---

## References

- ADR-LEARN: Establish Shared Project Memory, `docs/adr/adr-learn-establish-shared-project-memory.md`. Source of the durable-layer boundary the permanence guarantee serves.
- ADR-LEARN: Capture User Corrections via Transcript Parse, `docs/adr/adr-learn-capture-corrections-via-transcript-parse.md`. Supplies the contradiction signal this decision consumes.
- Learning Pipeline Investment Plan, `docs/process/2026-06-04-learning-signal-fidelity-plan.md`. Phase 2 carries the implementation.
- Evidence-Based Staleness Implementation Plan, `docs/process/2026-06-05-evidence-based-staleness-plan.md`. The phased implementation of this decision.
