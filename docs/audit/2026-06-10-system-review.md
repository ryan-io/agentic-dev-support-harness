# System Review Audit: agentic-dev-support-harness

Date: 2026-06-10. Scope: full harness review per the `system-review` skill checklist plus a code-level audit of every engine script, the learning pipeline, skills, docs, and manifests. Reference consumer: `unity-greenfield` (adopted 2026-06-10). Method: ran `validate-system.py` and all six test suites, diffed every mirror against its source, read all ten Python engines line by line, swept all 15 skills and all instruction files, and cross-checked the unity-greenfield adoption against the harness source.

## Baseline: what is healthy

The automated gates are green: `validate-system.py` reports 569 PASS, 0 FAIL, 0 WARN. All six test suites pass: 118 tests across `test_corrections` (20), `test_fidelity` (14), `test_staleness` (22), `test_eject` (25), `test_repository_setup` (18), `test_update` (19).

`CLAUDE.md` is byte-identical to `.github/copilot-instructions.md`. Every `.claude/rules/` mirror matches its `.github/instructions/` source (one cosmetic exception, B8). No orphaned mirrors. All instruction files are under the 4,000-char cap. All 15 skills have correct frontmatter, are registered in all four required locations, and every CLI flag they reference exists in its engine. The design-pipeline handoffs (stages 1-4) agree on paths and ordering. All file-producing skills carry the Skill Authoring revision step.

The eject manifest covers all 12 ADRs (Category B: 2, Category C: 10). The "two eject-manifest gaps" recorded in unity-greenfield's `memory.md` open threads were fixed upstream the same day; that consumer note is now stale. `update-manifest.json` merge_set and exclude are disjoint and complete. Repo hygiene is good: `__pycache__`, template `obj/` artifacts, `sync_log.txt`, and session notices are all untracked and gitignored.

## Bugs

| ID | Severity | Location | Finding |
|----|----------|----------|---------|
| B1 | High | `analyze.py` detectors 4 and 5; `.claude/settings.json` | Every tool call is recorded twice (PreToolUse and PostToolUse hooks both run `observe.py`). `detect_repeated_sequences` and `detect_corrections` filter to PostToolUse and the comment at line 527 names the doubling artifact, but `detect_file_conventions` and `detect_rule_consultation` count all events. Evidence counts are inflated 2x and the `total < 3` floor is reached after 2 real edits. The live `place-json-files-in-github-scripts` instinct's `evidence_count: 12` likely reflects 6 writes. |
| B2 | Medium | `analyze.py` `save_instinct`, line 149 | The merge comment says "increase confidence, append evidence" but the body is rebuilt from the new batch's evidence only. Prior evidence is silently discarded on every reinforcement, so a long-lived instinct shows only its most recent supporting events at review time. |
| B3 | Medium | `propose.py` `apply_instinct_decay` | Decay is computed as `rate * windows_stale` from an unchanging `last_seen_session` and subtracted on every propose run. Two runs while two windows stale costs 0.40 of confidence, not the intended per-window 0.05. Effective decay depends on how often analyze/propose happen to fire, not on sessions elapsed, which contradicts the evidence-based staleness ADR's clock model. No record of already-applied decay exists. |
| B4 | Medium | `propose.py` archive flow plus `proposal_exists` | Archived (decayed) proposals leave `proposals/`, so `proposal_exists()` stops seeing them. An instinct still above 0.7 immediately re-promotes a fresh proposal with a new `created_session`. Result: a 30-session archive-and-recreate churn loop for any unreviewed proposal whose instinct stays hot. The docstring's "without reinforcement" has no implementation: nothing ever refreshes `created_session` or `last_reviewed` when the instinct is reinforced. |
| B5 | Low | `analyze.py` main, `observe.py` rotation | The `_analysis_marker` is appended without the lock `observe.py` uses, so a concurrent session's observation can interleave mid-record. Separately, `analyze.py` runs detached at SessionEnd while rotation runs at the next SessionStart; if rotation wins, the marker lands in the fresh file and the carried-forward "unanalyzed" tail may be analyzed twice. |
| B6 | Low | `observe.py` `is_self_observation`, lines 237-245 | The self-observation filter only checks `file_path`. Bash, Grep, and Glob calls targeting `.claude/learning/` are still recorded (command or pattern in `input_summary`), partially defeating the rule that the pipeline must not learn from its own churn. |
| B7 | Low | `update.py` `cmd_finish`, lines 485-491 | The unresolved-conflict check scans every merge_set file for `<<<<<<<` instead of the conflicted paths from the run (the pending file stores only source and target). A merge-set file that legitimately contains that string (for example a doc about git conflicts) blocks `--finish` permanently. Store the conflicted paths in `.git/harness-update-pending.json` and check only those. |
| B8 | Cosmetic | `sync-claude-rules.py`, line 129 | The output template adds `\n` before a body that already starts with `\n`, so every mirror carries one extra blank line after the frontmatter relative to its source. Harmless, but it makes the `system-review` skill's "body content must be identical" check fail a naive diff. |

## Inconsistencies

| ID | Severity | Location | Finding |
|----|----------|----------|---------|
| I1 | Medium | `project-setup/SKILL.md` lines 99-102, 116-117 | The skill still says "look for `<!-- CUSTOMIZE -->` markers" in `copilot-instructions.md` and `system-index.md`. `status.md` confirms those markers were removed. The files still need stack rows added at setup; the instructions for finding where are stale. |
| I2 | Low | `analyze.py` line 20 | Header says "Called automatically by observe.py on Stop". The session boundary is SessionEnd (per the staleness ADR and `observe.py` itself). |
| I3 | Low | `observe.py` lines 8-9, 416 | Module docstring omits the registered UserPromptSubmit hook. `handle_session_start_notice`'s docstring says "On first PreToolUse of a session" but it runs on SessionStart. |
| I4 | Low | `docs/process/2026-06-08-system-review-remediation-plan.md` lines 13, 59 | Two em dashes in section headers. The writing-voice "no em dashes" hard rule applies to process docs. Only file in the repo affected. |
| I5 | Low | `csharp-code-standards.instructions.md` (3,987 ch), `lua-code-standards.instructions.md` (3,961 ch) | Both exceed the 3,800-char trim threshold from system-index Size Management. Under the hard cap, but the policy says trim at 3,800; one accepted learning proposal could push either over 4,000 and block sync. |
| I6 | Low | `system-review/SKILL.md` | The skill never mentions `validate-system.py`. The validator automates the skill's 6 checks plus 17 more sections. An agent following the skill manually duplicates the cheap checks and skips the deep ones. Add: run the validator first, then audit what it cannot check (semantic consistency, stale guidance). |
| I7 | Low | `analyze.py` `detect_rule_consultation` | Source and mirror filenames are tracked as distinct rules (`code-standards.instructions.md` vs `code-standards.md`). Consultations of the mirror do not credit the source, so a rule read only via `.claude/rules/` can be falsely flagged "rarely consulted". |
| I8 | Low | `scaffold.py` vs testing policy | `testing.instructions.md` requires tests for new logic. The other three engines have suites; `scaffold.py` (541 lines) has none, only the `scaffold-matrix.yml` CI exercise. |

## Gaps

| ID | Severity | Finding |
|----|----------|---------|
| G1 | High | No delivery path for the update mechanism into projects adopted before it existed. unity-greenfield lacks `update.py`, `update-manifest.json`, and both lifecycle skills; the `harness-update` skill's `--anchor` bootstrap presumes the engine is already downstream. Chicken-and-egg: the update mechanism cannot deliver itself. Needs a documented one-time install step (copy engine, manifest, and skills, then bootstrap the anchor) or a standalone bootstrap script. |
| G2 | Medium | `.github/TEMPLATE_SOURCE` ships on the scaffold and adopt copy paths (`TREE_COPIES` copies `.github` wholesale) and its removal is delegated to the project-setup skill's final step, an agent-executed action. A project that never finishes project-setup is permanently refused by both eject and update with the misleading message "this looks like the template source". Options: exclude the sentinel from downstream copy paths (the `setup-complete` marker still gates eject), or teach the engines to distinguish "sentinel present but setup incomplete" and say so. |
| G3 | Medium | Rejected and applied proposals never leave `proposals/`. `continuous-learning` sets the status and stops; `propose.py` archives only pending/stale. Two rejected proposals from 2026-06-01 still sit in the tracked directory. Since `proposals/` is committed for `learning-summary.yml`, resolved proposals accumulate in git history and in every consumer's adoption copy. The skill's cleanup step should move applied/rejected files to `proposals.archive/` with a recorded reason. |
| G4 | Low | The pre-commit hash skip covers instruction sources and the hub only. A hand-edit to a `.claude/rules/` mirror (forbidden, but the file system allows it) does not invalidate `.claude/.sync-hash`, so sync is skipped; whether the drift is caught depends on incremental validation's section map for the staged path. Changing `sync-claude-rules.py` itself also leaves the hash valid. Hash the mirrors and the sync script too, or always run sync when anything under `.claude/rules/` is staged. |
| G5 | Low | `detect_error_recovery` embeds `input_summary[:80]` in the action text, and the action is the instinct ID. Every distinct recovery mints a new instinct file that never merges with its siblings. Detector 1's own docstring states the no-volatile-label rule; detector 3 violates it. Template the action ("Recover failed {tool} with {tool}") and move the command detail to evidence. |
| G6 | Low | `.claude/sync_log.txt` grows without bound (append per sync run). Local and gitignored, but a long-lived clone accumulates indefinitely. Cap or rotate it. |

Closeout 2026-06-11: all six gaps fixed per `docs/process/2026-06-11-audit-gap-fix-plan.md`. G1: `bootstrap-update.py`, applied to unity-greenfield the same day (anchor 9bb830c). G2: sentinel excluded from both copy paths. G3: `archive_resolved_proposals` in `propose.py`, three resolved files migrated. G4: pre-commit hash covers mirrors, `CLAUDE.md`, and the sync script. G5: detector-3 action templated. G6: sync-log rotation at 256 KB.

## Missing features

Already tracked in the backlog, listed for completeness: the `agent-feature-planning` and `agent-refactor-planning` skills (`docs/process/backlog/2026-05-30-skill-backlog.md`), and the semantic-validation tier (contradiction detection, rule efficacy, template-instance validity) from `docs/process/backlog/2026-05-30-validation-hallucination-optimization.md`.

New candidates from this review:

| ID | Finding |
|----|---------|
| F1 | Generic-vs-project convention awareness in `map_target_file`. The two live pending proposals route "Place .json files in .github/scripts/" into `code-standards.instructions.md`, a universal file. That convention is an artifact of building the harness itself, not a code standard. The promotion path has no way to say "true here, not portable". A `domain: repo-layout` route to memory or a project-conventions file would stop harness-development churn from proposing itself as universal law. |
| F2 | Optional instinct seeding on adopt. Adopted projects start with an empty learning corpus. Genuinely portable instincts (for example "place .yml workflow files in .github/workflows/") could ship as low-confidence, unconfirmed seeds the consumer's own evidence then reinforces or decays. Worth an ADR if pursued; default-off is the safe choice. |
| F3 | Machine-readable behind-state from `update.py --check` (it exits 0 whether current or behind). A distinct exit code or `--quiet` flag would let CI or a scheduled job nudge when a consumer falls behind. |
| F4 | Proposal reinforcement. Tied to B4: when analyze reinforces an instinct that already has a pending proposal, bump the proposal's `last_reviewed` or a `reinforced_session` field and have staleness read that instead of `created_session`. This is the missing mechanism the propose.py docstring already claims. |

## Refactoring (value-adding only)

| ID | Value | Finding |
|----|-------|---------|
| R1 | High | Deduplicate the instinct frontmatter I/O. `load_instinct` (analyze.py) and `parse_instinct` (propose.py) are near-identical parsers; `update_instinct_confidence` (analyze.py) and `save_instinct_confidence` (propose.py) are exact duplicates. All four must stay format-compatible with `save_instinct`. Move them into `session_clock.py`, which is already the shared-primitives module the three scripts import. Eliminates a real drift class for ~40 lines moved. |
| R2 | High | Decide one Pre/Post recording policy instead of per-detector filters. Either record tool observations only on PostToolUse (halves log volume, kills the B1 bug class permanently, keeps the outcome field) or keep both and make event-type filtering a shared helper every detector goes through. The current state, where two detectors filter and two do not, is how B1 happened. |
| R3 | Medium | `eject.py` `scrub_content` drops any line containing a removed backtick ref. In list rows and tables that is right; in flowing prose it amputates mid-paragraph. Restrict the drop to list items and table rows, and report (rather than edit) prose hits for manual cleanup. |
| R4 | Judgment call | `_git` subprocess plumbing is duplicated across `eject.py`, `update.py`, and partially `repository-setup.py`. A shared module would normally be right, but each engine is deliberately a standalone file that survives downstream copies in isolation. Recommend leaving as is and recording the standalone-file constraint in a comment so the duplication reads as intent, not accident. |

## Disposition notes

The unity-greenfield drift (its `pattern-fidelity` copy lacks the index-first triage section; its hub omits the lifecycle skills) is expected for a consumer adopted hours before the harness's evening push, not a harness defect. It becomes resolvable exactly when G1 is fixed.

Items B1-B4 cluster in the learning pipeline's evidence math. None corrupts data and all are bounded by the human-review gate, but together they distort the confidence numbers the developer is asked to trust during the open verification windows. Recommend fixing B1/B3/B4 before trusting the first correction-batch review, since that review is explicitly the test of those numbers.

## Summary

PASS: automated validation (569 checks), 118 engine tests, mirror sync, manifest coverage, skill registration and handoffs, repo hygiene.
FAIL: 7 bugs of substance (B1-B7), 2 high gaps (G1, G2), 1 stale-guidance inconsistency with setup impact (I1).
WARN: 7 low inconsistencies, 4 low gaps, 4 feature candidates, 3 refactors worth doing.

Nothing found threatens existing data or breaks a current workflow today. The highest-leverage fixes, in order: B1+R2 (one policy for event recording), G1 (update bootstrap for pre-mechanism adoptees), B3+B4+F4 (decay and reinforcement math), I1 (project-setup stale markers), G2 (sentinel lockout).
