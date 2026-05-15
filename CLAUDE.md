# Project Instructions

This file is the agent entry point. It is loaded automatically by Copilot (as `copilot-instructions.md`) and synced to `CLAUDE.md` for Claude Code. Both files are identical, `.github/copilot-instructions.md` is the source of truth.

## Project Overview
<!-- CUSTOMIZE: Fill in stack, architecture, testing framework, etc. -->
- Architecture Decision Records (ADRs) are stored in `docs/adr/`.
- Business Rules are stored in `docs/business-rules/`.
- Design patterns adopted by the project are documented in `patterns.instructions.md`.

## Instruction Files
Instruction files are loaded automatically based on file scope. All files are in `.github/instructions/`. Claude Code uses synced copies in `.claude/rules/` (managed by the sync script).

- `code-standards.instructions.md`: Universal code standards (all files)
- `pr-review.instructions.md`: PR review format and process (all files)
- `patterns.instructions.md`: Adopted design pattern registry (all files)
- `user-interface.instructions.md`: UI standards (all files)
- `user-experience.instructions.md`: UX standards (all files)
- `writing-voice.instructions.md`: Prose voice for human-readable deliverables (all files)
- `research.instructions.md`: Research and sourcing practice (all files)
- `agent-guardrails.instructions.md`: Agent behavioral constraints (all files)
- `testing.instructions.md`: Testing standards (all files)
- `adr-template.instructions.md`: ADR creation policy (`docs/adr/**`)
- `adr-pr-review.instructions.md`: ADR review/validation (`docs/adr/**`)
- `br-review.instructions.md`: Business rule review/validation (`docs/business-rules/**`)

Stack-specific files (loaded by file extension match):
<!-- CUSTOMIZE: Add or remove lines below to match the stacks used in this project -->
- `{language}-code-standards.instructions.md`: Language-specific standards
<!-- END CUSTOMIZE -->

## On-Demand (not preloaded)
- Templates: `.github/docs/adr-template.md`, `.github/docs/br-template.md`
- Skills: `.github/skills/adr-creation/SKILL.md`, `.github/skills/create-business-rule/SKILL.md`, `.github/skills/system-review/SKILL.md`, `.github/skills/project-setup/SKILL.md`, `.github/skills/convention-discovery/SKILL.md`, `.github/skills/continuous-learning/SKILL.md`
- Setup: `setup.bat` / `setup.sh` initializes a new repo from this template (run first, then use `project-setup` skill to tailor)
- Reference: `.github/docs/system-index.md`

## Key Policies
- **Code standards**: Universal standards apply to all files. Stack-specific files extend them. See `code-standards.instructions.md`.
- **PR review**: Use Severity/Category comment format. See `pr-review.instructions.md`.
- **ADRs**: Use the template in `.github/docs/adr-template.md`. Status defaults to `Active`. See `adr-pr-review.instructions.md` for validation rules.
- **Business rules**: Use the template in `.github/docs/br-template.md`. See `br-review.instructions.md` for validation rules.
- **Commit messages**: Conventional commits, imperative, present tense. See `agent-guardrails.instructions.md`.
- **ADR required**: When introducing new architectural patterns, cross-cutting concerns, or third-party dependencies.

## Continuous Learning
The project includes an automated learning pipeline that observes developer sessions and surfaces patterns as proposals for instruction file updates. No action is needed to enable it, hooks in `.github/hooks/observe.json` activate automatically.

- **Pipeline**: `observe.py` (record) → `analyze.py` (detect patterns) → `propose.py` (promote high-confidence patterns)
- **Data**: `.claude/learning/` holds observations, instincts, proposals, and config (