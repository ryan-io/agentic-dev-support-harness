# Reference Docs

Files in this folder are read on demand by skills, not loaded automatically by the agent. They are the long-form companions to the rules in `../instructions/`.

## adr-template.md

The copyable Architecture Decision Record template. The `adr-creation` skill reads this when walking a user through a new ADR. Validation lives in `../instructions/adr-pr-review.instructions.md`.

## br-template.md

The copyable Business Rule template. Same relationship, the `create-business-rule` skill reads it; `../instructions/br-review.instructions.md` validates the output.

## system-index.md

The map of every file in the template, its purpose, and how it relates to the others. The reference of last resort when something has fallen out of sync or a new file's role is unclear.

## Guide Files (thin-rules / deep-docs)

Instruction files that grow large are split into a thin rule file (terse imperatives, auto-loaded by agents) and a companion guide (examples, rationale, read on demand). The thin rule contains a `Full guidance` directive pointing to the guide. Agents read the guide when actively applying rules in depth.

| Guide | Companion Rule |
|-------|----------------|
| `writing-voice-guide.md` | `writing-voice.instructions.md` |
| `agent-guardrails-guide.md` | `agent-guardrails.instructions.md` |
| `testing-guide.md` | `testing.instructions.md` |
| `pr-review-guide.md` | `pr-review.instructions.md` |
