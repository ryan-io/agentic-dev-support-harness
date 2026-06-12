# Continuous Learning Pipeline

A three-stage observer that watches how the agent actually works in this repository and surfaces patterns as concrete proposals to update the instruction files. Nothing here ever edits an instruction file directly, every change still goes through a human via the `continuous-learning` skill.

## Stages

`observe.py` runs from the hooks registered in `.claude/settings.json` on every PostToolUse, SessionStart, SessionEnd, and UserPromptSubmit event. Tool calls are recorded on PostToolUse only, so each call lands exactly once, with its outcome. The hook command picks `python3` if present, else `python`, so it runs under `sh` on macOS/Linux and Git Bash on Windows. A Windows machine without Git Bash skips the hook and records nothing, which is acceptable because the hooks are designed never to block. It appends a JSON line per call to `.claude/learning/observations.jsonl` capturing the tool, target, and outcome. When the observations file exceeds 1,000 entries it is rotated to `.claude/learning/observations.archive/` with a timestamp suffix. On SessionEnd it ticks the session counter, parses the transcript for corrections (see below), and appends a one-block summary of the session (files touched, domains, rules consulted) to `.claude/learning/session-delta.md`, a local log that accumulates across sessions and feeds both the session-start orientation notice and the memory curation step below.

`analyze.py` reads the observation log and aggregates recurring shapes into "instincts", short markdown files in `.claude/learning/instincts/` with a confidence score and an example set. Runs after enough observations accumulate (default 20, configurable in `.claude/learning/config.json`). Reinforcement merges new evidence into the existing instinct, additively and capped, so a long-lived instinct keeps its history. In incremental mode (default), only observations recorded after the most recent analysis marker are processed, avoiding a full-file scan on every run.

`propose.py` promotes instincts that clear the confidence threshold (default 0.7) into "proposals", markdown files in `.claude/learning/proposals/` that name a specific instruction file and suggest a specific edit. `analyze.py` only invokes `propose.py` when new instincts were created or updated, skipping the scan when no patterns were detected. When an instinct with a pending proposal gathers new evidence, the proposal is stamped reinforced and its staleness clock restarts; archived proposals block immediate re-promotion, so nothing churns.

## Correction capture

On SessionEnd, `observe.py` batch-parses the session transcript Claude Code passes and records a `correction` observation for each user turn that rejects, contradicts, or redirects the agent's prior mutating action (see `adr-learn-capture-corrections-via-transcript-parse`). The classifier is conservative: only anchored trigger phrases in the head of a turn count, and an ambiguous turn is not a correction.

The `correction` observation carries derived fields only: `target` (repo-relative file or `general`), `change` (a templated description built from tool metadata), `category` (`negation`, `rejection`, or `redirect`), plus `provenance: user-correction`, the paired tool, and the file extension. Raw transcript text never reaches `observations.jsonl`; a fixture-driven `validate-system.py` check enforces this. Parsing fails closed: malformed or oversized (>10 MB) transcripts degrade quietly and the hook always exits zero.

A prompt that begins with `#correction` is the explicit developer signal: a `UserPromptSubmit` hook records a `correction` observation with `provenance: developer-flagged`, paired with the session's most recent mutating action. The prompt text itself is never recorded. Use it to flag a correction the transcript classifier would miss.

Corrections feed two consumers in `analyze.py`. The contradiction reducer: each correction whose target falls inside an instinct's `file_scope` reduces that instinct's confidence by `staleness.contradiction_penalty` (default 0.1), weighted by provenance (user corrections and developer flags count double an agent self-correction); confirmed instincts are never reduced, a contradicted confirmed instinct surfaces as a review nudge instead. And seeding: corrections aggregate into instincts that seed at `thresholds.correction_seed_confidence` (default 0.45), above the 0.30 frequency proxy, so a real correction promotes faster. Every instinct carries `provenance` (`user-correction`, `developer-flagged`, `self-correction`, or `frequency`); the values are never conflated.

`propose.py` applies a quality gate at promotion: an instinct whose headline is a pattern description rather than an imperative rule is held as an instinct, not promoted. Correction-derived instincts pass the gate carrying their derived change descriptions; the developer writes the actual rule text at review.

## Staleness model

Staleness is evidence-based, not wall-clock (see `adr-learn-replace-wall-clock-decay-with-evidence-based-staleness`). The only timer is a session clock: `observe.py` increments `.claude/learning/session-counter.json` once per SessionEnd, and `session_clock.py` provides the shared primitives. A dormant repository is frozen; only continued work without reinforcement decays anything.

Three mechanisms run against the clock. Proposals go stale after `proposal_decay_sessions` (default 15) and archive with reason `decayed` at `proposal_archive_sessions` (default 30). Instinct confidence drops `instinct_decay_per_sessions` (default 0.05) per full `instinct_decay_session_window` (default 15 sessions) without reinforcement, with one window of grace. A relevance pass in `analyze.py` archives instincts whose `file_scope` glob matches no real file, with reason `irrelevant`.

Confirmed knowledge never decays: any instinct or proposal carrying `confirmed: true` is skipped by every staleness pass, structurally. Archived files always record `archived_reason` (`decayed`, `irrelevant`, `rejected`, or `applied`), the session number, and the date, so nothing disappears silently. When pending proposals exceed `thresholds.pending_proposal_soft_cap` (default 10), the session-start notice nudges an oldest-first review instead of auto-archiving.

Existing installs migrate automatically: `analyze.py` and `propose.py` rewrite date-based config keys (`proposal_decay_days`, `proposal_archive_days`, `instinct_decay_per_month`) to the session-based keys on first run, and pre-clock instincts and proposals are stamped with the current session count so nothing decays retroactively.

## Review

The `continuous-learning` skill is the human-in-the-loop step. It lists pending proposals, shows the suggested edit, and applies or discards on confirmation. Once a proposal is applied or rejected, the next pipeline run moves it to `proposals.archive/` with the reason stamped, keeping the tracked directory to the live queue. Session-start and session-end nudges fire when proposals are waiting. A weekly GitHub Issue summarizing them is opened by `../../workflows/learning-summary.yml`.

## Project memory

The `continuous-learning` skill also curates `../../instructions/memory.instructions.md`, a committed, always-loaded digest of durable project facts. It promotes entries from the local session log under developer review, so a fresh clone or a new session starts oriented instead of re-reading the codebase. The raw session data stays local; only the curated digest is committed. The boundary and rationale are recorded in the project-memory ADR (`adr-learn-establish-shared-project-memory`).

## Local-only data

Observations, instincts, and session data are per-developer and gitignored. Each developer's harness learns from their own sessions, not the team's aggregate. That's by design: instincts that reflect one engineer's workflow shouldn't auto-propagate to everyone else.

Proposals and `config.json` are tracked (committed). Proposals are the curated, high-confidence output of the pipeline, meant for team review via the `continuous-learning` skill and the weekly `learning-summary.yml` GitHub Issue.

## Related

- [Scripts overview](../README.md): how this pipeline sits among the other automation.
- [Git hooks](../../hooks/README.md): the pre-commit hook (the learning hooks live in `.claude/settings.json`).
- [Instruction files](../../instructions/README.md): what approved proposals edit.
- [Skills](../../skills/README.md): the `continuous-learning` review step.
- [`.claude/`](../../../.claude/README.md): where the local learning data lives.
