---
name: harness-eject
description: >
  One-time, reversible teardown of harness template machinery after project-setup
  completes. Surfaces a dry-run preview, confirms the scaffolder opt-out, runs the
  eject engine, and verifies the result. Use when the user wants to "eject", "remove
  template machinery", "trim the harness", or finish adopting the harness into an
  existing project.
---

# Harness Eject Skill

Run the one-time teardown that removes setup-only machinery and resets template-authored content, leaving the governance layer intact. The engine is `.github/scripts/eject.py`; the removal set lives in `.github/scripts/eject-manifest.json`. Decision record: `docs/adr/adr-setup-introduce-harness-eject.md`.

## Preconditions

Eject runs once, after `project-setup` completes. Confirm before anything else:

1. Run `python .github/scripts/eject.py --check`. It must report the manifest PASS and guard state CAN eject (`.claude/setup-complete` present, `.github/TEMPLATE_SOURCE` absent). If it refuses, stop and tell the developer why; do not work around the guards.
2. The working tree must be clean. The eject lands as a single revertable commit; ask the developer to commit or stash first if `git status` shows changes.

## Workflow

### Step 1: Surface the preview

Run `python .github/scripts/eject.py --dry-run` and show the developer the full output: every removal by category, the Category C resets (`README.md` and the memory digest are rewritten to new-project skeletons), the reference scrub, and the scaffolder trim. Nothing has changed yet.

### Step 2: Confirm the scaffolder decision

Ask whether to keep the scaffolder (`templates/`, `scaffold.py`). Default is removal; `--keep-scaffolder` retains it for projects that will still scaffold new solutions. Re-run the dry-run with the flag if the developer opts out, so the preview matches what will run.

### Step 3: Run the eject

Only after explicit confirmation of the previewed plan, run `python .github/scripts/eject.py --run` (plus `--keep-scaffolder` if chosen). The engine enforces the guards again, applies the manifest, scrubs references, runs sync and validation, and commits. A non-zero validation rolls back automatically; nothing partial lands.

### Step 4: Verify and hand back

Confirm the engine reported the eject commit and that `python .github/scripts/validate-system.py` is green. Tell the developer the reversal path: one `git revert` of the eject commit restores the pre-eject tree. Suggest reviewing the reset `README.md` and memory digest, which now carry new-project skeletons to fill in.

## Revising a prior eject

Eject is not re-runnable; the marker files and removed paths are gone. To adjust afterward: revert the eject commit, make the change (for example, flip the scaffolder decision), and run the skill again from the preview step.
