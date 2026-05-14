# Architecture Decision Records

Every decision that shapes how the system is built lives here as a numbered markdown file. ADRs are not retrospectives; they are written at the moment of decision, while the context and the rejected alternatives are still fresh.

## When to write one

When introducing a new architectural pattern, a cross-cutting concern, or a third-party dependency. When choosing between two viable technologies. When deviating from an established convention in the codebase. If the decision could surprise a future reader six months from now, it earns an ADR.

## How to write one

Invoke the `adr-creation` skill — it walks you through the template at `../../.github/docs/adr-template.md` and validates against `../../.github/instructions/adr-pr-review.instructions.md`. Status defaults to `Active`; supersede an older ADR by setting its status to `Archived` and referencing the new one.

## Conventions

Filenames are zero-padded numbers: `0001-use-postgres.md`, `0002-adopt-htmx.md`. Numbers never get reused; archived ADRs stay in place with their status updated. Both Copilot and Claude auto-load `adr-template` and `adr-pr-review` rules when editing files in this directory.
