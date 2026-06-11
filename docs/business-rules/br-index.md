# Business Rule Index

Triage table for every Business Rule in `docs/business-rules/`. Consult it before loading any full business rule into context.

Read this first: scan for a row whose Domain matches what you are touching, check its Status, then read the Synopsis. Open the full rule only when it governs your change. A rule that depends on an architectural decision names it in Related ADRs; cross-check that ADR through `adr-index.md`.

Status values follow the BR policy: `Active` (in force) or `Archived` (retired). Domain is the business area the rule belongs to.

| BR | Status | Domain | Related ADRs | Synopsis |
|----|--------|--------|--------------|----------|
| _None yet._ | | | | |

## Maintenance

This index is generated content. Keep one row per business rule. When the `create-business-rule` skill writes a new rule, it appends a row here, copying Domain and Related ADRs from the rule's Metadata table. When a rule's status changes, update the Status cell in the same PR. Replace the placeholder row with the first real rule.
