# System Review Remediation Plan

Status: Phases 1 and 5 complete (2026-06-08). Phases 2, 3, and 4 planned.

Date: 2026-06-08

Scope: a deep review of the whole harness found no active breakage. The mirror is in sync, `CLAUDE.md` is byte-identical to `copilot-instructions.md`, all 78 tests pass, and `validate-system.py` reports 509 pass, 0 fail, 0 warn. Cross-references resolve. This plan fixes the latent bugs and the documentation drift the review surfaced, ordered by risk and cost. Nothing here is urgent; the highest-value items are cheap doc corrections and one data-loss guard.

## Cross-cutting constraints

Instruction sources under `.github/instructions/` and the `.claude/rules/` mirror are not hand-edited. `.claude/rules/memory.md` changes only through the `continuous-learning` skill. ADR edits follow `adr-pr-review`. Run `validate-system.py` and the test suites after every change. Pipeline Python stays stdlib-only and fails closed.

## Phase 1: Documentation reconciliation (DONE 2026-06-08)

Completed. The capture-corrections ADR Decision body now reads SessionEnd throughout; the only remaining Stop mention is the amendment's explanatory "SessionEnd, not Stop" line. A related stale line that claimed "the status is Proposed" while the metadata reads Active was corrected in the same pass. The ADR README prefix list gained `setup`. The scripts README "byte-for-byte" claim now reads "line-ending and BOM normalization." The system-index gained the two test files and the templates README; their Purpose cells avoid slash-paths so the validator does not read them as references. The memory date claim was reworded to "implemented and amended 2026-06-05" via the instruction source, then re-synced. Validator passes 512/0/0 and all five test suites pass.

The original plan text follows.

These are factual mismatches between curated docs and the system they describe. Cheap, no code risk.

The capture-corrections ADR is the headline. `docs/adr/adr-learn-capture-corrections-via-transcript-parse.md` still describes the Stop hook as the capture mechanism in its Decision and supporting prose (lines 23, 27, 35, 37, 55, 69, 75, 88), while the Amendment (line 13) and Consequences (line 91) record that the parse actually runs on SessionEnd. The project rejected Stop for SessionEnd. Reconcile the Decision body to SessionEnd, or annotate each Stop mention inline as superseded, matching how `adr-scaffold-introduce-ah-ide-cli.md` annotates its superseded lines.

`docs/adr/README.md` (line 15) lists prefixes `design, learn, project, rag, scaffold` but omits `setup`, which `adr-setup-introduce-harness-eject.md` uses. Add `setup`.

`.github/scripts/README.md` (line 7) calls the hub copy "byte-for-byte." The sync normalizes BOM and CRLF, so the claim is inaccurate for non-ASCII or CRLF sources. Reword to "copies with line-ending and BOM normalization."

`.github/docs/system-index.md` omits three real files: `.github/scripts/tests/test_eject.py`, `.github/scripts/tests/test_repository_setup.py`, and `templates/README.md`. Add them under the infrastructure section.

`.claude/rules/memory.md` (line 24) says both learning ADRs "went Active 2026-06-05." The metadata dates are 2026-06-04 (staleness) and 2026-06-01 (correction capture); both were amended/implemented 2026-06-05. Reword to "both implemented and amended 2026-06-05." Route this through the `continuous-learning` skill, not a hand-edit.

## Phase 2: Sync-script safety

Two changes to `.github/scripts/sync-claude-rules.py`, both about making the sync safe and inspectable.

The orphan cleanup deletes any `*.md` in `.claude/rules/` not in the expected generated set, keyed only on the extension. A hand-added file or a mirror whose source hit a transient parse error is silently removed with `os.remove`. Guard the deletion: only remove files that match the known generated-mirror shape, or keep an explicit manifest of generated mirrors, or quarantine strays instead of deleting.

The script has no `--check` mode; it always mutates and always appends to `sync_log.txt`. The read-only check logic lives separately in `validate-system.py` section 4, so the transform is implemented twice and can drift. Add a `--check` flag that runs the transform in memory, reports would-change and would-delete files, writes nothing, and exits non-zero when the mirror is stale.

While in this file, replace the `split("---", 2)` frontmatter parse with an explicit leading `^---\n...\n---\n` block match. The same fragile split exists in `validate-system.py` section 4; fix both so a `---` inside a YAML value cannot corrupt parsing. No current file triggers this.

## Phase 3: Pipeline correctness

Four low-severity bugs in the learning pipeline. None breaks the fail-closed or exit-zero invariants; each degrades signal quality or audit accuracy.

`analyze.py` (around line 932) appends the `_analysis_marker` with a plain `open(OBS_FILE, "a")`, bypassing `observe.locked_append`. Analysis runs detached via `subprocess.Popen` while a fresh session's hooks may append concurrently, so the marker write can interleave bytes with a locked writer. Route it through the locked append helper.

`analyze.py` `correction_contradicts_scope` (lines 293-304) uses a basename fallback that matches across directories: a correction on `other/foo.py` wrongly contradicts an instinct scoped to `src/foo.py`, penalizing confidence on an unrelated file. Apply the basename fallback only when the scope is a `**/*.ext` glob with no fixed directory.

`observe.py` `is_self_observation` (lines 237-245) inspects only `tool_input["file_path"]`, so a Bash command like `cat .claude/learning/...` is recorded against intent. Also scan `tool_input["command"]` for the self-observation fragments. Low impact because Bash observations carry no file extension.

`analyze.py` `contradiction_pass` (lines 358-362) logs `len(corrections)`, the whole batch, while the evidence applied is the scope-matched subset. Print the matched count instead, so the audit trail is honest.

## Phase 4: Test coverage

This folds into the existing `2026-06-08-pytest-test-suite-plan.md`; do not duplicate that effort.

Only `detect_user_corrections` is exercised. Untested: the other six detectors (`detect_corrections`, `detect_repeated_sequences`, `detect_error_recovery`, `detect_file_conventions`, `detect_rule_consultation`, `detect_guide_consultation`), most of `propose.py` (`map_target_file`, `compute_priority`, `generate_proposal`, `proposal_exists`, `record_archive_reason`), and the `observe.py` builders (`build_observation`, `summarize_tool_input`, `classify_domain`, `rotate_observations_if_needed`, plus `correction_contradicts_scope`, the subject of the Phase 3 cross-directory bug). Add fixture tests for each detector and for `map_target_file` and `compute_priority`. Write the `correction_contradicts_scope` test first; it pins the Phase 3 fix.

## Phase 5: Replace unmeasurable confidence thresholds in decision rules (DONE 2026-06-08)

Completed. `pr-review.instructions.md` line 35 now requires naming the concrete failure (triggering input or code path and the wrong result) or using `Question/`, replacing the ">90%" rule. Both `volatility-decomposition/SKILL.md` lines gate on "clearly variable rather than volatile (bounded change, no system-wide ripple)" instead of "90%+ confidence." The lookalikes were left as the plan specified. The pr-review source was re-synced to its mirror; validator passes 512/0/0.

The original plan text follows.

Three actionable directives gate a decision on a self-assessed confidence percentage the agent cannot measure. An agent has no calibrated probability, so ">90%" is theater. Replace each with the concrete, checkable test it stands in for. These are instruction and skill edits, so they need developer approval before the change lands.

`.github/instructions/pr-review.instructions.md` (line 35) reads "Only comment with HIGH CONFIDENCE (>90%) that an issue exists." The concrete test already lives in `.github/docs/pr-review-guide.md` line 20 ("this causes... when..." with a concrete scenario). Replace line 35 with: "Raise a comment only when you can name the concrete failure: the triggering input or code path and the wrong result it produces. If you cannot state that scenario, use `Question/` or stay silent."

`.github/skills/volatility-decomposition/SKILL.md` (lines 36 and 62) both gate on "clearly variable (90%+ confidence)." Volatility is defined by change along the method's axes, not by a confidence number. Replace "clearly variable (90%+ confidence)" in both lines with "clearly varies along a known axis (across customers, over time, or between business cases)."

Leave the lookalikes alone. The `config.json` thresholds (`0.7`, `0.45`, `0.2`) and `continuous-learning`'s "confidence below 0.2" reference a real stored numeric field and are already actionable. `convention-discovery`'s "80%+ consistent" and "50-79% consistent" are countable ratios over git history, not self-assessment; they are fine, though Phase 4 author tooling could later pin a minimum sample size so a ratio over three occurrences is not read like one over two hundred. The "roughly 240 lines," "roughly eighty files," "several minutes," and "almost never wrong" phrases are ADR rationale prose, not decision rules; forcing false precision there would violate `writing-voice`.

## Out of scope

These are noted as tradeoffs or thin margins, not defects. No action unless they bite.

`rotate_observations_if_needed` (observe.py:129-131) discards unanalyzed observations when the file hits 1000 lines with no analysis marker. This is documented as intentional bounding. The `lua-code-standards` (3962/4000) and `csharp-code-standards` (3862/4000) mirrors sit close to the char cap, and the `applyTo` to `paths` transform grows the output past the source; a small source edit could push the output over cap and leave that one mirror stale on a failed sync. Consider an author-time warning at 3800 chars. Business rules have no Proposed status while ADRs do; flag only if Proposed BRs are ever wanted.

## Verification

After Phase 2 and 3, run `python3 .github/scripts/validate-system.py` (expect exit 0) and every suite under `.github/scripts/learning/tests/` and `.github/scripts/tests/` (expect all pass). After Phase 1, re-read the capture-corrections ADR end to end and confirm no remaining Stop reference describes the live mechanism. Run `sync-claude-rules.py --check` once it exists and confirm a clean tree reports no changes.
