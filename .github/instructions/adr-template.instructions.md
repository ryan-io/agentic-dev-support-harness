---
applyTo: "docs/adr/**"
---

# ADR Creation Policy
When creating a new ADR, copy `.github/docs/adr-template.md` and fill in all sections. See `adr-pr-review.instructions.md` for validation rules, required sections, and file naming conventions.

## Defaults
- Status: `Active`
- Date: today's date
- Authors: GitHub handle(s)
- Valid statuses: `Active`, `Proposed`, `Archived`

## Writing Context
Before drafting the Context section, identify the forces driving the decision:
1. What goes wrong if we do nothing?
2. What environment constraints exist that a textbook wouldn't assume?
3. Where do quality attributes conflict?

Every force should create tension that the Decision resolves and the Consequences acknowledge.

## Policy
- ADRs are permanent records and must never be deleted.
- If no longer applicable, change status to `Archived` via PR.
