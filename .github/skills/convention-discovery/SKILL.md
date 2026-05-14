---
name: convention-discovery
description: >
  Analyze git history to generate or refine instruction files from actual conventions.
  Use when adopting this template in an existing repo, or "discover conventions".
---

# Convention Discovery Skill

Analyze git history to generate instruction files from actual team conventions.

## Prerequisites

- Git history (50+ commits recommended).
- Template in place (`repository-setup` and `project-setup` first).
- Read `.github/docs/system-index.md` for file map.

## When to Use

- Adopting this template in a repo with established patterns.
- Periodic audit after milestones. Not for greenfield, use `project-setup`.

## Workflow

### Step 1: Gather Evidence

Run git analyses and record findings. Do not infer rules, only collect data.

| Area | Command |
|---|---|
| Commits | `git log --format="%s" -200` |
| File placement | `git log --diff-filter=A --name-only --format=""` |
| Hotspots | `git log --format="" --name-only \| sort \| uniq -c \| sort -rn` |
| Naming | `find . -name "*.{ext}" -not -path "./.git/*"` |
| Error handling | `grep -rn "catch\|except\|throw" --include="*.{ext}"` |
| DI | `grep -rn "inject\|constructor\|container" --include="*.{ext}"` |

### Step 2: Classify Findings

For each finding, classify as:

- **Strong convention**: 80%+ consistent. Write as a rule.
- **Emerging pattern**: 50-79% consistent. Write as a recommendation.
- **Inconsistency**: conflicting patterns. Flag for team discussion.
- **Absent**: no evidence. Skip: do not invent rules.

### Step 3: Generate or Update Instruction Files

Map findings to instruction files. Only modify relevant sections, preserve existing content.

**Targets:** commits/file placement → `code-standards`. Naming/errors/DI → `{language}-code-standards`. Architecture → `patterns`. UI → `user-interface`.

**Rules:** cite the git command as evidence. Mark `[strong]` or `[emerging]`. Stay under 4,000 chars. Preserve `<!-- CUSTOMIZE -->` markers and `applyTo` frontmatter.

### Step 4: Present Findings for Review

Before writing files, present a summary:

1. **Strong conventions**: rules to codify (with evidence).
2. **Emerging patterns**: recommendations to consider.
3. **Inconsistencies**: conflicts needing team decision.
4. **No evidence**: areas with no clear pattern.

Wait for user approval before modifying instruction files.

### Step 5: Apply and Sync

1. Write approved changes to `.github/instructions/` files.
2. Run `sync.bat` (or `python .github/scripts/sync-claude-rules.py`).
3. Verify sync log and confirm all files remain under 4,000 characters.

### Step 6: Confirm

- [ ] All rules cite git evidence; confidence marked
- [ ] No rules invented without evidence
- [ ] `applyTo` frontmatter correct; all `.md` under 4,000 chars
- [ ] Sync ran; user approved before files were modified

<!-- WORKFLOW: PR merge → convention-discovery.yml gathers evidence into a GitHub Issue →
developer runs this skill to classify and apply. Action gathers; human decides. -->
