---
paths: ["docs/business-rules/**"]
---


# Business Rule Review Policy
Validation rules for Business Rule documents. Applies to all files under `docs/business-rules/`.

## File Naming
- Filename must be lowercase: `br-{project}-{kebab-case-title}.md`
- The heading inside the file uses uppercase: `# BR-PROJECT: [Short Title]`
- Place in `docs/business-rules/`.

## Required Sections
Every Business Rule must contain all of the following `##` sections.
Flag any section that is missing, empty, or contains only placeholder text (bracket-wrapped `[...]`).

- `## Metadata` — Must include a table with: Status (default: Active), Date, Authors, Domain, Related ADRs. Reject if any field is missing or empty.
- `## Description` — Plain language statement of the rule. Must be specific and unambiguous. One rule per document.
- `## Conditions` — When the rule applies. Must define triggering context, inputs, and preconditions.
- `## Expected Behavior` — What must happen when the rule is triggered. Must be precise.
- `## Exceptions` — Cases where the rule does not apply. Write "None" if there are no exceptions.

## Policy
- Status must be `Active` (default) or `Archived`.
- If a rule is no longer applicable, change its status to `Archived` via PR.
- Each document covers exactly one rule. Do not combine multiple rules.
- Business rules that depend on architectural decisions should reference the relevant ADR in the Related ADRs metadata field.
