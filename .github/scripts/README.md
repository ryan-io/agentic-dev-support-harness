# Scripts

Python automation that keeps the harness coherent. Two scripts run on every commit, one on every PR, one on a weekly schedule, one on merge to main, the learning pipeline on agent hook events, and one (`scaffold.py`, the `ah-ide` engine) on demand from the command line. The pre-commit git hook (`../hooks/pre-commit`) is the only shell script; everything here is invoked through Python.

## sync-claude-rules.py

The keystone. Copies `../copilot-instructions.md` to `CLAUDE.md` with line-ending and BOM normalization, and transforms each `../instructions/*.instructions.md` into a `.claude/rules/*.md` mirror, converting `applyTo` frontmatter to `paths`, stripping the suffix from the filename. Validates each instruction file's frontmatter, body, and character count (≤ 4,000). Skips files prefixed with `<!-- DEPRECATED` and cleans orphaned mirrors. Runs from the pre-commit hook (`../hooks/pre-commit`) and directly via `python .github/scripts/sync-claude-rules.py`.

## validate-system.py

PR-time guardrail. Confirms that the synced files are in sync (no manual edits to `.claude/rules/`), all instruction files parse, all skills declare a description, and cross-references resolve to existing files. Invoked by `../workflows/validate-system.yml`. Uses an `@lru_cache` read-once cache so each file is read at most once per run. Supports `--changed file1 file2 ...` for incremental mode: maps each changed file to the relevant validation sections and skips the rest. The pre-commit hook passes staged files automatically. CI runs without `--changed` for full validation.

## eject.py

The `harness-eject` engine. Trims template-only machinery from a clone once a downstream project has run `project-setup`. Reads `eject-manifest.json`, which sorts removable paths into Category A (one-time setup, removed), B (the scaffolder, removed unless `--keep-scaffolder`), and C (template-authored content reset to the consuming project); everything else is kept. The keep-set guard refuses to act on any path under a `protected_roots` entry, so the governance layer can never be stripped. Two run-context guards gate execution: the `.claude/setup-complete` marker must exist and `.github/TEMPLATE_SOURCE` must not, so eject cannot run in the template source. Phase 0 ships read-only `--list` and `--check`; the destructive run lands in Phase 1. Decision record: `../../docs/adr/adr-setup-introduce-harness-eject.md`.

## update.py

The `harness-update` engine. Pulls harness improvements from the template into an adopted project. Reads the committed anchor (`../harness-version.json` at the repo's `.github/` root: source URL plus last-applied commit), clones the source, diffs anchor to target, and applies each changed file per `update-manifest.json`: the overwrite set is applied directly, the merge set goes through `git merge-file` three-way merges with the anchored version as base, excluded and out-of-scope paths are skipped, and locally deleted files are never resurrected. `--check` and `--dry-run` are read-only; `--run` applies, runs the sync-and-validate gate, bumps the anchor, and lands one revertable commit; conflicts stop before the commit and `--finish` completes after resolution. Refuses on the `.github/TEMPLATE_SOURCE` sentinel and on a dirty tree. Decision record: `../../docs/adr/adr-setup-add-harness-update-mechanism.md`.

## bootstrap-update.py

One-time installer for the update mechanism into a project adopted before the mechanism existed (audit G1). Run from a harness clone: `python .github/scripts/bootstrap-update.py --target <path> [--anchor <sha>] [--record-source <url>]`. Installs `update.py`, `update-manifest.json`, and the `harness-update` and `harness-eject` skills into the target, never overwriting an existing file, then writes the `.github/harness-version.json` anchor (`--anchor` resolves in the harness clone, default HEAD; `--record-source` defaults to the clone's path). Refuses on a `.github/TEMPLATE_SOURCE` target, a target without `.github/`, or an existing anchor. Prints the consumer-side registration checklist; it never edits consumer prose. Setup-side machinery: excluded from updates and removed by eject (Category A).

## scaffold.py

The `ah-ide` CLI engine. Scaffolds a base solution from a template under `../../templates/` into the caller's current directory (default; `--out` overrides): copies the tree, renames the manifest-declared token to `--name`, and includes IDE assets per `--ide` (vscode, vs2026, both). For templates that declare a `test_frameworks` block, `--test-framework` selects the test project (C#: NUnit, xUnit, MSTest; default NUnit), overlaid from the template's `_testfw/<Framework>/` subtree (`docs/adr/adr-scaffold-add-test-framework-dimension.md`). Stacks are data; adding one is a new template directory with a `manifest.json`, never an engine change. Each scaffold writes a receipt (`.ah-ide-scaffold.json`) with content hashes; the `undo` subcommand removes the most recent scaffold from that receipt, refusing if files were modified since (unless `--force`). Invoked through Python as `python .github/scripts/scaffold.py <stack> --name <Name>`; no shell or batch wrapper ships. Templates resolve relative to the engine, not the caller. `python .github/scripts/scaffold.py help` prints a manifest-driven command overview. Decision record: `../../docs/adr/adr-scaffold-introduce-ah-ide-cli.md`.

## setup/

The repository-setup engine, `repository-setup.py`: a stdlib-only, cross-platform Python script invoked as `python .github/scripts/setup/repository-setup.py`. No shell or batch wrapper ships (ADR-SCAFFOLD Amendment 2026-06-08); the pre-commit git hook is the template's only shell script. The engine auto-detects two modes. Run from inside an already-populated repo (the GitHub template-feature case), it activates in place: configures the hook path, makes the hook executable, installs a `.git/hooks` compatibility symlink, then runs sync, system validation, and the ah-ide smoke check; nothing is copied. Given a target directory, it git-inits there, copies the template files, then activates the same way. It checks prerequisites first (git, Python 3.10+), supports `--dry-run` to preview every action, and makes no changes outside the repository. `--remove-path` is a migration that strips PATH entries a superseded setup wrote. This `setup/` machinery is removed by `harness-eject` once a project is bootstrapped.

## tests/

Stdlib `unittest` tests for the top-level scripts. `test_eject.py` covers the `eject.py` manifest loading and keep-set guard; `test_update.py` covers the `update.py` engine against temp git fixtures (classification, anchor, dry-run, overwrite, three-way merge, conflicts and `--finish`, guards, revert); `test_repository_setup.py` covers the `setup/repository-setup.py` engine: template copy, dry-run, the `--remove-path` migration, and that setup writes nothing outside the repository; `test_bootstrap_update.py` covers the `bootstrap-update.py` installer against temp fixtures (install set, anchor, collision skip, dry-run, guards); `test_sync_log_rotation.py` covers the sync-log cap (G6) by running `sync-claude-rules.py` against a temp repo. Run from the repo root: `python .github/scripts/tests/test_eject.py` and `python .github/scripts/tests/test_repository_setup.py`. The learning pipeline keeps its own fixtures under `learning/tests/`.

## learning/

The continuous-learning pipeline: `observe.py` (hook handler, transcript correction capture, explicit `#correction` marker), `analyze.py` (detectors plus relevance and contradiction passes), `propose.py` (promotion, session-clock staleness, quality gate), and `session_clock.py` (shared session-counter, config-migration, and permanence primitives). Fixture tests live in `learning/tests/`. See `learning/README.md` for the detail.

## Related

- [Git hooks](../hooks/README.md): what triggers sync and validation on commit.
- [Learning pipeline](learning/README.md): the observe, analyze, and propose scripts.
- [Instruction files](../instructions/README.md): the source the sync script mirrors.
- [Scaffolding templates](../../templates/README.md): what `scaffold.py` consumes.
- [`.claude/`](../../.claude/README.md): the mirror and learning data these scripts write.
