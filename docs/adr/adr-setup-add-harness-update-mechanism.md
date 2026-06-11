# ADR-SETUP: Add a Manifest-Driven Update Channel from the Template to Adopted Projects

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-10 |
| Authors | @ryan-io   |

---

## Context

The harness reaches downstream projects three ways (template, scaffold, adopt; see `adr-setup-add-adopt-mode-three-paths.md`), and every one of them is a one-time copy. After `project-setup` and `harness-eject`, a project owns its tree and the template has no channel back into it. Improvements to instruction files, skills, the learning pipeline, or the sync and validate scripts stay in this repository unless a developer notices them and ports them by hand.

If we do nothing, adopted projects drift. The case-study literature on template fleets shows the failure mode: rarely-touched projects accumulate months of template changes, and each manual catch-up gets more expensive than the last. With several projects already adopted, every harness fix today is multiplied by hand-porting.

Two existing decisions constrain the design. First, the harness version is currently stamped only into `.claude/setup-complete`, which is gitignored by design (`adr-setup-introduce-harness-eject.md`), so a downstream clone has no committed record of which harness commit it adopted. An update mechanism needs a tracked anchor or it cannot compute what changed. Second, downstream trees are deliberately divergent: eject resets template-authored content (Category C) to project-owned skeletons, and `project-setup` has the project customize the memory digest, research repo signals, patterns file, the hub file, and the system index. A blind overwrite would clobber exactly the files the harness tells projects to make their own.

The histories are also unrelated. Adopt mode copies trees into an existing repository, so `git merge` from an upstream remote is not generally available. Whatever we build must work at the file level.

---

## Decision

We add a `harness-update` skill backed by a data-driven engine at `.github/scripts/update.py`, following the precedent set by the scaffolder and eject: a thin skill over a Python engine that reads a manifest, stdlib-only, fails closed.

The mechanism is a three-way merge anchored on a committed version record. This is the algorithm Copier and cruft use for template updates, scoped to our own manifest instead of their templating engines: diff the harness between the anchored commit and the target commit, then apply that diff to the project, so local customizations survive and only true conflicts surface.

Three parts make it work.

**A tracked anchor.** `project-setup` writes `.github/harness-version.json` recording the harness source URL and the adopted commit. Unlike `.claude/setup-complete`, this file is committed: it is the base revision for every future three-way merge. The gitignored marker keeps its existing role as the eject guard; the anchor is new, additive, and survives eject (Category D).

**An update manifest.** `.github/scripts/update-manifest.json` sorts harness-shipped paths into two sets. The *overwrite set* is consume-only content a project never edits: the generic instruction files, skills, learning pipeline scripts, sync and validate scripts, and `.github/docs/` templates and guides. These are applied directly from the new harness version. The *merge set* is the files projects customize: the memory digest, research repo signals, `patterns.instructions.md`, the hub file, and `system-index.md`. These go through `git merge-file` with the anchored harness version as base, the project's file as ours, and the new harness version as theirs; conflicts land as standard conflict markers for the developer to resolve. Everything not in the manifest is project-owned and untouched, which automatically excludes eject Category C content (the project's ADRs, README, process docs, learning data).

**A gated apply.** The engine refuses on a dirty tree, offers `--check` and `--dry-run`, applies the manifest, reruns `sync-claude-rules.py` to regenerate the `.claude/rules/` mirror, runs `validate-system.py`, bumps the anchor to the new commit, and lands everything as one revertable commit. A non-zero validate aborts and rolls back, mirroring eject's closing gate.

The skill runs in the downstream project, pulling from the harness. Push-based distribution is out of scope here (see Other Considerations).

---

## Other Considerations

**Adopt Copier (or cruft) wholesale.** Copier's update flow is the strongest prior art and directly inspired this design. Rejected as the implementation because it requires restructuring the harness into a Copier/Cookiecutter template, adds a non-stdlib dependency to a pipeline that is deliberately stdlib-only, and its anchor (`.copier-answers.yml`) would sit alongside rather than replace our setup machinery. May be revisited if the manifest approach proves too coarse.

**actions-template-sync scheduled PRs.** A GitHub Action that periodically diffs against the template and opens a PR, with an ignore file protecting customized paths. It solves the drift-awareness problem (nobody has to remember to update) but not the merge problem: it is a file-level overwrite, not a three-way merge. Complementary, not competing. A follow-up may add an optional workflow that runs `update.py --check` on a schedule and opens an issue or PR when the anchor is behind.

**Fork-based `git merge` from upstream.** Works only when histories are shared, which the template and adopt paths do not provide. Rejected as the general mechanism; projects that happen to be forks can still use it.

**Manual cherry-picking (status quo).** No new machinery, full developer control. Rejected because it does not scale past a couple of projects and leaves no record of update state.

**Extending `eject-manifest.json` instead of a new manifest.** Tempting since eject's Category D approximates the overwrite set. Rejected: the two manifests answer different questions ("what survives teardown" vs "what the template still owns"), and coupling them would make every eject edit a potential update bug. The CI coverage check applies the same drift-containment pattern to both.

---

## Consequences

Pros. Harness improvements reach adopted projects as one reviewable, revertable commit per project. Customized files are merged, not clobbered. The anchor makes update state explicit and auditable. The manifest reuses a proven pattern (eject) and the engine reuses proven gates (dry-run, sync, validate, single commit).

Cons. The merge set can conflict, and resolving conflicts in instruction files requires judgment; the skill must surface them clearly rather than auto-resolving. Projects adopted before this ADR have no anchor; the skill needs a one-time `--anchor <commit>` bootstrap where the developer identifies (or approximates) the adopted commit.

Technical debt. The update manifest must track future additions to the harness, the same drift risk eject carries. A new instruction file missing from the manifest will silently never ship. CI asserts manifest coverage against the harness tree to contain this, mirroring the eject coverage check.

---

## Enforcement / Guidance

- `project-setup` writes `.github/harness-version.json` in the same final step that writes `.claude/setup-complete`; the validator gains a check that the anchor exists and parses whenever `setup-complete` is present.
- `update.py --check` reports anchor state and whether the harness has newer commits, without changing anything. `--dry-run` prints every planned overwrite, merge, and expected conflict.
- The engine refuses on a dirty working tree and lands the update as a single commit, so one `git revert` restores the pre-update tree.
- The closing sync-and-validate gate is mandatory; a non-zero result rolls back the working tree and leaves the anchor untouched.
- The validator (check 24) asserts the manifest parses, merge and exclude sets are disjoint, classified paths exist in the source tree, and every eject-protected root is reachable by the update manifest, catching drift when files are added.
- The `harness-update` skill must not run in this source repository; it refuses when `.github/TEMPLATE_SOURCE` is present, the same upstream guard eject uses.

---

## References

- Copier documentation, "Updating a project", https://copier.readthedocs.io/en/stable/updating/, accessed 2026-06-10.
- cruft, https://github.com/cruft/cruft, accessed 2026-06-10.
- AndreasAugustin, actions-template-sync, https://github.com/AndreasAugustin/actions-template-sync, accessed 2026-06-10.
- Mr-Pepe, "Managing Repositories at Scale: A Case Study", Medium, accessed 2026-06-10.
- ADR-SETUP: Introduce harness-eject, `docs/adr/adr-setup-introduce-harness-eject.md`, 2026-06-07.
- ADR-SETUP: Add Adopt Mode, `docs/adr/adr-setup-add-adopt-mode-three-paths.md`.
