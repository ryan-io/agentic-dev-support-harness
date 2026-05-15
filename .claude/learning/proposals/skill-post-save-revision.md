---
id: skill-post-save-revision
status: applied
target: agent-guardrails.instructions.md
instinct_confidence: 0.00
evidence_count: 1
priority: 1
created: "2026-05-31"
last_reviewed: "2026-05-31"
created_session: 0
---

# Proposal: Skills that generate a saved artifact should support post-save revision

## Trigger
A skill generates a file as its output, the user confirms and saves it, then later wants to change the saved artifact (wording, participants, ordering, added detail). The skill describes generation and one pre-save review loop, but gives no path for revising the file after it is written.

## Suggested Change
Add to `agent-guardrails.instructions.md`: (retargeted from patterns.instructions.md on accept, 2026-05-31)

> Skills whose output is a saved file should include a "revise an existing artifact" step. That step reads the saved file first, applies the requested change, preserves all other content and the skill's generation conventions, confirms before overwriting, and saves to the same path unless the user renames the artifact.

## Evidence
Confidence: manual flag from a developer session, not yet corroborated by the observation log.
Domain: workflow | Scope: `.github/skills/**`

Precedent set this session: the `sequence-diagram` skill was extended with a Step 7 ("Revise an Existing Diagram") doing exactly this. The pattern is reusable across any artifact-producing skill (ADR creation, business-rule creation, sequence diagrams). Flagging it so the next skill author inherits the convention rather than rediscovering it.

## Review
- [ ] Reviewed by developer
- [ ] Change applied to instruction file
