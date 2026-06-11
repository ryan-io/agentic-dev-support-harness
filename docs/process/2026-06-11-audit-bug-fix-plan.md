# Audit Bug-Fix Plan

Status: Implemented 2026-06-11, all six phases. Evidence counts on the two detector-4 instincts and their proposals were halved (12 to 6, 6 to 3; yml proposal priority recomputed 4 to 3). The validator's hook check now requires PreToolUse to be absent. New suite: `.github/scripts/learning/tests/test_event_policy.py`. Verification: validate-system.py 567 PASS / 0 FAIL / 0 WARN; 145 tests across seven suites pass; mirror bodies byte-identical to sources.

Date: 2026-06-11

Scope: fixes for the eight bugs (B1-B8) from `docs/audit/2026-06-10-system-review.md`. Ordered by the audit's own leverage ranking: evidence math first (it gates the open verification windows from `memory.md`), then concurrency and filter bugs, then the update-engine check, then cosmetics. Inconsistencies, gaps, and features from the same audit are out of scope here.

## Cross-cutting constraints

Pipeline Python stays stdlib-only and fails closed; hooks always exit 0. Tests go in `.github/scripts/learning/tests/` (or `.github/scripts/tests/` for `update.py`), temp filesystem only. Do not hand-edit `.claude/rules/` mirrors; edit sources under `.github/instructions/` and run `sync-claude-rules.py`. Changes to `.claude/settings.json` hook registration touch a load-bearing path; flag in the PR. Run `validate-system.py` and all six suites after each phase.

## Phase 1: One event-recording policy (B1)

Adopt the audit's R2 recommendation rather than patching detectors one by one: record tool observations on PostToolUse only. Remove the PreToolUse `observe.py` registration from `.claude/settings.json` (keep any non-tool hooks). Delete the now-dead PostToolUse filters in `detect_repeated_sequences` and `detect_corrections`, or convert them to a shared assert-style helper so a future second hook fails loudly instead of doubling counts again.

Data correction: existing instinct evidence counts are inflated for detectors 4 and 5. Halve `evidence_count` on instincts minted by `detect_file_conventions` and `detect_rule_consultation` (the live `place-json-files-in-github-scripts` instinct goes 12 to 6), or annotate them for the developer to re-confirm via `continuous-learning`. Note the choice in the commit body.

Tests: one fixture asserting a Pre/Post duplicated log no longer double-counts, one asserting the `total < 3` floor needs three real events.

## Phase 2: Decay and reinforcement math (B3, B4)

B3: make decay idempotent per stale window. Record applied decay on the instinct (for example `decay_applied_through: <session>`), compute decay only for windows after that mark, and update the mark when decay lands. Two propose runs in the same stale window must subtract once.

B4: stop the archive-and-recreate churn. Implement the reinforcement the `propose.py` docstring already claims (the audit's F4): when `analyze.py` reinforces an instinct with a pending proposal, bump a `reinforced_session` field on the proposal, and have proposal staleness read that instead of `created_session`. Then make `proposal_exists()` also see archived proposals, or record archived IDs so a hot instinct cannot immediately re-promote.

These two share the session-clock model; implement against `session_clock.py` primitives. Tests: decay applied twice in one window equals once; reinforced proposal does not archive; archived proposal does not resurrect while unreviewed.

## Phase 3: Evidence merge on reinforcement (B2)

In `analyze.py` `save_instinct`, merge prior evidence with the new batch instead of rebuilding from the new batch alone, capped (keep the most recent N entries, N around 10) so instinct files stay bounded. Test: reinforce an instinct twice with distinct evidence, assert both batches survive up to the cap.

## Phase 4: Concurrency and filter hygiene (B5, B6)

B5: route the `_analysis_marker` append through `observe.py`'s locked-append helper. For the rotation race, write the marker only if the observation file still contains the batch tail analyze just processed; otherwise skip (fail closed, worst case is re-analysis suppressed rather than doubled). Document the chosen behavior in a comment.

B6: extend `is_self_observation` to scan Bash `command`, Grep, and Glob inputs for `.claude/learning/` fragments, not just `file_path`. This overlaps the Phase 3 item in the 2026-06-08 remediation plan; implement once, satisfy both.

Tests: a `cat .claude/learning/...` Bash call is filtered; a marker append under a concurrent locked writer does not interleave (lock acquisition test).

## Phase 5: Update-engine conflict check (B7)

In `update.py` `cmd_finish`, store the conflicted paths from the merge run in `.git/harness-update-pending.json` and scan only those for `<<<<<<<`. A merge-set doc that legitimately contains conflict markers must no longer block `--finish`. Test in `.github/scripts/tests/test_update.py`: pending file with zero conflicts finishes even when another merge-set file contains the marker string.

## Phase 6: Sync cosmetic (B8)

Drop the duplicate `\n` in the `sync-claude-rules.py` output template (line 129) so mirror bodies are byte-identical to sources after frontmatter. Re-run sync to regenerate all mirrors; expect a one-blank-line diff per mirror. Do this last so earlier phases do not collide with a full-mirror regeneration commit.

## Verification

After each phase: `python3 .github/scripts/validate-system.py` exits 0; all suites pass (118 tests plus the new ones). After Phase 1, confirm a session produces exactly one observation per tool call. After Phase 6, diff each mirror against its source and confirm bodies match byte for byte, then confirm the `system-review` naive-diff check passes. Close out by re-checking the audit's B-table against the codebase and marking each finding fixed with its commit.
