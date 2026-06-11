---
applyTo: "**"
---

# Pattern Fidelity
Match the project. Before introducing any pattern, abstraction, coding standard, library, or architectural approach, ground it in what this project already does. Prefer the project's established way over a generic best-practice from memory. `code-standards` governs how code is written; this file governs whether a pattern belongs here at all.

## Ground Before You Build
Check for precedent in this order, and stop at the first that answers:

1. Adopted patterns in `patterns.instructions.md` and the language-specific code standards.
2. Decisions and constraints, found through the triage indexes first: scan `docs/adr/adr-index.md` and `docs/business-rules/br-index.md` by status and context, then open only the full ADR or rule that governs the change. Do not load whole records from `docs/adr/` or `docs/business-rules/` before checking the index.
3. Neighboring code: how the surrounding module, package, or feature already solves the same shape of problem.
4. Confirmed instincts and proposals from the learning pipeline (`.claude/learning/`).

If precedent exists, follow it. Do not refactor toward a different style just because it is one you would reach for by default.

## When No Precedent Exists
Do not silently invent. Surface the gap: state that no project precedent was found, name the options, recommend one, and get the developer's confirmation before adding it. This is the `agent-guardrails` "Ask, Do Not Guess" rule applied to design choices. A new pattern adopted on a hunch becomes the precedent everyone copies next.

A new architectural pattern, cross-cutting concern, or third-party dependency requires an ADR (see `agent-guardrails`). Propose the ADR; do not assume it.

## Resist Generic Solutions
The failure mode is reaching for a textbook abstraction the project never asked for: a generic repository layer over a codebase that queries directly, an event bus where a function call suffices, a config framework for three constants, premature interfaces with one implementation. Industry-standard is not the same as right-for-here. Solve the problem the project actually has, at the scale it actually has it.

Match the domain's vocabulary too. Name types and functions after the project's terms, not generic ones (`Invoice`, not `DataRecord`). Mirror the existing layering, error-handling, and dependency style rather than importing a foreign one.

## How Patterns Become Precedent
This rule is the proactive front end of the harness's learning loop. Confirmed patterns get captured, not left implicit:

- `convention-discovery` mines git history into instruction-file rules.
- The learning pipeline (`observe` -> `analyze` -> `propose`) surfaces recurring choices as proposals a developer reviews via `continuous-learning`.
- A deliberate, reusable decision earns an ADR or a `patterns.instructions.md` entry.

When the developer confirms a new pattern, propose codifying it through one of these so the next agent inherits it as precedent rather than rediscovering or contradicting it.

## Scope
Applies to design and implementation choices across all files: source, tests, docs, configuration. It does not forbid new patterns; it forbids introducing them without grounding or confirmation. Greenfield work with no precedent is expected, that is exactly when the confirm-first step matters most.
