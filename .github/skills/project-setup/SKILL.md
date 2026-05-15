---
name: project-setup
description: >
  Tailor this project setup template for a specific stack. Walks through creating
  stack-specific instruction files, updating hub files, and running the sync script.
  Use when starting a new project, adding a new language/framework, or when the user
  mentions "set up project", "add a stack", "new language", or "tailor template".
---

# Project Setup Skill

Tailor the project setup workflow template for a specific technology stack.

## Prerequisites

Read the system index for the current file map:
- `.github/docs/system-index.md`

## Workflow

### Step 1: Identify the Stack

Ask the user:
- What language(s) will this project use? (e.g., C#, Lua, C++, Python, TypeScript)
- What frameworks or UI toolkits? (e.g., WPF, raylib, Qt, React, Flask)
- What test framework? (e.g., NUnit, busted, GoogleTest, pytest, Jest)
- What architectural pattern? (e.g., MVVM, MVC, ECS, layered)

### Step 2: Create Stack-Specific Instruction Files

For each language identified, create the following in `.github/instructions/`:

**Required:**
- `{language}-code-standards.instructions.md`: Language-specific coding standards.
  - Must use `applyTo: "**/*.{ext}"` frontmatter matching the language's file extension.
  - First line of body: `These standards extend code-standards.instructions.md with {language}-specific rules.`
  - Sections to include: null safety, async conventions, dependency injection, naming conventions, error handling, testing (framework, mocking library, naming pattern).

### Step 3: Populate Agnostic Template Files

Review all files with `CUSTOMIZE` comments and fill in stack-appropriate content:
- `patterns.instructions.md`: Replace the example pattern with the project's adopted patterns and code examples. Optionally narrow `applyTo` scope.
- `user-interface.instructions.md`: If the project has a UI layer, narrow `applyTo` to the framework's file extensions (e.g., `**/*.xaml`, `**/*.tsx`) and fill in the CUSTOMIZE sections. If no UI layer, mark the file `<!-- DEPRECATED -->` so the sync script skips it.
- `user-experience.instructions.md`: Same rule as user-interface: scope to UI extensions or mark deprecated.
- `code-standards.instructions.md`: Replace any customize markers with language-specific conventions.
- `copilot-instructions.md`: Fill in the Project Overview section.
- `.gitignore`: Replace `# CUSTOMIZE` sections with stack-specific build outputs, packages, test results, and config patterns.

### Step 4: Update Hub and Index Files

After creating instruction files, update these files, look for `<!-- CUSTOMIZE -->` markers:

1. **`.github/copilot-instructions.md`**: Add stack-specific files to the Instruction Files section. (`CLAUDE.md` is synced automatically by the sync script.)
2. **`.github/docs/system-index.md`**: Add rows to the Instruction Files table between the CUSTOMIZE markers.

### Step 5: Run Sync and Validate

1. Run `sync.bat` (or `python .github/scripts/sync-claude-rules.py`).
2. Verify the sync log shows all new files synced.
3. Confirm `.claude/rules/` contains matching copies with `paths` frontmatter.

### Step 6: Confirm Checklist

Before finishing, verify:
- [ ] All new instruction files have correct `applyTo` frontmatter
- [ ] Each language has at least a `{language}-code-standards.instructions.md`
- [ ] `copilot-instructions.md` references all new instruction files (`CLAUDE.md` syncs automatically)
- [ ] `system-index.md` table includes all new files with correct scopes
- [ ] Sync script ran successfully with no warnings
- [ ] All `.md` files are under 4,000 characters
- [ ] `.claude/learning/config.json` exists (continuous learning is active from first session)
