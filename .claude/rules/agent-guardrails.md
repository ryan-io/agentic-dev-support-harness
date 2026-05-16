---
paths: ["**"]
---


# Agent Guardrails

> **Full guidance:** `.github/docs/agent-guardrails-guide.md`

Behavioral constraints for any agent in this repository: Claude Code, Copilot, or subagents. This file does not duplicate rules defined elsewhere. It establishes the boundaries those rules assume.

## Ask, Do Not Guess

When an agent is uncertain about intent, scope, implementation approach, or the correct answer, it must ask the developer. Do not infer, assume, or fabricate. A wrong guess costs more than a clarifying question. This applies to code generation, architectural decisions, business logic interpretation, and any situation where the agent is not confident in the outcome.

## Commit Workflow

Use conventional commit prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `style`, `perf`, `build`. Subject line is imperative, present tense, max 72 characters. Body wraps at 80 characters. Scope is optional but encouraged when confined to a single module.

## Architecture Preservation

The following directory structure is load-bearing and must not be reorganized without an ADR:

- `.github/instructions/` and `.claude/rules/`: instruction files (source and mirror)
- `.github/skills/`: on-demand skill definitions
- `.github/docs/`: templates, reference documents, and companion guides
- `.github/scripts/`: automation scripts including the sync pipeline
- `docs/adr/`: architecture decision records
- `docs/business-rules/`: business rule definitions
- `.claude/learning/`: continuous-learning pipeline data

## Instruction File Integrity

Agents must not directly edit files in `.github/instructions/` or `.claude/rules/` without explicit developer approval. Use the continuous-learning pipeline to propose changes.

## Detected Workflows

- **ADR creation**: `adr-creation` skill + `.github/docs/adr-template.md`
- **Business rule creation**: `create-business-rule` skill + `.github/docs/br-template.md`
- **System review**: `system-review` skill
- **Convention discovery**: `convention-discovery` skill
- **Continuous learning**: `continuous-learning` skill
- **Project setup**: `project-setup` skill
- **Session continuity**: `observe.py` writes session deltas on session end
