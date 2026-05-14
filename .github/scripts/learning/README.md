# Continuous Learning Pipeline

A three-stage observer that watches how the agent actually works in this repository and surfaces patterns as concrete proposals to update the instruction files. Nothing here ever edits an instruction file directly — every change still goes through a human via the `continuous-learning` skill.

## Stages

`observe.py` runs from the hooks in `../../hooks/observe.json` on every PreToolUse, PostToolUse, and Stop event. It appends a JSON line per call to `.claude/learning/observations.jsonl` capturing the tool, target, and outcome.

`analyze.py` reads the observation log and aggregates recurring shapes into "instincts" — short markdown files in `.claude/learning/instincts/` with a confidence score and an example set. Runs after enough observations accumulate (default 20, configurable in `.claude/learning/config.json`).

`propose.py` promotes instincts that clear the confidence threshold (default 0.7) into "proposals" — markdown files in `.claude/learning/proposals/` that name a specific instruction file and suggest a specific edit. Also applies staleness decay: proposals untouched for 30 days lose confidence, archived at 60.

## Review

The `continuous-learning` skill is the human-in-the-loop step. It lists pending proposals, shows the suggested edit, and applies or discards on confirmation. Session-start and session-end nudges fire when proposals are waiting; `../../workflows/learning-summary.yml` opens a weekly GitHub Issue summarizing them.

## Local-only data

Only `config.json` is checked in. Observations, instincts, and proposals are per-developer and gitignored — every developer's harness learns from their own session, not the team's aggregate. That's by design: instincts that reflect one engineer's mistakes shouldn't auto-propagate to everyone else.
