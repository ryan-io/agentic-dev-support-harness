# Harness Status

Point-in-time state of the harness. Update this when a subsystem ships or a verification window opens or closes. Last updated 2026-06-05.

## Configuration

The harness is configured. `copilot-instructions.md` and `system-index.md` no longer carry `<!-- CUSTOMIZE -->` markers. The remaining markers live in `.gitignore`, the Repo Signals block of `research.instructions.md` (fill it during project setup), and the deprecated `patterns.instructions.md` placeholder.

Two language-specific code-standards files are populated: `csharp-code-standards.instructions.md` and `lua-code-standards.instructions.md`. ADRs are authored under `docs/adr/`, including the project-memory decision (`adr-learn-establish-shared-project-memory`) and the scaffolding CLI decision (`adr-scaffold-introduce-ah-ide-cli`). `docs/business-rules/` has no rules yet.

## Scaffolder

The `ah-ide` scaffolder ships with four templates (three C# layouts on .NET 10 with NUnit, one Lua), validated by the `scaffold-matrix.yml` workflow and check 23 of `validate-system.py`.

## Learning pipeline

The learning pipeline is wired and live, recording observations and producing proposals. One earlier proposal (`skill-post-save-revision`) was reviewed and applied, adding the Skill Authoring rule to `agent-guardrails.instructions.md`. The committed project-memory digest is populated and curated through the `continuous-learning` skill; review any pending proposals with that skill before acting on them.

As of 2026-06-05 the pipeline's signal layer is implemented in full: transcript-parse correction capture and evidence-based session-clock staleness (both ADRs Active), provenance-tagged instincts, the proposal quality gate, the `#correction` marker, and the contradiction reducer. The verification windows are open: classifier precision is unproven until the first real correction batches are reviewed, per `docs/process/2026-06-04-learning-signal-fidelity-plan.md` (baseline metrics recorded there).

## Design pipeline

A volatility-based design pipeline (`behavioral-requirements`, `volatility-decomposition`, `architecture-layering`, orchestrated by `architecture-design-pipeline`) runs requirements through to a layered architecture under `docs/design/{slug}/`, following Löwy's Righting Software method.
