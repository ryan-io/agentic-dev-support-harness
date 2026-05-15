# Business Rules

The constraints the system must respect because the business says so, not because of an architectural choice. Tax thresholds, eligibility criteria, regulatory deadlines, pricing tiers. Things that change when the business changes, not when the code does.

## When to write one

When a piece of logic exists only because a stakeholder said it must. When the same constraint shows up in multiple places and would benefit from a single source of truth. When a future engineer would otherwise hard-code the rule and forget where it came from.

## How to write one

Invoke the `create-business-rule` skill, it uses the template at `../../.github/docs/br-template.md` and validates against `../../.github/instructions/br-review.instructions.md`. Each rule names its owner (the business stakeholder), its effective date, and the system surfaces it touches.

## Difference from ADRs

ADRs are decisions the engineering team owns and revisits when technology changes. Business rules are decisions the business owns and revisits when policy changes. If you would call the CTO to discuss it, it is an ADR; if you would call the head of finance, it is a business rule.

## Related

- [ADRs](../adr/README.md): the engineering-owned counterpart to business rules.
- [Skills](../../.github/skills/README.md): the `create-business-rule` skill.
- [Reference docs](../../.github/docs/README.md): the business-rule template and validation rules.
