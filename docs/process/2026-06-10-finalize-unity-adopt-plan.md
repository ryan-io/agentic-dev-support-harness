# Finalize Unity Adoption Plan (Adopt Mode + Eject Phase 1)

Date: 2026-06-10
Status: In progress (Phases 1-4 complete 2026-06-10; next: Phase 5 verification)
Governing ADRs: `adr-setup-add-adopt-mode-three-paths` (Active), `adr-setup-introduce-harness-eject` (Active)

The unity-greenfield integration (2026-06-10) proved the adoption procedure by hand: manual overlay with collision policy, in-place activate, project-setup's Unity path, then a hand-trim following the eject Phase 0 classification. This plan turns that procedure into code so adopt runs as a first-class path. Per the adopt ADR, adopt mode and eject Phase 1 are one delivery unit; eject lands first because adopt chains into it. Git LFS is required for Unity projects under git (developer decision, 2026-06-10) and lands in the project-setup Unity path (Phase 4).

Phase numbering here is this plan's own. Where a phase delegates to the 2026-06-07 eject plan, it says so rather than restating it.

## Phase 1: Eject destructive run (this session)

Goal: `eject.py` performs the categorized teardown, preview first. This implements Phase 1 of the 2026-06-07 eject plan. Effort: medium.

1. Preconditions. A live run refuses unless `.claude/setup-complete` exists, `.github/TEMPLATE_SOURCE` is absent, and the working tree is clean. The manifest keep-set check runs first in every mode; a violating manifest stops everything.
2. Dry-run. `--dry-run` prints every path it would remove, clear, or reset, grouped by category, and changes nothing. It runs even where the guards refuse, reporting guard state alongside, so a developer can preview safely anywhere.
3. Actions. `remove` deletes Category A always and Category B unless `--keep-scaffolder`; empty parent directories are pruned. `clear` empties a directory except its keep list. `reset` rewrites `README.md` and the memory digest to new-project skeletons, deriving the project name from the repository directory. A runtime keep-set guard refuses any destructive action on a protected path, defense in depth over the manifest check.
4. Closing gate. After mutations, run `sync-claude-rules.py` (the memory reset must reach its mirror) then `validate-system.py`. A non-zero result rolls back with `git reset --hard` (nothing has been committed) and aborts; a partial eject never lands.
5. Reversal. The clean-tree precondition makes the 2026-06-07 plan's pre-deletion snapshot a no-op, so the eject lands as a single commit and one `git revert` of it restores the pre-eject tree, which is the reversal property Phase 4 of that plan verifies.
6. Tests. `test_eject.py` gains Phase 1 coverage on temp git fixtures: dry-run output matches the manifest, a live run removes A and C and honors `--keep-scaffolder`, `clear` preserves the keep list, resets write valid skeletons, a planted protected path is refused, and a revert restores the tree.

Exit: the 2026-06-07 plan's Phase 1 criteria. Dry-run output matches the manifest exactly on a test clone; a live run on a throwaway clone removes A and C, retains B under `--keep-scaffolder`, and leaves a clean reversal commit.

## Phase 2: Eject reference scrub and skill

Delegates to Phases 2 and 3 of the 2026-06-07 eject plan unchanged: scrub references in the two gated files, trim `project-setup` Step 0, de-scaffold the validator, then ship the `harness-eject` skill as the interactive front end. Sequenced before adopt ships because the chained adopt-into-eject run must end validator-green.

Exit: those phases' own criteria.

## Phase 3: Adopt mode in `repository-setup.py`

Goal: the third setup path per the adopt ADR. Effort: medium.

1. Invocation. An explicit `--adopt <target>` flag; no auto-detection. The operator resolves the activate-versus-adopt ambiguity. Adopt refuses an empty target (that is scaffold's job) and a target carrying `.github/TEMPLATE_SOURCE`.
2. Collision policy. Never overwrite an existing file. Merge `.gitignore` rather than copy it: append harness blocks and add case-insensitive collision negations (the `!/Packages/` pattern proven in unity-greenfield) when a tracked target path collides. Skip the template `README.md`. Tolerate an existing `.git`, initializing only when absent. Report every skipped collision.
3. Reuse. Adopt drives the existing `TREE_COPIES` / `FILE_COPIES` / `ROOT_FILES` lists with the adopt write policy. Banner art is already excluded from every copy path. No manifest knowledge at copy time; eject owns removal.
4. Chain. Adopt ends with overlay plus activate, then hands off: the developer runs `project-setup` (an interactive skill), whose completion marker is exactly what eject's guard requires. The chain is procedural across script and skill; adopt prints the handoff explicitly.
5. Tests. `test_repository_setup.py` gains the ADR-named coverage: never-overwrite, gitignore merge, collision report. Hard constraint: the template and scaffold paths keep passing their suites unchanged.

Exit: adopt overlays a populated fixture with zero overwrites and a complete collision report; the regression suites are untouched and green.

## Phase 4: project-setup adopt path and Unity LFS

Goal: the skill knows how to finish an adoption, and Unity projects get LFS from day one. Effort: small.

1. Adopt path. `project-setup` detects an adopted project (for Unity, `ProjectSettings/ProjectVersion.txt`), skips Step 0, verifies the `.gitignore` merge, and fills repo signals as it did for unity-greenfield.
2. LFS. Ship a Unity `.gitattributes` pattern set (textures, audio, video, models, archives, plus the existing text/eol rules) as a reference file under `.github/docs/`. The Unity path merges it into the root `.gitattributes`, never overwriting existing rules, and instructs `git lfs install`. LFS is required, not optional, for Unity adoption.
3. ADR upkeep. Amend `adr-setup-add-adopt-mode-three-paths` to record the project-setup adopt path and the LFS policy. This also closes the two undispositioned ADR candidates from unity-greenfield's exploration doc (the instruction-file landing record and the project-setup amendment).
4. Skill authoring. The new path carries the revision step required by `agent-guardrails` for skills that write artifacts.

Exit: a skill walkthrough on a Unity fixture yields a merged `.gitattributes`, a merged `.gitignore` with `Packages/` tracked, repo signals filled, and the completion marker written.

## Phase 5: Verification (both targets)

Goal: prove the path end to end and prove it is safe to re-run. Effort: small.

1. Fresh project. Hub-create a throwaway Unity project, then adopt, activate, project-setup Unity path, eject. Confirm the validator is green, `Packages/manifest.json` and `packages-lock.json` are tracked, LFS attributes are present, and turn-one agent orientation describes the project, not the harness.
2. Re-adoption. Run adopt `--dry-run` against unity-greenfield. Every overlay file must report a skipped collision; nothing would be overwritten. This proves the collision policy against a real, already-adopted repository.
3. Regression. The template and scaffold paths (csharp vscode/vs2026, lua) pass their existing test and validation suites unchanged, the hard constraint from the adopt ADR.

Exit: all three green.

## Downstream handoff (unity-greenfield, separate sessions)

Once Phase 4 ships: apply the Unity `.gitattributes` LFS set there, resolving its open Git LFS thread as required rather than deferred; record the CoplayDev `unity-mcp` version pin when the bridge is installed; scaffold the headless source-linked `dotnet test` pair so the boundary guard three ADRs cite becomes real; refresh the stale `memory.md` entries through `continuous-learning`. The design pipeline run and Tier 1 pressure tests then proceed per that repo's `next-steps.md`.
