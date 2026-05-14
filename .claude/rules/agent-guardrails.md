---
paths: ["**"]
---


# Agent Guardrails

Behavioral constraints for any agent operating in this repository: Claude Code, Copilot, or subagents spawned during a session. This file does not duplicate rules defined elsewhere. It establishes the boundaries those rules assume.

## Commit Workflow

Use conventional commit prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `style`, `perf`, `build`. Subject line is imperative, present tense, max 72 characters. Body wraps at 80 characters. Scope is optional but encouraged when the change is confined to a single module or directory (e.g., `fix(adr): correct status field validation`).

Do not amend or force-push commits that have already been pushed to a shared branch. Keep changes aligned with the existing pull-request and review flow described in `pr-review.instructions.md`.

## Architecture Preservation

The following directory structure is load-bearing and must not be reorganized without an ADR:

- `.github/instructions/` and `.claude/rules/`: instruction files (source and mirror)
- `.github/skills/`: on-demand skill definitions
- `.github/docs/`: templates and reference documents
- `.github/scripts/`: automation scripts including the sync pipeline
- `docs/adr/`: architecture decision records
- `docs/business-rules/`: business rule definitions
- `.claude/learning/`: continuous-learning pipeline data

Preserve the current module organization. Moving, renaming, or merging these directories changes the contract that CLAUDE.md, the sync script, and the continuous-learning pipeline depend on. If a structural change is warranted, write an ADR first.

## Instruction File Integrity

Agents must not directly edit files in `.github/instructions/` or `.claude/rules/` without explicit developer approval. The sanctioned path for evolving instruction files is the continuous-learning pipeline: `observe.py` records patterns, `analyze.py` detects convergence, `propose.py` surfaces proposals for human review via the `continuous-learning` skill.

When an agent identifies a convention gap or a rule that should change, it should record the observation rather than act on it. Create a learning observation or flag it in a PR comment. Do not self-modify the rules you operate under.

## Detected Workflows

These are the project's sanctioned workflows. Agents should use the corresponding skill or template rather than improvising an alternative.

- **ADR creation**: Use the `adr-creation` skill and the template at `.github/docs/adr-template.md`.
- **Business rule creation**: Use the `create-business-rule` skill and the template at `.github/docs/br-template.md`.
- **System review**: Use the `system-review` skill for cross-cutting audits.
- **Convention discovery**: Use the `convention-discovery` skill to surface implicit patterns.
- **Continuous learning**: Use the `continuous-learning` skill to review and apply pending proposals.
- **Project setup**: Use the `project-setup` skill when tailoring the template for a new project.

## Regeneration Policy

Regenerate or update this file when repository conventions materially change: new instruction files are added, skills are created or retired, or the directory structure evolves. The continuous-learning pipeline's proposal mechanism is the preferred trigger. Review this file at least once per quarter to confirm it still reflects the project's actual constraints.
