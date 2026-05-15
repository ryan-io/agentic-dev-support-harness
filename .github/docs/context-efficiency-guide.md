# Context Efficiency Guide

Companion to the context efficiency summary in the root `README.md`. The harness assumes agent context is scarce and budgets it deliberately. This guide records how.

## Scoped loading

Instruction files carry frontmatter (`applyTo` for Copilot, `paths` for Claude) and load only when the agent touches a matching file. Editing a `.cs` file loads the universal rules plus `csharp-code-standards` and `testing`; it does not load the ADR template, the business-rule review policy, or the Lua standards. The full scope map is in `.github/docs/system-index.md`.

## Hard size cap

Every instruction file is capped at 4,000 characters, enforced by `validate-system.py` and CI. The cap forces rules to stay terse and keeps the always-loaded set small even as the file count grows. The cap applies only to `.github/instructions/` and `.claude/rules/`; other markdown (docs, guides, templates, skills, READMEs) is exempt.

## Two-tier documentation

Each dense topic splits into a lean auto-loaded rule and a companion guide in `.github/docs/` (e.g. `pr-review.instructions.md` and `pr-review-guide.md`). The rule states the policy; the guide carries the rationale and examples and is read only when the agent or developer asks for depth.

## On-demand skills

Skills are never preloaded. The agent reads a `SKILL.md` only when it decides to run that skill, so eleven multi-page procedures cost zero tokens until one is invoked.

## Memory instead of rediscovery

The project-memory digest trades a one-time 4,000-character load for the repeated cost of re-exploring the repository at the start of every session. See `learning-system-guide.md` for how it is curated.

## Cheap observation

The pipeline itself stays out of the context window. Hooks run as external Python with a 5-second timeout and never block the agent. The observation log rotates to an archive at 1,000 entries, analysis runs incrementally from a marker rather than re-scanning the full log, and `propose.py` runs only when analysis produced new instincts.
