# Audit Inconsistency-Fix Plan

Status: Planned

Date: 2026-06-11

Scope: fixes for the eight inconsistencies (I1-I8) from `docs/audit/2026-06-10-system-review.md`. Companion to `2026-06-11-audit-bug-fix-plan.md`, which covers B1-B8 and scopes these out. Ordered by impact: stale setup guidance first (the audit ranked I1 in its top five), then the skill and documentation accuracy fixes, then the size, detector, and test-coverage items. Gaps and features from the same audit remain out of scope.

## Cross-cutting constraints

Pipeline Python stays stdlib-only and fails closed; hooks always exit 0. Tests go in `.github/scripts/learning/tests/` (or `.github/scripts/tests/` for setup-path engines), temp filesystem only. Edits to `.github/instructions/` require explicit developer approval per `agent-guardrails` Instruction File Integrity; Phase 4 is gated on that. Never hand-edit `.claude/rules/` mirrors; edit sources and run `sync-claude-rules.py`. Run `validate-system.py` and all suites after each phase.

Sequencing against the bug-fix plan: Phases 3 and 5 here touch `analyze.py` and `observe.py`, the same files the bug-fix plan's Phases 1 and 4 rewrite. Land bug-fix Phase 1 (PostToolUse-only recording) first, then write these against the post-fix state so the corrected docstrings describe the hooks that actually remain registered.

## Phase 1: Project-setup stale markers (I1)

`project-setup/SKILL.md` Step 4 (lines 99-102) and the Step 6 checklist still direct the agent to find `<!-- CUSTOMIZE -->` markers in `copilot-instructions.md` and `system-index.md`. Those markers were removed (confirmed in `status.md`, 2026-06-10). Rewrite Step 4 to name the actual insertion points: the Instruction Files section of `copilot-instructions.md` (the stack-specific line) and the Instruction Files table in `system-index.md`. Sweep the rest of the skill for other marker references; `.gitignore` and `research.instructions.md` still legitimately carry markers per `status.md`, so leave those mentions intact.

Verification: dry-run the skill's Step 4 instructions against the current files and confirm an agent can locate both insertion points without markers.

## Phase 2: System-review skill ignores the validator (I6)

`system-review/SKILL.md` never mentions `validate-system.py`, so a manual run duplicates the cheap checks and skips the 17 sections the validator covers beyond the skill's six. Add a step before the checklist: run `python .github/scripts/validate-system.py` first, then spend the manual audit on what it cannot check (semantic consistency, stale guidance, cross-file agreement). Mark which checklist items the validator already automates so the agent does not redo them.

## Phase 3: Documentation accuracy batch (I2, I3, I4)

I2: `analyze.py` line 20 says "Called automatically by observe.py on Stop". The boundary is SessionEnd per the staleness ADR and `observe.py` itself. Fix the header.

I3: `observe.py` lines 8-9 list four hook events but omit the registered UserPromptSubmit hook; add it. `handle_session_start_notice` (line 416) says "On first PreToolUse of a session" but runs on SessionStart; fix the docstring.

I4: `docs/process/2026-06-08-system-review-remediation-plan.md` lines 13 and 59 use em dashes in section headers, violating the writing-voice hard rule. Replace with a colon (`## Phase 1: Documentation reconciliation: DONE 2026-06-08` reads poorly; prefer `(DONE 2026-06-08)` in parentheses). Only file in the repo affected; grep for em dashes repo-wide to confirm before closing.

No tests; these are comment and prose changes with no behavior.

## Phase 4: Instruction files over trim threshold (I5)

`csharp-code-standards.instructions.md` (3,987 ch) and `lua-code-standards.instructions.md` (3,961 ch) both exceed the 3,800-char trim threshold from system-index Size Management. One accepted learning proposal could push either past the 4,000 hard cap and block sync. Trim redundancy in each to land under 3,800; if trimming loses real content, extract to a `{name}-guide.md` companion per the Size Management policy instead.

Gate: these are instruction sources, so present the proposed trims to the developer for approval before editing, then run `sync-claude-rules.py` and confirm the mirrors regenerate under the cap.

## Phase 5: Mirror and source counted as distinct rules (I7)

`detect_rule_consultation` in `analyze.py` counts `code-standards.instructions.md` and `code-standards.md` as different rules, so consultations of the `.claude/rules/` mirror never credit the source and a mirror-only-read rule is falsely flagged "rarely consulted". Normalize at count time: strip the path and map `{name}.md` under `.claude/rules/` to `{name}.instructions.md` before incrementing `rule_consult_counts`. Keep the normalization a small helper so detector 4's scope mapping can share it.

Test in `.github/scripts/learning/tests/`: observations consulting only the mirror produce no "rarely consulted" instinct for the source. Coordinate with bug-fix Phase 1, which edits the same detector's event filtering.

## Phase 6: Scaffolder test suite (I8)

`scaffold.py` (541 lines) is the only engine without a test suite; `testing.instructions.md` requires tests for new logic and the other engines all have them. Add `.github/scripts/tests/test_scaffold.py` covering the four templates: scaffold into a temp directory, assert expected tree and file contents, assert idempotence or the documented collision behavior, and exercise the CLI flag surface. Mirror the structure of `test_repository_setup.py`. The `scaffold-matrix.yml` CI exercise stays; the suite gives local, pre-commit coverage.

## Verification

After each phase: `python3 .github/scripts/validate-system.py` exits 0 and all suites pass (118 tests plus additions from the bug-fix plan and Phases 5-6 here). After Phase 1, a fresh read of `project-setup/SKILL.md` references no removed markers. After Phase 4, both trimmed files are under 3,800 characters and mirrors match. Close out by re-checking the audit's I-table and marking each finding fixed with its commit.
