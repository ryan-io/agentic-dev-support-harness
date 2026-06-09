# Project Instructions

This file is the agent entry point. It is loaded automatically by Copilot (as `copilot-instructions.md`) and synced to `CLAUDE.md` for Claude Code. Both files are identical, `.github/copilot-instructions.md` is the source of truth.

## Project Overview
- Architecture Decision Records (ADRs) are stored in `docs/adr/`.
- Business Rules are stored in `docs/business-rules/`.
- Design patterns adopted by the project are documented in `patterns.instructions.md` (deprecated placeholder; reinstated and auto-loaded once patterns are documented).

## Instruction Files
Auto-loaded by file scope. Source: `.github/instructions/`, mirror: `.claude/rules/` (managed by sync script).

**Universal (all files):** code-standards, writing-voice, research, agent-guardrails, pattern-fidelity, memory
**Code files:** testing, pr-review
**UI files:** user-interface, user-experience
**ADR (`docs/adr/**`):** adr-template, adr-pr-review
**Business rules (`docs/business-rules/**`):** br-review
**Stack-specific:** csharp-code-standards (`*.cs`), lua-code-standards (`*.lua`)

Full file map and constraints: `.github/docs/system-index.md`

## On-Demand (not preloaded)
- Templates: `.github/docs/adr-template.md`, `.github/docs/br-template.md`
- Skills: `adr-creation`, `create-business-rule`, `system-review`, `project-setup`, `convention-discovery`, `continuous-learning`, `behavioral-requirements`, `volatility-decomposition`, `architecture-layering`, `architecture-design-pipeline`, `implementation`, `write-unit-tests`, `sequence-diagram` (all in `.github/skills/{name}/SKILL.md`)
- Reference: `.github/docs/system-index.md`

## Key Policies
- **Code standards**: Universal standards apply to all files. Stack-specific files extend them. See `code-standards.instructions.md`.
- **PR review**: Use Severity/Category comment format. See `pr-review.instructions.md`.
- **ADRs**: Use the template in `.github/docs/adr-template.md`. Status defaults to `Active`. See `adr-pr-review.instructions.md` for validation rules.
- **Business rules**: Use the template in `.github/docs/br-template.md`. See `br-review.instructions.md` for validation rules.
- **Commit messages**: Conventional commits, imperative, present tense. See `agent-guardrails.instructions.md`.
- **ADR required**: When introducing new architectural patterns, cross-cutting concerns, or third-party dependencies.

## Continuous Learning
Automated learning pipeline; details in `agent-guardrails.instructions.md`. Run `continuous-learning` skill to review pending proposals.
