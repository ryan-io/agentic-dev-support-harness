# Agent Guardrails Guide

Companion to `agent-guardrails.instructions.md`. Read this when making architectural changes, editing instruction files, or reviewing the learning pipeline.

## Architecture Preservation: Rationale

Moving, renaming, or merging the load-bearing directories changes the contract that CLAUDE.md, the sync script, and the continuous-learning pipeline depend on. If a structural change is warranted, write an ADR first. The sync script expects `.github/instructions/` as source and `.claude/rules/` as destination. The learning pipeline reads from `.claude/learning/`. Skills resolve by directory name under `.github/skills/`.

## Instruction File Integrity: Pipeline Details

The sanctioned path for evolving instruction files is the continuous-learning pipeline: `observe.py` records patterns, `analyze.py` detects convergence, `propose.py` surfaces proposals for human review via the `continuous-learning` skill.

When an agent identifies a convention gap or a rule that should change, it should record the observation rather than act on it. Create a learning observation or flag it in a PR comment. Do not self-modify the rules you operate under.

## Commit Workflow: Shared Branch Rules

Do not amend or force-push commits that have already been pushed to a shared branch. Keep changes aligned with the existing pull-request and review flow described in `pr-review.instructions.md`.

## Detected Workflows: Full Descriptions

- **ADR creation**: Use the `adr-creation` skill and the template at `.github/docs/adr-template.md`.
- **Business rule creation**: Use the `create-business-rule` skill and the template at `.github/docs/br-template.md`.
- **System review**: Use the `system-review` skill for cross-cutting audits.
- **Convention discovery**: Use the `convention-discovery` skill to surface implicit patterns from git history.
- **Continuous learning**: Use the `continuous-learning` skill to review and apply pending proposals.
- **Project setup**: Use the `project-setup` skill when tailoring the template for a new stack.
- **Session continuity**: On session end, `observe.py` writes a session delta and tracks instruction file changes. The next session's start notice includes what changed.

## Regeneration Policy

Regenerate or update `agent-guardrails.instructions.md` when repository conventions materially change: new instruction files are added, skills are created or retired, or the directory structure evolves. The continuous-learning pipeline's proposal mechanism is the preferred trigger. Review the file at least once per quarter to confirm it still reflects the project's actual constraints.
