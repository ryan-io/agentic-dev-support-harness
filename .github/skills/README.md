# Skills

On-demand procedures the agent runs when invoked by name. Unlike instruction files, skills are not preloaded, they are read only when the agent decides to execute one based on the user's request.

## Catalog

`project-setup` tailors the template to a specific stack: offers scaffolding (`python .github/scripts/scaffold.py`) as step zero when no solution exists, fills in the CUSTOMIZE markers, generates a `{language}-code-standards` file, and removes anything not relevant. Run this once, right after setup (`python .github/scripts/setup/repository-setup.py`).

`harness-eject` runs the one-time, reversible teardown after `project-setup`: previews the removal plan, confirms the scaffolder opt-out, runs `../scripts/eject.py`, and verifies the validator stays green. The eject lands as a single revertable commit.

`harness-update` pulls harness improvements from the template into an adopted project: checks the committed version anchor, previews overwrites and three-way merges, and lands one revertable commit. Conflicted merges stop before the commit; `--finish` completes after resolution. Decision record: `docs/adr/adr-setup-add-harness-update-mechanism.md`.

`adr-creation` walks the user through writing an Architecture Decision Record using the template in `../docs/adr-template.md`, validating against the rules in `../instructions/adr-pr-review.instructions.md`, and saving to `docs/adr/`.

`create-business-rule` does the same for business rules, against `../docs/br-template.md` and `../instructions/br-review.instructions.md`, saving to `docs/business-rules/`.

`system-review` audits the harness itself, checks that synced files match, frontmatter is valid, character limits are respected, and cross-references resolve.

`convention-discovery` reads git history to surface implicit conventions that should be promoted into instruction files. Triggered manually or by the `convention-discovery.yml` workflow on merge to main.

`continuous-learning` reviews pending proposals from the learning pipeline (see `../scripts/learning/README.md`), applies the approved ones to the instruction files, and curates the project-memory digest (`../instructions/memory.instructions.md`) by promoting durable facts from the local session log under review.

`behavioral-requirements` captures requirements as required behavior rather than functionality. Elicits use cases, draws activity diagrams for anything with nested conditionals, and flags solutions masquerading as requirements. Stage 1 of the design pipeline; its `use-cases.md` feeds `volatility-decomposition`.

`volatility-decomposition` applies volatility-based decomposition. Identifies what is likely to change, scrubs solutions masquerading as requirements, decides what not to encapsulate, and proposes change boundaries. Stage 2 of the pipeline: reads `use-cases.md` if present, writes `volatilities.md`. Also runs standalone to analyze a codebase or review an existing architecture.

`architecture-layering` classifies a volatilities list into a layered architecture: the Four Questions, the Client / Business Logic / ResourceAccess / Resource layers plus the Utilities bar, the Manager/Engine/ResourceAccess taxonomy, and the naming conventions. Stage 3 of the pipeline: reads `volatilities.md`, writes `architecture.md`.

`architecture-design-pipeline` is a thin orchestrator that runs the three stages in order (behavioral-requirements, volatility-decomposition, architecture-layering) over one shared `docs/design/{slug}/` folder. Adds no design logic; each stage skill also runs independently.

`implementation` pair-programs a design into C#/WPF code: the agent drives, the developer navigates. It reads the `docs/design/{slug}/` artifacts in any combination, builds a service backlog from `architecture.md`, and implements them one at a time, test first, with the design as the source of truth and drift flagged back into the design skills. Stage 4 of the pipeline. Bootstraps a base solution via `scaffold.py` when none exists and keeps a backlog note in `docs/process/`.

`write-unit-tests` writes unit tests for code that already exists, one unit at a time, applying the testing standards rather than restating them. Reads the unit and its collaborators, enumerates behaviors and edge cases, writes Arrange-Act-Assert tests, mocks only at owned boundaries, verifies outcomes, and runs the suite green. C# default is NUnit 4 with Moq. Distinct from `implementation`, which is test-first pairing on a new design: this skill produces the tests themselves and also revises an existing test file in place.

`sequence-diagram` creates a Mermaid sequence diagram from a structured specification or natural-language description. Walks the user through participants, message flow, and interaction patterns (loops, conditionals, parallel flows), then saves a markdown file with the diagram source to `docs/diagrams/`.

## Adding a New Skill

Create the skill directory and SKILL.md, then register it in all four locations. The validation script checks each one and will fail if any is missing.

1. `.github/skills/{name}/SKILL.md`: the skill definition with frontmatter.
2. `.github/skills/README.md`: add an entry to the Catalog section above.
3. `.github/copilot-instructions.md` (and `CLAUDE.md`): add to the On-Demand skills list. These files must stay identical.
4. `.github/docs/system-index.md`: add a row to the On-Demand table.

## Structure

Each skill is a folder with a `SKILL.md` file. The frontmatter `description` field is what the agent matches against to decide whether to invoke. Keep descriptions tight and unambiguous, vague descriptions cause skills to fire when they shouldn't, or fail to fire when they should.

## Related

- [Instruction files](../instructions/README.md): the always-on rules skills run alongside.
- [Reference docs](../docs/README.md): the templates and system index skills read on demand.
- [Learning pipeline](../scripts/learning/README.md): how `continuous-learning` gets its proposals.
- [ADRs](../../docs/adr/README.md) and [business rules](../../docs/business-rules/README.md): outputs of `adr-creation` and `create-business-rule`.
- [Design artifacts](../../docs/design/README.md): outputs of the architecture design pipeline skills.
- [Scaffolding templates](../../templates/README.md): the `ah-ide` step `project-setup` offers first.
