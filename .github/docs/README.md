# Reference Docs

Files in this folder are read on demand by skills, not loaded automatically by the agent. They are the long-form companions to the rules in `../instructions/`.

## adr-template.md

The copyable Architecture Decision Record template. The `adr-creation` skill reads this when walking a user through a new ADR. Validation lives in `../instructions/adr-pr-review.instructions.md`.

## br-template.md

The copyable Business Rule template. Same relationship — the `create-business-rule` skill reads it; `../instructions/br-review.instructions.md` validates the output.

## system-index.md

The map of every file in the template, its purpose, and how it relates to the others. The reference of last resort when something has fallen out of sync or a new file's role is unclear.
