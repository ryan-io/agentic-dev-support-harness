# ADR-SETUP: Add Adopt Mode and Establish the Three-Path Model

---

## Metadata

| Field       | Value                |
|-------------|----------------------|
| Status      | Active               |
| Date        | 2026-06-10           |
| Authors     | @ryan-io             |

---

## Amendment 2026-06-10: project-setup adopt path and required Git LFS for Unity

This amendment extends the Decision with the skill-side half of the adopt path and a Unity-specific VCS requirement. Amendments are recorded here rather than by editing the original text, per the ADR permanence policy.

**project-setup adopt path.** The `project-setup` skill gains an adopt path: it detects an adopted project (for Unity, `ProjectSettings/ProjectVersion.txt`), skips the scaffold step, verifies the `.gitignore` merge (merge header present, `git check-ignore` clean on `Packages/manifest.json`), and scopes the UI instruction files. This closes the third ADR candidate from the unity-greenfield exploration doc. The second candidate (recording how stack decisions land in the rule set) needs no separate ADR: the supersession layer is the consuming project's own `unity-code-standards.instructions.md`, governed by that project's ADRs.

**Git LFS is required for Unity adoption** (developer decision, 2026-06-10), not deferred. A Unity LFS reference set ships at `.github/docs/unity.gitattributes`. Adopt mode itself detects a Unity target (`ProjectSettings/ProjectVersion.txt`), merges the set into the project root `.gitattributes` (append-only, under a marker header), and runs `git lfs install --local`, warning loudly when git-lfs is absent. The project-setup adopt path verifies the merge and owns the judgment calls (`git lfs migrate` for blobs already committed as plain objects). Unity text assets (`.unity`, `.prefab`, `.asset`, `.meta`) never route through LFS.

**Implementation status.** Eject Phases 1 and 2 (destructive run, reference scrub, scaffolder trim, `harness-eject` skill) and adopt mode in `repository-setup.py` shipped 2026-06-10 per `docs/process/2026-06-10-finalize-unity-adopt-plan.md`. The chain is procedural across script and skill: adopt overlays and activates, `project-setup` writes the completion marker, `harness-eject` finishes the teardown.

---

## Context

The harness assumes it arrives first: clone the template, run setup, scaffold, eject. Tools that own project creation invert that order. Unity Hub creates the project folder itself and cannot create into a non-empty directory, so a Unity stack template under `templates/` would never be consumed; the same applies to any generator-owned ecosystem. The first real case (unity-greenfield, 2026-06-10) was integrated by hand: manual copy with collision policy, in-place activate, then a hand-trim following the eject Phase 0 plan. It worked, but every step was error-prone manual policy, and the overlay initially carried dead template machinery (scaffolder, `templates/`, harness ADRs) into the consuming project.

---

## Decision

Add an adopt mode to `repository-setup.py`, establishing three first-class paths into the harness: **template** (GitHub template clone plus activate), **scaffold** (new local directory), and **adopt** (integrate with an existing project).

Adopt copies the template trees into a non-empty target with a collision policy: never overwrite an existing file, merge `.gitignore` rather than copy it (keep harness entries, add `!/Packages/`-style negations where the target's tracked paths collide case-insensitively), skip the template `README.md`, tolerate an existing `.git` (init only when absent), and report every skipped collision. It reuses the existing `TREE_COPIES` / `FILE_COPIES` / `ROOT_FILES` lists with a different write policy. Banner art is never copied on any path.

Adopt ends by chaining into the eject workflow: once overlay, activation, and project-setup complete, eject runs and removes out-of-scope machinery per its manifest. Removal knowledge lives in the manifest only; adopt does not duplicate it at copy time. This requires eject Phase 1 (the destructive run); Phase 0 today is classification only. Adopt mode and eject Phase 1 are therefore one delivery unit.

---

## Other Considerations

Manifest-driven exclusion at copy time (adopt skips Category A/B instead of copying then ejecting) was considered and rejected by the developer: it duplicates manifest knowledge in a second engine and lets the two drift. Manual copy plus activate remains the documented interim and was used for unity-greenfield; it stays valid as a fallback but is not a path. Clone-then-move (create from template, move the generated project in) was rejected: fiddlier than the manual copy with no advantage. These alternatives are recorded in the unity-greenfield exploration doc.

---

## Consequences

Pros: generator-owned ecosystems (Unity Hub, and analogous tools) get a supported, repeatable path; the consuming repo's first commit contains only live machinery; collision handling becomes tested code instead of careful hands. Cons: `repository-setup.py` grows a third mode and a collision-policy surface that needs its own tests; adopt is blocked on eject Phase 1. Technical debt: until both land, adoption remains the documented manual procedure. The 2026-06-10 session also hardened the surrounding pieces in advance: eject-manifest gaps closed (second scaffold ADR, implementation-stage ADR, setup-engine test, banners) and `validate-system.py` made eject-aware (setup-engine and templates checks gate on `.claude/setup-complete`).

---

## Enforcement / Guidance

Adopt-mode collision policy gets unit tests in `.github/scripts/tests/test_repository_setup.py` (never-overwrite, gitignore merge, collision report). Eject Phase 1 must respect the existing guards: `require_marker` `.claude/setup-complete`, `refuse_if_present` `.github/TEMPLATE_SOURCE`, and the protected-roots keep-set. The scaffold and template paths must keep passing their existing test and validation suites unchanged; that is a hard constraint on the implementation.

---

## References

- unity-greenfield, `docs/design/unity-harness-integration/exploration.md` (integration options, collision analysis, 2026-06-10).
- `docs/adr/adr-setup-introduce-harness-eject.md` (this repository, category model and guards).
- Unity Hub project-creation behavior (checked 2026-06-09): https://docs.unity3d.com/hub/manual/
