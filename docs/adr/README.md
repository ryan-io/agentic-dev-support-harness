# Architecture Decision Records

Every decision that shapes how the system is built lives here as a markdown file named `adr-{prefix}-{kebab-title}.md`. ADRs are not retrospectives; they are written at the moment of decision, while the context and the rejected alternatives are still fresh.

## When to write one

When introducing a new architectural pattern, a cross-cutting concern, or a third-party dependency. When choosing between two viable technologies. When deviating from an established convention in the codebase. If the decision could surprise a future reader six months from now, it earns an ADR.

## How to write one

Invoke the `adr-creation` skill, it walks you through the template at `../../.github/docs/adr-template.md` and validates against `../../.github/instructions/adr-pr-review.instructions.md`. Status defaults to `Active`. Supersede an older ADR by setting its status to `Archived` and referencing the new one.

## Conventions

Filenames follow `adr-{prefix}-{kebab-case-title}.md`, where the prefix groups a subsystem or concern (`design`, `learn`, `project`, `rag`, `scaffold`): `adr-scaffold-introduce-ah-ide-cli.md`. Archived ADRs stay in place with their status updated. Both Copilot and Claude auto-load `adr-template` and `adr-pr-review` rules when editing files in this directory.

## Related

- [Business rules](../business-rules/README.md): the business-owned counterpart to ADRs.
- [Design artifacts](../design/README.md): pipeline outputs that promote into ADRs.
- [Skills](../../.github/skills/README.md): the `adr-creation` skill.
- [Reference docs](../../.github/docs/README.md): the ADR template and validation rules.
