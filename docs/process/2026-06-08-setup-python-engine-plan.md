# Setup Python Engine Implementation Plan

Date: 2026-06-08
Status: Done (scope expanded, see note below)
Governing ADR: `adr-scaffold-introduce-ah-ide-cli` (Amendment 2026-06-08)

**Scope update (2026-06-08).** This plan first proposed keeping thin `.sh`/`.bat` shims over the Python engine. The decision then went further: remove every shell and batch wrapper from the template, with the git pre-commit hook as the only exception, since git must run it as a shell script. What shipped is the Python engine `repository-setup.py` invoked directly as `python .github/scripts/setup/repository-setup.py`, the `ah-ide`/`sync` wrappers and `.bootstrap/` scripts deleted, and the scaffolder and sync invoked as `python .github/scripts/scaffold.py` / `python .github/scripts/sync-claude-rules.py`. The phases below describe the original shim plan; read "thin shims" as "deleted" and "invoke `./ah-ide`" as "invoke `python .github/scripts/scaffold.py`". The ADR amendment is the current record.

Repository setup runs as `repository-setup.sh` with a `.bat` twin, roughly 240 lines each kept in parity. It edits `~/.bashrc`, `~/.zshrc`, and the Windows user environment to put the repo root on PATH. That out-of-repo write is the part a developer audits before trusting the script, and the dual-dialect logic contradicts the wrappers-stay-thin principle the scaffolder follows. This plan moves setup into a stdlib-only Python engine and drops the PATH editing. It lands in three phases. Each phase has exit criteria; no phase starts until the prior one meets them.

## What stays the same

- The two setup modes: activate-in-place (run from inside a "Use this template" clone) and scaffold (run pointing at an empty or non-git directory).
- Git-hook installation: `git config core.hooksPath .github/hooks`, the executable bit on the hook, and the disclosed `.git/hooks` compatibility symlink for clients that ignore `core.hooksPath`.
- The closing actions of activate: run `sync-claude-rules.py`, then `validate-system.py`, then the `ah-ide` smoke check, each degrading to a warning rather than aborting.
- `ah-ide` itself, invoked from the clone as `./ah-ide` or `.\ah-ide.bat`, or as `python .github/scripts/scaffold.py`.

## What changes

- Setup logic moves to `.github/scripts/setup/repository-setup.py`, stdlib only, cross-platform, the single implementation for both operating systems.
- `setup.sh`, `setup.bat`, and `repository-setup.sh` / `.bat` become bootstrap shims: locate Python 3, exec the engine, forward arguments. No logic beyond Python discovery.
- PATH registration is removed. Setup never edits a shell rc file or the Windows environment. The engine carries a `--remove-path` migration that strips entries an earlier setup wrote, so an existing clone can clean up.
- Setup gains `--dry-run`, parity with eject: it prints every action it would take and changes nothing.
- File copying in scaffold mode uses `shutil` (`copytree` with an ignore filter) in place of `rsync`, removing the `rsync` dependency.

## Cross-cutting constraints

- The engine is stdlib only and fails early on a missing prerequisite (git, Python 3.10+), matching the existing scripts and the rest of the pipeline.
- No setup path writes outside the repository tree. This is the trust property the whole change exists to establish; a write to a shell rc file or system environment is a defect.
- harness-eject removes setup machinery as Category A. When the script names change, the eject manifest and the `validate-system.py` drift check must change in the same commit, or eject's closing validate gate will fail.
- The `validate-system.py` `.bat` / `.sh` parity check still expects `setup.sh` paired with `setup.bat`. The shims keep that pair.

## Phase 1: Python setup engine with mode parity

Goal: `repository-setup.py` reproduces both setup modes, minus the PATH editing, behind thin shims. Effort: medium.

1. Port the engine. Prerequisite checks, mode detection (`SRC == TARGET` is activate-in-place, else scaffold), `activate()` (hook config, executable bit, compatibility symlink, sync, validate, smoke check), and scaffold-mode file copy via `shutil`. Refuse scaffold into an existing git repo, as the bash script does.
2. Thin the shims. `setup.sh`, `setup.bat`, `repository-setup.sh`, and `.bat` reduce to Python discovery plus exec, forwarding arguments.
3. Drop PATH registration. Remove `register_path`. Add `--remove-path` that strips a prior setup's rc and Windows-environment entries and reports what it removed.
4. Add `--dry-run`. Every create, copy, config, and hook action prints under dry-run and makes no change.

Exit: on a throwaway empty directory, scaffold mode reproduces the tree the old setup produced minus PATH edits; on a clone, activate-in-place configures the hook and runs sync and validate; `--dry-run` changes nothing; `--remove-path` clears a planted rc entry. No run touches a shell rc file or the Windows environment.

## Phase 2: Retire PATH from docs and align harness-eject

Goal: nothing instructs a user to rely on a bare `ah-ide` on PATH, and eject still removes setup cleanly. Effort: small.

1. Update setup docs and READMEs to invoke `ah-ide` as `./ah-ide` from the clone. Remove the "added to PATH" guidance.
2. Update the eject manifest Category A to list `repository-setup.py` alongside the shims, and update the `validate-system.py` drift check accordingly.
3. Re-sync `CLAUDE.md` from `copilot-instructions.md` if any synced reference changed, and confirm the two gated files (`system-index.md`, `copilot-instructions.md`) carry no stale setup reference.

Exit: `validate-system.py` exits zero; no doc tells a user to call `ah-ide` by bare name; an eject `--dry-run` on a test clone lists the new setup paths under Category A.

## Phase 3: Verification

Goal: prove the engine on a real instantiation with zero out-of-repo writes. Effort: small.

1. Fresh clone. Run setup in activate-in-place mode; confirm the hook is active, sync and validate pass, and `./ah-ide help` works.
2. Scaffold mode. Run setup pointing at an empty directory; confirm the copied tree matches and the hook is active.
3. Out-of-repo check. After both runs, confirm `~/.bashrc`, `~/.zshrc`, and the Windows user environment are untouched. Run `--remove-path` on a machine carrying a stale entry and confirm it is removed.
4. Eject intact. Run harness-eject `--dry-run` and confirm it still targets the setup machinery.

Exit: both setup modes pass with zero writes outside the repository tree, the `--remove-path` migration is verified, and harness-eject is unaffected.
