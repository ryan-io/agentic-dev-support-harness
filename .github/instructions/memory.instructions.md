---
applyTo: "**"
---

# Project Memory

Durable, curated facts about this project. This file loads on turn one for every session so an agent starts oriented instead of rediscovering the codebase. The `continuous-learning` skill maintains it by promoting entries from the local session log under developer review. Do not hand-edit it mid-task; propose changes through that skill. Keep the whole file under 4,000 characters. When it fills, prune the least useful entry rather than letting it overflow.

## Orientation

This is the agentic-dev-support-harness: a template repository giving Copilot and Claude Code a shared governance layer of instruction files, skills, ADR and business-rule workflows, and a continuous-learning pipeline. Source of truth lives under `.github/`; `CLAUDE.md` and `.claude/rules/` are generated mirrors kept consistent by `sync-claude-rules.py`.

## Key file map

Learning pipeline: `.github/scripts/learning/` (`observe.py` hooks, `analyze.py` detectors plus relevance and contradiction passes, `propose.py` promotion and decay, `session_clock.py` shared primitives, `tests/`). Validation: `.github/scripts/validate-system.py`, run by the pre-commit hook. Learning data: `.claude/learning/` (`config.json` and `proposals/` tracked; observations, instincts, session-delta, session-counter local). Decisions: `docs/adr/`; phased plans: `docs/process/`.

## Confirmed conventions

Pipeline Python is stdlib-only and fails closed: hooks always exit 0 and degrade quietly on bad input. Tests live in `.github/scripts/learning/tests/`, temp filesystem only. Edit instruction sources under `.github/instructions/`, never the `.claude/rules/` mirror, then run the sync script.

## Decisions and constraints

Staleness is evidence-based and session-clock driven; wall-clock decay is removed and confirmed knowledge (`confirmed: true`) never decays. Corrections are captured by parsing the SessionEnd transcript: derived fields only, raw transcript text never enters the observation log. SessionEnd, not Stop, is the session boundary. Instruction files are hard-capped at 4,000 characters. Both learning ADRs (staleness, correction capture) were implemented and amended 2026-06-05.

## Open threads

Verification windows open since 2026-06-05: one week of sessions with zero hook failures, and developer review of the first correction batches before the seed confidence is trusted. Fidelity-plan Phase 5 evaluation gate is due four to six weeks after Phase 2 shipped (baseline recorded in the plan).
