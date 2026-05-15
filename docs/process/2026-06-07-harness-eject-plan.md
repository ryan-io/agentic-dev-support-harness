# Harness Eject Implementation Plan

Date: 2026-06-07
Status: In progress (Phase 0)
Governing ADR: `adr-setup-introduce-harness-eject` (Active)

A bootstrapped clone keeps machinery that exists only to instantiate the project. This plan adds `harness-eject`: a one-time, reversible teardown that runs after `project-setup`, removes setup-only machinery, resets template-authored content to the new project, and leaves the governance layer intact with the validator green. It lands in five phases. Each phase has exit criteria; no phase starts until the prior one meets them.

## What stays relevant after bootstrap (Category D, never touched)

The teardown exists to protect this set, not just to delete. Eject must never reach any of it.

- Instruction files in `.github/instructions/` and the `.claude/rules/` mirror.
- Skills in `.github/skills/`, with `project-setup` trimmed of its scaffolder step. `project-setup` itself stays: it still adds stacks and languages later.
- The learning pipeline: `.github/scripts/learning/`, `.claude/learning/config.json`, `.claude/settings.json`.
- Automation that runs on every commit: `.github/hooks/pre-commit`, which runs `sync-claude-rules.py` and `validate-system.py`.
- Reference assets under `.github/docs/`: the ADR and BR templates, the companion guides, the system index.
- Subsystem READMEs, the PR template, `.gitattributes`, and `.gitignore`.
- The `docs/adr`, `docs/business-rules`, `docs/design`, `docs/diagrams`, and `docs/research` directories, emptied of harness examples and ready for the project's own content.

## What eject removes or resets

- Category A, removed unconditionally: `.github/scripts/setup/repository-setup.py`. (Setup is Python-only per ADR-SCAFFOLD Amendment 2026-06-08; the former `.bootstrap/` and `setup.*` shell/batch scripts no longer exist.)
- Category B, removed by default with `--keep-scaffolder` to retain: `templates/`, `.github/scripts/scaffold.py`, `.github/workflows/scaffold-matrix.yml`, `docs/adr/adr-scaffold-introduce-ah-ide-cli.md`.
- Category C, reset to the new project rather than blind-deleted: the harness ADRs (`adr-learn-*`, `adr-design-*`, `adr-project-*`, `adr-rag-*`, and `adr-scaffold-*` when B runs), `docs/process/`, `.claude/learning/proposals/*`, the root `README.md`, and the memory digest in `memory.instructions.md` and its mirror.

## Cross-cutting constraints

- Eject is reversible: it commits the working tree first, so the whole operation reverts with one `git revert`. It aborts before any deletion if the tree is dirty.
- Eject runs only when `.claude/setup-complete` exists and `.github/TEMPLATE_SOURCE` does not. The marker signals `project-setup` completion, not bootstrap, because the setup engine (`repository-setup.py`) runs in the source repo too. The sentinel is the upstream hard block. Together they refuse on a pre-setup clone and on the template source.
- The closing sync-and-validate gate is mandatory. A non-zero validate result aborts; a partial eject never lands.
- The validator inspects backtick path references in only two files, `copilot-instructions.md` and `system-index.md`. Reference scrubbing must cover both. Other files are cleaned for hygiene, not to satisfy the gate.
- Root `.bat` and `.sh` commands are checked for parity. Remove each pair together.
- Removing the scaffolder requires removing its validator checks in the same pass, so an absent `templates/` degrades to a skip, not a failure.

## Phase 0: Completion marker, source sentinel, manifest, keep-set guard

Goal: the run-context guards and the removal set, all as data the engine reads. Effort: small.

1. Completion marker producer. `project-setup`'s final step writes `.claude/setup-complete` with a timestamp and harness version. Add the path to `.gitignore` so it stays local and never commits. This is the missing producer for a marker the validator already reads.
2. Source sentinel. Add a committed `.github/TEMPLATE_SOURCE` to the template. `project-setup`'s final step removes it, the same step that writes the marker, because bootstrap cannot tell the source from a "Use this template" clone (both run the setup engine in place). CI asserts the source repo still carries it.
3. Manifest. A `.json` or `.md` data file lists every Category A, B, and C path with its category and its action (remove or reset). The engine reads it; no paths are hardcoded.
4. Keep-set guard. A deny check in the engine refuses to act on any Category D path even if a future manifest edit lists it by mistake.
5. Validation. `validate-system.py` asserts every Category A and B path in the manifest exists in the current tree, catching manifest drift as the harness grows.

Exit: marker is written by a `project-setup` dry-run and is gitignored, the sentinel is present and CI-checked, manifest parses, the keep-set guard rejects a planted Category D path in a unit test, the drift check is green.

## Phase 1: Engine with dry-run

Goal: `eject.py` performs the categorized teardown, preview first. Effort: medium.

1. Preconditions. Refuse unless `.claude/setup-complete` exists, `.github/TEMPLATE_SOURCE` is absent, and the working tree is clean.
2. Dry-run. `--dry-run` prints every path it would remove or reset, grouped by category, and changes nothing. This is the default safety surface.
3. Removal. Category A always; Category B unless `--keep-scaffolder`; Category C reset actions, including rewriting the memory digest to a new-project skeleton.
4. Reversal commit. Commit the working tree before the first deletion.

Exit: dry-run output matches the manifest exactly on a test clone; a live run on a throwaway clone removes A and C, retains B under `--keep-scaffolder`, and leaves a clean reversal commit.

## Phase 2: Reference scrubbing and validator de-scaffolding

Goal: the teardown leaves no dangling reference and no orphaned validator check. Effort: medium.

1. Scrub the two gated files. Remove references to removed paths from `system-index.md` and `copilot-instructions.md`, then re-sync `CLAUDE.md`.
2. Trim `project-setup`. Remove Step 0 (scaffolder) and any scaffolder mentions when Category B runs.
3. De-scaffold the validator. When B runs, remove the scaffold-manifest check and any scaffold-matrix workflow-chain check from `validate-system.py`.
4. Hygiene scrub. Clean scaffolder and harness-ADR references from the other READMEs and `scripts/README.md`.

Exit: on a test clone, `validate-system.py` exits zero after a full eject and after a `--keep-scaffolder` eject; no backtick reference in the two gated files points at a removed path.

## Phase 3: The harness-eject skill

Goal: an interactive front end over the engine. Effort: small.

1. Skill. `harness-eject` confirms intent, surfaces the dry-run, and prompts for `--keep-scaffolder`. Category C resets are shown before they run.
2. Authoring rule. The skill follows the skill-authoring convention: it reads current state before acting and confirms before destructive steps.
3. Discoverability. Register the skill in `copilot-instructions.md` and `system-index.md` so both agents can find it. Sync.

Exit: the skill runs end to end on a throwaway clone, the validator stays green, and the result is a project repo with the governance layer intact and no setup machinery.

## Phase 4: Verification

Goal: prove the teardown on a realistic instantiation. Effort: small.

1. End-to-end. Clone the template, run setup, run `project-setup` for one stack, run `harness-eject`. Confirm the validator passes and the agent's turn-one orientation describes the new project, not the harness.
2. Opt-out path. Repeat with `--keep-scaffolder` and confirm the scaffolder and its validator checks survive together.
3. Reversal. Confirm a single `git revert` of the eject commit restores the pre-eject tree.

Exit: both paths pass, reversal restores cleanly, and the memory digest no longer mentions the harness in the ejected clone.
