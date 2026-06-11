# ADR Index

Triage table for every Architecture Decision Record in `docs/adr/`. Consult it before loading any full ADR into context.

Read this first: scan for a row whose Context matches what you are touching, check its Status, then read the Synopsis. Open the full ADR only when the Synopsis shows it governs your change. This keeps whole ADRs out of context until one is actually relevant.

Status values follow the ADR policy: `Active` (in force), `Proposed` (recorded, not yet adopted), `Archived` (superseded or retired). Context is the subsystem or concern the decision belongs to.

| ADR | Status | Context | Synopsis |
|-----|--------|---------|----------|
| [adr-design-establish-architecture-design-pipeline](adr-design-establish-architecture-design-pipeline.md) | Active | Design pipeline | Splits design work into three single-purpose skills (behavioral-requirements, volatility-decomposition, architecture-layering) plus a thin orchestrator; stages hand off through files in `docs/design/{slug}/`, not code coupling. |
| [adr-design-add-implementation-stage](adr-design-add-implementation-stage.md) | Active | Design pipeline | Adds a fourth `implementation` stage that pair-programs the architecture into C#/WPF one service at a time; design artifacts stay source of truth and divergence stops the session rather than drifting silently. |
| [adr-learn-establish-shared-project-memory](adr-learn-establish-shared-project-memory.md) | Active | Learning / persistence | Establishes committed project memory via `memory.instructions.md` (synced to `.claude/rules/`), drawing the shared-vs-local boundary: curated digest is committed, raw observation data stays gitignored. |
| [adr-learn-capture-corrections-via-transcript-parse](adr-learn-capture-corrections-via-transcript-parse.md) | Active | Learning pipeline | Captures user corrections from the SessionEnd transcript as derived fields only; raw transcript text never enters the observation log, preserving the privacy boundary. |
| [adr-learn-replace-wall-clock-decay-with-evidence-based-staleness](adr-learn-replace-wall-clock-decay-with-evidence-based-staleness.md) | Active | Learning pipeline | Replaces wall-clock decay with a session-clock timer plus evidence-based confidence reduction; developer-confirmed knowledge never decays. |
| [adr-project-add-research-instruction-file](adr-project-add-research-instruction-file.md) | Active | Instruction files | Adds `research.instructions.md` as a universal rule governing how agents gather context and cite sources: prefer primary docs, date volatile facts, keep an evidence trail, inspect the repo before browsing. |
| [adr-rag-introduce-code-retrieval-subsystem](adr-rag-introduce-code-retrieval-subsystem.md) | Proposed | Code retrieval | Proposes an AST-aware (tree-sitter) chunking plus BM25-and-embedding hybrid retrieval subsystem for application code; composable and on-demand, not always-on infrastructure. |
| [adr-scaffold-introduce-ah-ide-cli](adr-scaffold-introduce-ah-ide-cli.md) | Active | Scaffolding | Ships the `ah-ide` Python scaffolding engine; stacks are data (`templates/*/manifest.json`), not engine code, so adding a stack is a new directory rather than an engine change. |
| [adr-scaffold-add-test-framework-dimension](adr-scaffold-add-test-framework-dimension.md) | Active | Scaffolding | Adds a `--test-framework` dimension (NUnit/xUnit/MSTest) as manifest-declared data resolved through a generic `_testfw/` overlay; no framework names appear in engine code. |
| [adr-setup-introduce-harness-eject](adr-setup-introduce-harness-eject.md) | Active | Setup / lifecycle | Adds `harness-eject` to trim template machinery from a bootstrapped clone; a data-driven manifest sorts paths into remove / reset / keep categories, gated on `setup-complete` and refused on the template source. |
| [adr-setup-add-adopt-mode-three-paths](adr-setup-add-adopt-mode-three-paths.md) | Active | Setup / lifecycle | Adds adopt mode to `repository-setup.py`, establishing three first-class entry paths (template, scaffold, adopt) with a non-destructive collision policy for integrating into an existing project. |
| [adr-setup-add-harness-update-mechanism](adr-setup-add-harness-update-mechanism.md) | Active | Setup / lifecycle | Adds the `harness-update` skill and manifest-driven engine: a committed version anchor plus three-way merge pulls harness improvements into adopted projects without clobbering customized files. |

## Maintenance

This index is generated content. Keep one row per ADR. When the `adr-creation` skill writes a new ADR, it appends a row here. When an ADR's status changes, update the Status cell in the same PR. Do not let a row drift from the file it points to.

On `harness-eject`, this index is reset to an empty skeleton because every row points to a template-authored ADR the consuming project does not own.
