---
paths: ["docs/adr/**"]
---


# ADR Review Policy
Full validation rules for Architecture Decision Records. Applies to all files under `docs/adr/`.

## File Naming
- Filename must be lowercase: `adr-project-[kebab-case-title].md` (placed in `docs/adr/`)
- The heading inside the file uses uppercase: `# ADR-PROJECT: [Short Title]`

## Required Sections
Every ADR must contain all of the following `##` sections.
Flag any section that is missing, empty, or contains only placeholder text (bracket-wrapped `[...]`).

- `## Metadata` — Must include a table with: Status (default: Active), Date, Authors. Status must be `Active` or `Archived`. Reject if any field is missing or empty.
- `## Context` — Must describe the problem space, constraints, and relevant quality attributes. Reject if vague or generic.
- `## Decision` — Must state the decision in active voice with explicit rationale referencing quality attribute tradeoffs.
- `## Consequences` — Detail pros, cons, and any technical debt introduced. If none, write "None".
- `## Enforcement / Guidance` — Must describe a concrete, actionable enforcement mechanism. Vague statements like "follow best practices" are not acceptable.

## Policy
If an ADR is no longer applicable, change its status to `Archived` via PR. Deleting ADRs is not allowed. See `pr-review.instructions.md` for PR review process and comment format.