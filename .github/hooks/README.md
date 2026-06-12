# Hooks

Git hooks that fire on local repository events. Two configurations live here, governed by different mechanisms.

## pre-commit

Runs the sync script and the system validator on every commit. If sync fails, validation fails, or any invariant is violated, the commit is rejected with the failure reason printed. Sync is skipped when nothing it depends on changed: the hook hashes the instruction sources, the hub, the generated mirrors, and the sync script itself, so even a forbidden hand-edit to a mirror triggers a regenerating resync. The hook is POSIX shell and works on macOS, Linux, and Windows (Git Bash) without modification.

The hook is installed automatically by setup (`python .github/scripts/setup/repository-setup.py`, run from inside the repo), via `git config core.hooksPath .github/hooks`. This applies to repos created from the GitHub template too, the template feature copies files but cannot set git config, so the activation step is required per clone. If you skipped setup, run that one command from the repo root and the hook becomes active.

## Claude Code learning hooks

The continuous-learning hooks (PostToolUse / SessionStart / SessionEnd / UserPromptSubmit) are not git hooks and do not live here. Claude Code loads them from `.claude/settings.json`, the only place it reads hook config. See `../scripts/learning/README.md`.

## Using the pre-commit hook with GitKraken

GitKraken Desktop surfaces hook output directly in the commit dialog. When the hook prints, you'll see the same `[1/2] Syncing...` and `[2/2] Validating...` sections you'd see in a terminal. On failure, GitKraken displays the error and refuses the commit until the issue is fixed or you click **Commit and skip hooks** in the commit panel.

Two GitKraken-specific things to know. First, on macOS and Linux the hook file must be marked executable (`chmod +x .github/hooks/pre-commit`), without that, GitKraken errors with exit code 126. Second, GitKraken does not honor `core.hooksPath`, so setup also symlinks the hook into `.git/hooks/pre-commit`. If you skipped setup and use GitKraken, create that symlink yourself.

GitKraken's official documentation on hooks: https://help.gitkraken.com/gitkraken-desktop/githooks/

## Using the pre-commit hook from the CLI

No special configuration needed beyond setup having run (`python .github/scripts/setup/repository-setup.py`). To bypass for one commit (emergency hotfix, work-in-progress save):

    git commit --no-verify

To disable hooks entirely for the repository:

    git config --unset core.hooksPath

To re-enable:

    git config core.hooksPath .github/hooks

## What the hook does, step by step

1. Resolves the repo root via `git rev-parse --show-toplevel`.
2. Picks `python3` if available, else `python` (handles macOS/Linux vs Windows Git Bash).
3. Runs `.github/scripts/sync-claude-rules.py` (skipped when the sync hash is unchanged): regenerates `CLAUDE.md` and `.claude/rules/` from the canonical sources.
4. Stages any files the sync regenerated so they're part of the commit.
5. Runs `.github/scripts/validate-system.py`: checks frontmatter, char limits, cross-references, hook config, learning config, Python syntax, workflow YAML, and pipeline chain integrity.
6. Exits 0 on success, 1 on any failure.

Total runtime is typically under two seconds.

## Related

- [Scripts](../scripts/README.md): the sync and validate scripts the pre-commit hook runs.
- [Learning pipeline](../scripts/learning/README.md): the Claude Code hooks loaded from `.claude/settings.json`.
- [Instruction files](../instructions/README.md): what the validator checks.
