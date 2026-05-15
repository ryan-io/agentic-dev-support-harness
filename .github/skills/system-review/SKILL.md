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

## Checklist

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

### 5. Content Consistency
- Agnostic files (`code-standards`, `pr-review`, `copilot-instructions`) must not contain stack-specific references (e.g., C#, WPF, MVVM, NUnit).
- Stack-specific files must reference the correct parent (e.g., "extends code-standards").
- Cross-references in the system index must resolve to real files.
- Templates must have no leftover placeholder text from previous edits.

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
