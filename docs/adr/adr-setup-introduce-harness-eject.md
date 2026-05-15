# ADR-SETUP: Introduce harness-eject to Trim Template Machinery from Bootstrapped Clones

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-07 |
| Authors | @ryan-io   |

---

## Context

The harness ships as a template repository. A downstream project clones it, runs setup, then runs the `project-setup` skill to tailor instruction files to a stack. After that point the clone still carries machinery that exists only to instantiate the project: one-time setup scripts, the `ah-ide` scaffolder and its stack templates, and the harness's own decision and process history. None of it is part of the project the developer is now building.

Three problems follow if we do nothing. The repository carries roughly eighty `templates/` files and a scaffolder a single-stack project will never run again. The harness's own ADRs, process plans, and seed learning proposals read as if they were the new project's decisions, which they are not. Most damaging, the project-memory digest in `memory.instructions.md` loads on turn one of every session and orients the agent toward "the agentic-dev-support-harness," so a fresh project starts every session pointed at the wrong subject.

Two constraints shape any teardown. The pre-commit validator (`validate-system.py`) rejects a commit on broken cross-references, missing required files, `.bat`/`.sh` parity gaps, and missing scaffold manifests, so removal cannot leave dangling references. The ADR policy forbids deleting a project's ADRs, so the teardown must distinguish the template's authored records from the downstream project's own future records.

The validator already reads a `.claude/setup-complete` marker for checks 15 through 17, but nothing writes it today. That marker is the natural precondition for a teardown, with one caveat: it must signal completion of the `project-setup` skill, not the `setup.sh` bootstrap. The maintainer runs `setup.sh` in this source repo too, to install the pre-commit hook, so "setup.sh ran" is true here and cannot discriminate a downstream project. Only `project-setup`, which tailors instruction files to a stack, is downstream-exclusive. This source repo has no stack to tailor and never completes it.

---

## Decision

We add a `harness-eject` skill backed by a data-driven engine at `.github/scripts/eject.py`, following the scaffolder's own precedent: a thin skill over a Python engine that reads a manifest, with Python already the repository's automation language. Eject runs only when `.claude/setup-complete` is present, and it commits the working tree first so the entire operation is reversible with one `git revert`.

Two changes make that marker trustworthy. The `project-setup` skill writes `.claude/setup-complete` as its final step, stamping a timestamp and harness version, so the marker means "a downstream project finished tailoring," not "hooks were installed." The marker is added to `.gitignore` so it stays local and never ships in the template or returns to the source through a commit. Because this source repo never completes `project-setup`, the marker never appears here, so eject refuses here.

This source repo also carries a committed sentinel, `.github/TEMPLATE_SOURCE`, that ships in the template. The `project-setup` skill removes it in the same final step that writes the marker, so a downstream clone sheds it the moment setup completes, while the source keeps it because the source never runs `project-setup`. Bootstrap is deliberately not involved: `setup.sh` runs in the source too (for hooks), so it cannot tell source from a "Use this template" clone. Eject hard-refuses whenever the sentinel is present. The two guards are defense in depth: the marker confirms a project finished setup, the sentinel confirms this is not the upstream template, and only the deliberate `project-setup` run clears both.

The engine sorts every removable path into three categories declared in a manifest, not hardcoded in the engine. Category A is one-time init machinery removed unconditionally: the setup engine `.github/scripts/setup/repository-setup.py`. (Per ADR-SCAFFOLD Amendment 2026-06-08, setup is Python-only; the former `.bootstrap/` and `setup.*` shell and batch scripts no longer exist to remove.) Category B is the scaffolder, removed by default with a `--keep-scaffolder` opt-out: `templates/`, `.github/scripts/scaffold.py`, `.github/workflows/scaffold-matrix.yml`, and the scaffold ADR. Category C is template-authored content reset rather than blind-deleted: the harness's own ADRs, `docs/process/`, seed learning proposals, the root `README.md`, and the memory digest, which is rewritten to describe the new project.

Everything else stays, because it remains relevant for the life of the project. The governance layer is the reason the harness exists, not setup overhead. That keep-set is Category D and is named explicitly so eject can never reach it: all instruction files and their mirror, the skills (with `project-setup` trimmed of its scaffolder step), the learning pipeline scripts and data, the pre-commit hook, the sync and validate scripts, the templates and companion guides under `.github/docs/`, every subsystem README, and the now-empty `docs/adr`, `docs/business-rules`, and `docs/design` directories ready for the project's own content.

Eject finishes by running sync and validate, and fails loudly if either does not pass, so a half-ejected repository never reaches a commit.

---

## Other Considerations

**Delete the harness ADRs versus archive them.** The ADR policy says records are archived, never deleted. We delete them on eject anyway, because that policy governs a project's own decision record, and the template's ADRs are not that record. Keeping them archived would clutter a new project with permanent decisions about a tool it now only consumes. The policy still binds in full from the moment the project authors its first ADR. This ADR itself stays in the template permanently; eject removes it only from a downstream clone.

**A flag on `project-setup` instead of a separate skill.** Eject is destructive and scaffolder removal is now default-on, so it deserves its own confirmation surface rather than riding inside setup. `project-setup` may run several times as stacks are added; eject runs once. Keeping them separate keeps each one's intent clear.

**Bulk `rm` in a shell script.** Rejected for the same reason the scaffolder rejected pure-shell generation: manifest parsing, reference scrubbing, and the sync-and-validate gate would be reimplemented in two dialects. The engine stays in Python and the wrappers stay thin.

**Custom undo receipt like `ah-ide undo`.** Rejected as redundant. A pre-eject commit plus `git revert` is simpler and needs no new bookkeeping.

---

## Consequences

Pros. A bootstrapped project sheds setup-only machinery in one reversible command. The memory digest stops mis-orienting every session. The keep-set is explicit, so the teardown cannot strip the governance layer. Scaffolder removal is the lean default while monorepos opt out.

Cons. Eject removes files the validator also checks, so the engine must scrub references in `copilot-instructions.md` and `system-index.md`, trim `project-setup` Step 0, and neutralize the scaffold-manifest and workflow-chain checks in `validate-system.py`, all in the same pass. A reference missed there fails the closing validate step, which is the intended backstop but also the main implementation risk.

Technical debt. The keep-set and removal manifest must track future additions to the harness. A new setup-only script that is not added to the manifest will survive eject. The manifest's coverage is asserted in CI to contain this drift.

---

## Enforcement / Guidance

- Eject refuses to run unless `.claude/setup-complete` exists and `.github/TEMPLATE_SOURCE` does not, and aborts before any deletion if the working tree is dirty, so the reversal commit is always clean.
- `project-setup` writes `.claude/setup-complete` as its final step, and `.gitignore` lists that path so it never commits. CI asserts the source repo still carries `.github/TEMPLATE_SOURCE`, so the upstream guard cannot be deleted unnoticed.
- `eject.py` offers `--dry-run` that prints every path it would remove or reset, grouped by category, and makes no changes.
- The closing sync-and-validate gate is mandatory: a non-zero validate result aborts the commit, so a partial eject cannot land.
- `validate-system.py` gains a check that every Category A and B path in the manifest exists in the pre-eject tree, catching manifest drift as the harness grows.
- When eject removes the scaffolder, it must also remove the scaffold-manifest check and any scaffold-matrix workflow-chain check from `validate-system.py`, so an absent `templates/` degrades to a skip, never a failure.

---

## References

- ADR-SCAFFOLD: Introduce the ah-ide Scaffolding CLI, `docs/adr/adr-scaffold-introduce-ah-ide-cli.md`, 2026-06-03.
- Implementation plan, `docs/process/2026-06-07-harness-eject-plan.md`, 2026-06-07.