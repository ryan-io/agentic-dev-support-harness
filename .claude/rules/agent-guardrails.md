---
paths: ["**"]
---

# Agent Guardrails

> **Full guidance:** `.github/docs/agent-guardrails-guide.md`

Behavioral constraints for any agent in this repository (Claude Code, Copilot, subagents). Establishes boundaries other rules assume.

## Ask, Do Not Guess

When uncertain about intent, scope, approach, or the correct answer, ask the developer. Do not infer, assume, or fabricate. A wrong guess costs more than a clarifying question.

## Commit Workflow

Conventional commit prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `style`, `perf`, `build`. Subject: imperative, present tense, max 72 chars. Body wraps at 80 chars. Scope optional but encouraged for single-module changes.

Agents never commit on their own. The developer runs every commit; at most, suggest a single commit subject (and a body if the change warrants one) and stop.

## Architecture Preservation

The following paths are load-bearing; do not reorganize without an ADR:

- `.github/instructions/` and `.claude/rules/`: instruction files (source and mirror)
- `.github/skills/`: on-demand skill definitions
- `.github/docs/`: templates, reference docs, companion guides
- `.github/scripts/`: automation scripts and sync pipeline
- `docs/adr/`: architecture decision records
- `docs/business-rules/`: business rule definitions
- `.claude/learning/`: continuous-learning pipeline data
- `.claude/settings.json`: Claude Code hook registration (continuous-learning pipeline)

## Instruction File Integrity

Agents must not edit files in `.github/instructions/` or `.claude/rules/` without explicit developer approval. Use the continuous-learning pipeline to propose changes.

## Continuous Learning Pipeline

The project observes developer sessions and surfaces patterns as proposals for instruction updates. The observation hooks live in `.claude/settings.json`, which Claude Code loads automatically. Copilot has no hook system, so the pipeline runs under Claude Code only.

- **Pipeline**: `observe.py` (record) → `analyze.py` (detect patterns) → `propose.py` (promote high-confidence patterns)
- **Data**: `.claude/learning/` holds observations, instincts, proposals, and config
- **Review**: Run `continuous-learning` skill to review and apply pending proposals
- **Automation**: Session nudges when proposals await review; weekly GitHub Issue summary via `learning-summary.yml`

## Detected Workflows

- **ADR creation**: `adr-creation` skill + `.github/docs/adr-template.md`
- **Business rule creation**: `create-business-rule` skill + `.github/docs/br-template.md`
- **System review**: `system-review` skill
- **Convention discovery**: `convention-discovery` skill
- **Project setup**: `project-setup` skill
- **Session continuity**: `observe.py` writes session deltas on session end

## Skill Authoring

Skills whose output is a saved file must include a step for revising an existing artifact. That step reads the saved file first, applies the requested change, preserves all other content and the skill's generation conventions, confirms before overwriting, and saves to the same path unless the user renames the artifact.
