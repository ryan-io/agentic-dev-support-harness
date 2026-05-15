# Pytest Test Suite Adoption Plan

Date: 2026-06-08
Status: Planned (not started)
Governing ADR: pending (Phase 1 drafts "Introduce pytest as the test runner")

The repo has real Python logic across the setup engine, scaffolder, eject, validator, sync, and learning pipeline, plus 5 `unittest.TestCase` test files. There is no unified runner: tests run one file at a time via `python <file>.py`, nothing runs them in CI, and three scripts have zero tests (`scaffold.py`, `validate-system.py`, `sync-claude-rules.py`). This plan stands up pytest as the single runner, migrates the existing tests, fills the untested-script gaps first, and gates PRs with a CI job. Each phase has exit criteria; no phase starts until the prior one meets them.

Decisions confirmed with the developer:

- Migrate all 5 existing files to pytest idioms, not a thin runner-over-unittest wrapper.
- Prioritize new coverage for the 3 untested scripts; wire existing tests in during the migration.
- Add a pytest CI job; leave the pre-commit hook unchanged so commits stay fast.

## Cross-cutting constraints

These hold in every phase.

- Dependency boundary: runtime and hook code stay stdlib-only. pytest is confined to test execution and CI. The fails-closed property of the hook scripts is not touched.
- A third-party dependency requires an ADR (`pattern-fidelity`, `agent-guardrails`). Phase 1 produces it and gates the rest.
- Instruction files are not hand-edited. Documenting pytest as the Python test runner routes through the `continuous-learning` pipeline with developer approval, not a direct edit.
- Two test tiers per `testing.md`: unit (pure functions, temp filesystem only) and integration (`@pytest.mark.integration`, spawns a subprocess against a fixture repo). The monolithic scripts whose logic lives inline in `main` are covered at the integration tier.
- Hyphenated filenames (`repository-setup.py`, `validate-system.py`, `sync-claude-rules.py`) load via the shared `importlib.util.spec_from_file_location` helper, centralized in conftest.

## Phase 1: ADR and sign-off

Goal: record the dependency decision before any code. Effort: hours.

Run the `adr-creation` skill to draft "Introduce pytest as the test runner." Record the dependency boundary, the rationale for pytest over bare `unittest` (discovery, fixtures, parametrize, one runner), and that `requirements-dev.txt` pins it.

Exit criteria: ADR drafted, reviewed, and Active. No test or config code is written before this.

## Phase 2: Config and scaffolding

Goal: pytest can discover and load every module. Effort: hours.

New files:

- `pyproject.toml` (repo root): `[tool.pytest.ini_options]` with `testpaths = [".github/scripts/tests", ".github/scripts/learning/tests"]`, `python_files = "test_*.py"`, `addopts = "-ra"`, and `markers = ["integration: spawns a subprocess or builds a fixture repo"]`.
- `requirements-dev.txt` (repo root): pin `pytest` (e.g. `pytest==8.*`). Dev and CI only.
- `.github/scripts/tests/conftest.py`: shared fixtures `repo_root`, a `load_script(relpath, modname)` importlib loader, and module fixtures (`rs`, `scaffold_mod`, `eject_mod`).
- `.github/scripts/learning/tests/conftest.py`: fixtures for `observe`, `analyze`, `propose`, `session_clock`, plus the temp-learning-dir and transcript setup currently duplicated in `TempLearningDirMixin` and `TranscriptMixin`, re-expressed as fixtures.

Exit criteria: `python -m pytest --collect-only` discovers across both testpaths with no import errors.

## Phase 3: Migrate the 5 existing files

Goal: existing coverage runs under pytest, intent preserved. Effort: half a day.

Same conversions across all five files:

- `unittest.TestCase` classes to plain `test_*` functions.
- `setUp`/`tearDown` plus `tempfile.mkdtemp` to the `tmp_path` and conftest fixtures.
- `redirect_stdout(io.StringIO())` to `capsys`.
- Manual `HOME` save and restore to `monkeypatch.setenv`.
- `@unittest.skipIf` to `@pytest.mark.skipif`.
- `self.assertX` to plain `assert`.
- Repetitive dry-run vs real cases to `@pytest.mark.parametrize`.

Files: `.github/scripts/tests/test_repository_setup.py`, `.github/scripts/tests/test_eject.py`, `.github/scripts/learning/tests/test_corrections.py`, `.github/scripts/learning/tests/test_fidelity.py`, `.github/scripts/learning/tests/test_staleness.py`.

This is a translation, not a rewrite of what is checked. After migration the files no longer run via `python file.py`; the run command becomes `python -m pytest`. Update each module docstring's "Run from repo root" line.

Exit criteria: every previously-passing assertion passes under pytest; assertion count is preserved or accounted for.

## Phase 4: New coverage for the untested scripts

Goal: close the three zero-coverage gaps. Effort: one day.

- `.github/scripts/tests/test_scaffold.py`: unit tests for `load_templates`, `excluded_ide_roots`, `resolve_test_framework`, `is_text_file`, `sha256_of`, `read_receipt`/`write_receipt` round-trip, `predict_empty_dirs`, `_within_out_dir` (path-escape guard), and `scaffold()` against a small temp template tree asserting the receipt. One integration test: `main()` dry-run creates nothing.
- `.github/scripts/tests/test_validate_system.py`: unit tests for `read_file`, `compute_active_sections`, `should_run`, `result`. Integration: run `validate-system.py` via subprocess against the real repo (exit 0), and against a temp repo with one injected violation (non-zero plus the message).
- `.github/scripts/tests/test_sync_claude_rules.py`: integration. Run the sync against a temp source tree; assert `CLAUDE.md` is a verbatim copy of `copilot-instructions.md`, the `.claude/rules/` frontmatter transform is applied, and the over-4000-character guard fails as designed.

Exit criteria: each of the three scripts has at least one unit or integration test exercising its primary path and one failure path.

## Phase 5: CI

Goal: tests gate PRs. Effort: hours.

- `.github/workflows/python-tests.yml` (new): mirror `validate-system.yml`. Checkout, `actions/setup-python@v5` (3.12), `pip install -r requirements-dev.txt`, then `python -m pytest`. Same triggers (push to main, PRs, dispatch). A separate workflow keeps validation and tests independently legible. The pre-commit hook is untouched.

Exit criteria: the job runs on a test branch and gates the PR; both tiers execute in CI.

## Phase 6: Governance and docs

Goal: register the change in the system map. Effort: hours.

- `.github/docs/system-index.md` (edit): register the new files (`pyproject.toml`, `requirements-dev.txt`, `python-tests.yml`, both `conftest.py`, the new test files) and add a short testing entry. This file is a docs map, editable directly.
- Documenting "pytest is the Python test runner" belongs in a `python-code-standards.instructions.md` (none exists today). Route that through the `continuous-learning` pipeline as a follow-up, not a hand-edit.
- Project memory updates go through the `continuous-learning` skill.

Exit criteria: `python .github/scripts/validate-system.py` exits 0 with the new files present; system-index reflects them.

## Verification

1. `python -m pytest` from repo root: full suite green (migrated and new).
2. `python -m pytest -m integration` and `-m "not integration"`: both selections run.
3. `python -m pytest --collect-only`: discovery across both testpaths.
4. `python .github/scripts/validate-system.py`: exits 0 after the new files land.
5. Migrated files no longer rely on `python file.py`; docstrings reflect the `pytest` command.
6. Push a branch; the `python-tests.yml` job runs and gates the PR.

## Out of scope

- Expanding learning-pipeline coverage beyond translating the existing tests.
- Coverage tooling (`pytest-cov`), pre-commit test integration, and the `python-code-standards` instruction file. All deferred follow-ups.
