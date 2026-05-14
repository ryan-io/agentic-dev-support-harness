# Skills

On-demand procedures the agent runs when invoked by name. Unlike instruction files, skills are not preloaded, they are read only when the agent decides to execute one based on the user's request.

## Catalog

`project-setup` tailors the template to a specific stack, fills in the CUSTOMIZE markers, generates a `{language}-code-standards` file, and removes anything not relevant. Run this once, right after `setup.sh`.

`adr-creation` walks the user through writing an Architecture Decision Record using the template in `../docs/adr-template.md`, validating against the rules in `../instructions/adr-pr-review.instructions.md`, and saving to `docs/adr/`.

`create-business-rule` does the same for business rules, against `../docs/br-template.md` and `../instructions/br-review.instructions.md`, saving to `docs/business-rules/`.

`system-review` audits the harness itself, checks that synced files match, frontmatter is valid, character limits are respected, and cross-references resolve.

`convention-discovery` reads git history to surface implicit conventions that should be promoted into instruction files. Triggered manually or by the `convention-discovery.yml` workflow on merge to main.

`continuous-learning` reviews pending proposals from the learning pipeline (see `../scripts/learning/README.md`) and applies the approved ones to the instruction files.

## Structure

Each skill is a folder with a `SKILL.md` file. The frontmatter `description` field is what the agent matches against to decide whether to invoke. Keep descriptions tight and unambiguous, vague descriptions cause skills to fire when they shouldn't, or fail to fire when they should.
