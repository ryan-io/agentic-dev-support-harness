---
id: consistent-read-pattern-on-md-user-corrected-appro-693cdd79
status: rejected
target: agent-guardrails.instructions.md
instinct_confidence: 0.90
evidence_count: 14
priority: 5
created: "2026-06-01"
last_reviewed: "2026-06-01"
created_session: 0
---

# Proposal: Consistent Read pattern on .md, user corrected approach 8 times

## Trigger
when using Read on .md

## Suggested Change
Add to `agent-guardrails.instructions.md`:

> Consistent Read pattern on .md, user corrected approach 8 times

## Evidence
Confidence: 0.90 from 14 observations.
Domain: navigation | Scope: `**/*.md`

- 8 corrections in session 8a2c5390

## Review
- [x] Reviewed by developer
- [ ] Change applied to instruction file

Rejected 2026-06-01: false positive. The correction detector inferred "corrections" from ordinary repeated Reads on markdown during a docs-heavy session. No user correction occurred, and the suggested text is not an actionable rule. `detect_corrections` in `analyze.py` was hardened the same day to prevent recurrence.
