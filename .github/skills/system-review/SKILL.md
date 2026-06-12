---
name: system-review
description: >
  Run an intermittent review of the project setup workflow. Checks file existence,
  cross-references, frontmatter consistency, sync state, size limits, and compatibility.
  Use when asked to "review the system", "audit the setup", or "check for gaps".
---

# System Review Skill

Audit the project setup workflow for inconsistencies, gaps, and rule violations.

## Prerequisites
Read `.github/docs/system-index.md` for the complete file map and cross-reference list.

## Step 0: Run the Validator First

Run `python .github/scripts/validate-system.py` before any manual auditing. It
automates checklist items 1-4 and 6 below plus seventeen further sections
(hook registration, manifest coverage, skill registration, workflow YAML,
Python syntax, learning-pipeline invariants, and more). Report its summary
line, then spend the manual pass only on what it cannot check: semantic
consistency, stale or misleading guidance, cross-file agreement, and content
that parses cleanly but says the wrong thing. A FAIL from the validator is a
finding; do not re-derive it by hand.

## Checklist

Items 1-4 and 6 are automated by the validator; verify them via Step 0 and
audit manually only when the validator could not run. Item 5 is the manual
core of this skill.

### 1. File Existence
Verify every file listed in the system index exists. Flag missing files.

### 2. Golden Rule: Environment Compatibility
For each file, confirm it works in all three environments:
- `.github/instructions/` files have `applyTo` frontmatter (Copilot)
- `.claude/rules/` files have `paths` frontmatter (Claude Code)
- `copilot-instructions.md` has NO frontmatter (always-on hub)
- `CLAUDE.md` has NO `@` imports: all rules load via `.claude/rules/`

### 3. Sync State
Compare each `.claude/rules/` file against its `.github/instructions/` source:
- Frontmatter key: `applyTo` in source, `paths` in copy (same glob value)
- Body content must be identical
- Every `.github/instructions/` file must have a corresponding `.claude/rules/` copy
- No extra or orphaned files in `.claude/rules/`

### 4. Size Limits
Instruction files (`.github/instructions/`, `.claude/rules/`) must be ≤ 4,000 characters including whitespace. Skill files (`.github/skills/`) and `README.md` files are exempt. Flag any instruction file over the limit.

### 5. Content Consistency (manual: the validator cannot judge meaning)
- Agnostic files (`code-standards`, `pr-review`, `copilot-instructions`) must not contain stack-specific references (e.g., C#, WPF, MVVM, NUnit).
- Stack-specific files must reference the correct parent (e.g., "extends code-standards").
- Cross-references in the system index must resolve to real files.
- Templates must have no leftover placeholder text from previous edits.
- Docstrings, skill steps, and READMEs describe what the code actually does today (stale guidance is a finding even when every automated check passes).

### 6. Hub File Accuracy
`copilot-instructions.md` is the source of truth; `CLAUDE.md` must be an identical copy (managed by the sync script).
- References to instruction files, templates, skills, and policies are valid paths.
- No stale references to renamed, moved, or deleted files.
- On-demand section lists all current templates and skills.

## Output Format
Report findings as:
- **PASS**: Check passed
- **FAIL**: Issue found: describe what and where
- **WARN**: Not broken but worth attention

End with a summary count: passes, fails, warnings.
