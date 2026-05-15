---
id: consistent-edit-pattern-on-md-user-corrected-appro-e69c04ff
status: rejected
target: adr-pr-review.instructions.md
instinct_confidence: 0.90
evidence_count: 16
priority: 5
created: "2026-06-01"
last_reviewed: "2026-06-01"
created_session: 0
---

# Proposal: Consistent Edit pattern on .md, user corrected approach 9 times

## Trigger
when using Edit on .md

## Suggested Change
Add to `adr-pr-review.instructions.md`:

> Consistent Edit pattern on .md, user corrected approach 9 times

## Evidence
Confidence: 0.90 from 16 observations.
Domain: code-style | Scope: `**/*.md`

- 9 corrections in session 8a2c5390

## Review
- [x] Reviewed by developer
- [ ] Change applied to instruction file

Rejected 2026-06-01: false positive. The correction detector inferred "corrections" from ordinary repeated Edits on markdown during a docs-heavy session. No user correction occurred, and the suggested text is not an actionable rule. `detect_corrections` in `analyze.py` was hardened the same day to prevent recurrence.
