# ADR-PROJECT: Add a Research Instruction File

---

## Metadata

| Field       | Value                |
|-------------|----------------------|
| Status      | Active               |
| Date        | 2026-05-14           |
| Authors     | @ryan-io             |

---

## Context

The harness ships instruction files for code standards, PR review, UI, UX, prose voice, ADRs, business rules, and design patterns. None of them govern how an agent gathers context or cites sources. That is a real gap: work in this repository is documentation-heavy and source-sensitive, and without a rule the sourcing behavior drifts. An agent might lean on stale memory, cite a secondary summary instead of the primary doc, or browse the web for something the repository already answers.

Any fix has to fit the harness model. Every instruction file must work across three surfaces (Copilot PR review, Copilot chat, Claude Code chat), stay under 4,000 characters, carry `applyTo` frontmatter, and sync to `.claude/rules/`. A rule kept in a non-standard location, or written as a skill, would not load automatically and would break that model.

---

## Decision

Add `research.instructions.md` as a universal instruction file with `applyTo: "**"`, a sibling of `writing-voice`. `writing-voice` governs how findings are written; this file governs how they are gathered and supported. The content is adapted from an external research playbook: three Defaults (prefer primary documentation and direct source links, date facts that can change, keep an evidence trail per conclusion) and a three-step Suggested Flow (inspect local code and docs first, browse only for unstable or external facts, summarize with file paths and links).

The playbook's "Repo Signals" block was repo-specific generated metadata. It was replaced with a CUSTOMIZE-marked placeholder for the `project-setup` skill to fill, because the harness is a stack-agnostic template. A standard instruction file was chosen over a one-off document because the rule is cross-cutting and always applicable, which is exactly the shape an instruction file is for. The tradeoff is consistency and correctness of sourcing against a small, fixed increase in always-loaded context: 1,177 characters.

---

## Consequences

Agents now have an explicit, discoverable sourcing standard that loads on every file and pairs with `writing-voice`. The cost is one more file in the always-loaded set. Adding the row to `system-index.md` pushed it past its 4,000-character limit, so a redundant cross-reference line, already covered by the Entry Points table, was removed to make room. Technical debt: the Repo Signals block is a placeholder with no project-specific value until `project-setup` fills it.

---

## Enforcement / Guidance

`research.instructions.md` syncs to `.claude/rules/research.md` through `sync-claude-rules.py`, and `validate-system.py` checks its frontmatter, size, sync state, and hub reference. The pre-commit hook runs both, so a broken or unsynced state blocks the commit. The `project-setup` skill must fill the Repo Signals CUSTOMIZE block during onboarding. New sourcing rules extend this file rather than creating parallel ones.
