# Audit Gap-Fix Plan

Status: Implemented 2026-06-11, all six phases plus the consumer application. New suites: `.github/scripts/tests/test_bootstrap_update.py` (11 tests) and `test_sync_log_rotation.py` (3); the three resolved proposals moved to `proposals.archive/`. Verification: validate-system.py 569 PASS / 0 FAIL / 0 WARN; 168 tests across nine suites pass. unity-greenfield bootstrapped at anchor 9bb830c (its commit e419f83; validator there 523 PASS / 0 FAIL after restoring its missing `.claude/setup-complete` marker).

Date: 2026-06-11

Scope: fixes for the six gaps (G1-G6) from `docs/audit/2026-06-10-system-review.md`. Companion to `2026-06-11-audit-bug-fix-plan.md` (B1-B8, implemented) and `2026-06-11-audit-inconsistency-fix-plan.md` (I1-I8, planned). Ordered by the audit's leverage ranking: the update bootstrap first (it also unblocks the unity-greenfield drift), then the sentinel lockout and proposal accumulation, then the three low hygiene items. Feature candidates F1-F3 stay out of scope.

Approach decisions, confirmed by the developer 2026-06-11: G1 ships as a standalone bootstrap script, not a documented manual procedure. G2 excludes the sentinel from the downstream copy paths rather than teaching the engines a smarter refusal message. All six gaps land in one pass, and the new bootstrap is applied to unity-greenfield in the same session.

## Cross-cutting constraints

Engine Python stays stdlib-only; learning-pipeline code fails closed and hooks always exit 0. Tests go in `.github/scripts/tests/` for setup-path engines and `.github/scripts/learning/tests/` for pipeline code, temp filesystem only. Never hand-edit `.claude/rules/` mirrors. `.github/hooks/pre-commit` and `.claude/settings.json` are load-bearing paths; flag changes in the PR. Run `validate-system.py` and all seven suites after each phase.

## Phase 1: Update bootstrap script (G1)

New `.github/scripts/bootstrap-update.py`, run from a harness clone and pointed at a consumer: `python .github/scripts/bootstrap-update.py --target <path> [--anchor <sha>] [--record-source <url>]`. It installs the update mechanism into a project adopted before the mechanism existed: `update.py`, `update-manifest.json`, and the `harness-update` and `harness-eject` skills, never overwriting an existing file (the adopt collision policy). It resolves `--anchor` (default HEAD) via `git rev-parse` in the harness clone and writes `.github/harness-version.json` in the `update.py` anchor format, recording `--record-source` (default: the harness clone path) as the source. It refuses when the target carries `.github/TEMPLATE_SOURCE` or has no `.github/` directory, and finishes by printing the consumer-side registration checklist: hub On-Demand list, `system-index.md`, skills README, then commit.

Classification: the script is setup-side machinery. Add it to the update manifest `exclude` list and to the eject manifest Category A (one-time init machinery).

Tests: new `.github/scripts/tests/test_bootstrap_update.py`. Fresh target gets all four artifacts and a valid anchor; existing files survive untouched; template-source target is refused; missing `--anchor` resolves to the clone HEAD.

## Phase 2: Sentinel off the copy paths (G2)

Add `TEMPLATE_SOURCE` to the `.github` ignore set in `repository-setup.py` `TREE_COPIES`. Both copy paths (scaffold `copy_template`, adopt `overlay_template`) share that set, so one edit covers both. The GitHub-template and activate-in-place paths still carry the sentinel because no copy runs there; the `project-setup` Step 7 removal stays for them. Reword that step and the adopt next-steps banner to "remove if present: only template clones still carry it". The `setup-complete` marker continues to gate eject on its own.

Tests in `test_repository_setup.py`: scaffold into a temp target delivers no `.github/TEMPLATE_SOURCE`; adopt over a temp project delivers none either.

## Phase 3: Resolved proposals leave the tracked directory (G3)

`propose.py` gains `archive_resolved_proposals()`: move every proposal with `status: applied` or `status: rejected` from `proposals/` to `proposals.archive/` (gitignored), stamping `archived_reason: applied|rejected` via the existing `record_archive_reason`. Run it in `main` before the staleness pass. `proposal_exists` already scans the archive (B4), so a rejected instinct does not immediately re-promote; that is the desired behavior. Update the `continuous-learning` skill: the apply and reject steps note the file is archived on the next pipeline run, and the wrap-up step reports archive counts.

Data migration: the two rejected proposals from 2026-06-01 and the applied `skill-post-save-revision` move to the archive; `proposals/` keeps the two pending ones and `.gitkeep`. The deletions are tracked; the archive copies are local.

Tests in `.github/scripts/learning/tests/`: applied and rejected files move with a reason stamped; pending files stay; the move is idempotent.

## Phase 4: Pre-commit hash coverage (G4)

Extend the `CURRENT_HASH` computation in `.github/hooks/pre-commit` to also hash `.claude/rules/*.md`, `CLAUDE.md`, and `sync-claude-rules.py` (both the md5sum and md5 branches). A hand-edited mirror or a changed sync script then invalidates the hash, sync reruns, and the regeneration overwrites the drift. No Python test (the hook is bash); verify manually by touching a mirror and confirming the hook reruns sync.

## Phase 5: Detector-3 instinct dedup (G5)

In `analyze.py` `detect_error_recovery`, template the action as `Recover failed {failed_tool} with {resolution_tool}` and move the `input_summary[:80]` detail into the evidence line. The action is the instinct ID, so recoveries of the same tool pair now merge into one instinct instead of minting a sibling file per distinct command, which is the no-volatile-label rule detector 1 already states.

Test: two failure-recovery pairs with the same tools but different commands yield instincts with identical IDs, and both commands survive in evidence after the B2 merge.

## Phase 6: Sync log rotation (G6)

`sync-claude-rules.py` appends to `.claude/sync_log.txt` without bound. Before appending, when the file exceeds 256 KB, rewrite it to its most recent half (split on run-boundary blank lines, keep whole runs) with a one-line truncation notice at the top. Wrap the rotation in a try/except OSError so a failed rotation never blocks a sync. Local and gitignored, so no migration.

Test: a synthetic oversized log rotates to under the cap, keeps the newest runs, and a normal-size log is untouched.

## Consumer application

After Phase 1 lands, run the bootstrap against unity-greenfield with `--anchor 9bb830c` (the harness commit nearest its 2026-06-10 07:54 adoption) and `--record-source /home/ryan/internal-source/projects/agentic-dev-support-harness`. Then complete the consumer-side checklist there: register `harness-update` and `harness-eject` in its hub On-Demand list, `system-index.md`, and skills README; run its sync script and validator; commit. The first `harness-update` run stays a separate, developer-driven session since the approximate anchor can surface conflicts.

## Verification

After each phase: `python3 .github/scripts/validate-system.py` exits 0 and all suites pass (145 tests plus additions). After Phase 1, the bootstrap dry-runs cleanly against a scratch copy of unity-greenfield. After Phase 2, a scaffold and an adopt into temp targets carry no sentinel. After Phase 3, `git status` shows only deletions under `proposals/` and the archive holds the three resolved files. Close out by re-checking the audit's G-table and marking each finding fixed with its commit.
