# Scripts

Python and shell automation that keeps the harness coherent. Two scripts run on every commit, one on every PR, two on schedules, and three more on agent tool calls.

## sync-claude-rules.py

The keystone. Copies `../copilot-instructions.md` to `CLAUDE.md` byte-for-byte and transforms each `../instructions/*.instructions.md` into a `.claude/rules/*.md` mirror, converting `applyTo` frontmatter to `paths`, stripping the suffix from the filename. Validates each file's frontmatter, body, and character count (≤ 4,000). Runs from the pre-commit hook (`../hooks/pre-commit`) and from `sync.bat` at the repo root.

## validate-system.py

PR-time guardrail. Confirms that the synced files are in sync (no manual edits to `.claude/rules/`), all instruction files parse, all skills declare a description, and cross-references resolve to existing files. Invoked by `../workflows/validate-system.yml`.

## setup/

The two repository-setup scripts (`.sh` and `.bat`). They auto-detect two modes. Run from inside an already-populated repo (the GitHub template-feature case), they activate in place: configure the hook path, make the hook executable, run an initial sync, copy nothing. Run pointing at an empty directory, they git-init it, copy the template files, then activate the same way. The root-level `setup.sh` / `setup.bat` are thin shims that exec these.

## learning/

The three-stage continuous-learning pipeline, `observe.py`, `analyze.py`, `propose.py`. See `learning/README.md` for the detail.
