# Hooks

Git hooks that fire on local repository events. Two configurations live here, governed by different mechanisms.

## pre-commit

Runs the sync script and the system validator on every commit. If sync fails, validation fails, or any invariant is violated, the commit is rejected with the failure reason printed. The hook is POSIX shell and works on macOS, Linux, and Windows (Git Bash) without modification.

The hook is installed automatically by `setup.sh`, `setup.bat`, and the `.bootstrap/` scripts via `git config core.hooksPath .github/hooks`. If you cloned the repo manually and skipped setup, run that one command from the repo root and the hook becomes active.

## observe.json

Configuration for Claude Code's PreToolUse / PostToolUse / Stop hooks — used by the continuous-learning pipeline, not by git. Read by Claude on session start; not invoked by git. See `../scripts/learning/README.md`.

## Using the pre-commit hook with GitKraken

GitKraken Desktop surfaces hook output directly in the commit dialog. When the hook prints, you'll see the same `[1/2] Syncing...` and `[2/2] Validating...` sections you'd see in a terminal. On failure, GitKraken displays the error and refuses the commit until the issue is fixed or you click **Commit and skip hooks** in the commit panel.

Two GitKraken-specific things to know. First, on macOS and Linux the hook file must be marked executable (`chmod +x .github/hooks/pre-commit`) — without that, GitKraken errors with exit code 126. Second, GitKraken honors `core.hooksPath`, so the `.github/hooks/` location works correctly; you do not need to symlink anything into `.git/hooks/`.

GitKraken's official documentation on hooks: https://help.gitkraken.com/gitkraken-desktop/githooks/

## Using the pre-commit hook from the CLI

No special configuration needed beyond `setup.sh` having run. To bypass for one commit (emergency hotfix, work-in-progress save):

    git commit --no-verify

To disable hooks entirely for the repository:

    git config --unset core.hooksPath

To re-enable:

    git config core.hooksPath .github/hooks

## What the hook does, step by step

1. Resolves the repo root via `git rev-parse --show-toplevel`.
2. Picks `python3` if available, else `python` (handles macOS/Linux vs Windows Git Bash).
3. Runs `.github/scripts/sync-claude-rules.py` — regenerates `CLAUDE.md` and `.claude/rules/` from the canonical sources.
4. Stages any files the sync regenerated so they're part of the commit.
5. Runs `.github/scripts/validate-system.py` — checks frontmatter, char limits, cross-references, hook config, learning config, Python syntax, workflow YAML, and pipeline chain integrity.
6. Exits 0 on success, 1 on any failure.

Total runtime is typically under two seconds.
