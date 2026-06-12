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

### Adopt path (existing projects)

When the harness was overlaid onto an existing project (`repository-setup.py --adopt`,
or a manual overlay), the project already has a solution.
Skip Step 0; scaffolding is for empty repositories.
Detect the adopt context before asking: `ProjectSettings/ProjectVersion.txt`
means a Unity project; any populated repo without `.github/TEMPLATE_SOURCE`
that predates the harness files is an adoption.

Run these adopt-only actions, then continue at Step 1:

1. **Verify the .gitignore merge.** The adopt merge header
   (`# === agentic-dev-support-harness (adopt merge) ===`) must be present, and
   no tracked project path may be swallowed by a harness pattern. For Unity,
   confirm `git check-ignore Packages/manifest.json` reports nothing (the
   `!/Packages/` negation protects it on case-insensitive filesystems).
2. **Verify the LFS attributes (Unity: required).** `repository-setup.py --adopt`
   merges `.github/docs/unity.gitattributes` into the root `.gitattributes` and
   runs `git lfs install --local` when it detects a Unity target; confirm the
   merge header is present and `git lfs version` works. After a manual overlay,
   perform the merge yourself: append the missing reference lines (never remove
   or reorder existing ones), show the diff, confirm with the developer before
   writing. Files already committed as plain blobs need `git lfs migrate`; flag
   this rather than running it.
3. **Scope the UI instruction files.** For Unity with UI Toolkit, narrow
   `user-interface` / `user-experience` to `**/*.uxml,**/*.uss` (see Step 3).

### Step 0: Scaffold the Solution (ah-ide)

If the repository has no solution or project files yet, offer to scaffold one
before tailoring instruction files. Ask which stack and layout, then run the
ah-ide scaffolder from the repo root through Python:

- `python .github/scripts/scaffold.py csharp --type classlib|wpf|wpf-ef --name <Name> [--ide vscode|vs2026|both] [--test-framework NUnit|xUnit|MSTest]`
- `python .github/scripts/scaffold.py lua --name <Name>` (WoW addon)

For C# templates, `--test-framework` selects the test project's framework
(NUnit, xUnit, or MSTest; default NUnit). Ask the developer their preference
before scaffolding so the test project is right the first time. See
`docs/adr/adr-scaffold-add-test-framework-dimension.md`.

The scaffold lands in the current directory; `python .github/scripts/scaffold.py undo`
reverses the most recent scaffold if the user picked the wrong layout. See `templates/README.md`
and `docs/adr/adr-scaffold-introduce-ah-ide-cli.md`. Skip this step when a
solution already exists.

### Step 1: Identify the Stack

Ask the user:
- What language(s) will this project use? (e.g., C#, Lua, C++, Python, TypeScript)
- What frameworks or UI toolkits? (e.g., WPF, raylib, Qt, React, Flask)
- What test framework(s)? Ask per test type if they differ (e.g., NUnit, Unity Test Framework, busted, GoogleTest, pytest, Jest)
  - For C#, this should already be set by Step 0's `--test-framework` choice; confirm the scaffolded test project matches.
- What architectural pattern? (e.g., MVVM, MVC, ECS, layered)

### Step 2: Create Stack-Specific Instruction Files

For each language identified, create the following in `.github/instructions/`:

**Required:**
- `{language}-code-standards.instructions.md`: Language-specific coding standards.
  - Must use `applyTo: "**/*.{ext}"` frontmatter matching the language's file extension.
  - First line of body: `These standards extend code-standards.instructions.md with {language}-specific rules.`
  - Sections to include: null safety, async conventions, dependency injection, naming conventions, error handling, testing (framework(s) from Step 1 per test type, mocking library, naming pattern, run command).

### Step 3: Populate Agnostic Template Files

Populate the agnostic files with stack-appropriate content. Only `patterns.instructions.md`, `research.instructions.md`, and `.gitignore` still carry `<!-- CUSTOMIZE -->` markers; the others are edited by section name:
- `patterns.instructions.md`: Replace the example pattern with the project's adopted patterns and code examples. Optionally narrow `applyTo` scope.
- `user-interface.instructions.md`: If the project has a UI layer, narrow `applyTo` to the framework's file extensions (e.g., `**/*.xaml`, `**/*.tsx`) and fill in the framework-specific sections. If no UI layer, mark the file `<!-- DEPRECATED -->` so the sync script skips it.
- `user-experience.instructions.md`: Same rule as user-interface: scope to UI extensions or mark deprecated.
- `research.instructions.md`: Fill in the Repo Signals section (primary language, framework, build/test commands for each test framework chosen in Step 1).
- `code-standards.instructions.md`: Confirm the universal rules fit the stack; language-specific conventions belong in the `{language}-code-standards` file from Step 2, not here.
- `copilot-instructions.md`: Fill in the Project Overview section.
- `.gitignore`: Replace `# CUSTOMIZE` sections with stack-specific build outputs, packages, test results, and config patterns.

### Step 4: Update Hub and Index Files

After creating instruction files, register them in both maps. Neither file carries markers; the insertion points are:

1. **`.github/copilot-instructions.md`**: In the `## Instruction Files` section, extend the `**Stack-specific:**` line with each new file and its glob, following the existing form, e.g. `csharp-code-standards (\`*.cs\`)`. (`CLAUDE.md` is synced automatically by the sync script.)
2. **`.github/docs/system-index.md`**: In the `### Instruction Files` section, add a `| Source | Scope |` row to the matching subsection table (usually `#### Domain-specific`), e.g. `| \`{language}-code-standards.instructions.md\` | \`**/*.{ext}\` |`.

### Step 5: Run Sync and Validate

1. Run `python .github/scripts/sync-claude-rules.py`.
2. Verify the sync log shows all new files synced.
3. Confirm `.claude/rules/` contains matching copies with `paths` frontmatter.

### Step 6: Confirm Checklist

Before finishing, verify:
- [ ] All new instruction files have correct `applyTo` frontmatter
- [ ] Each language has at least a `{language}-code-standards.instructions.md`
- [ ] Each standards file's testing section names the confirmed test framework(s) and run commands
- [ ] `copilot-instructions.md` references all new instruction files (`CLAUDE.md` syncs automatically)
- [ ] `system-index.md` table includes all new files with correct scopes
- [ ] Sync script ran successfully with no warnings
- [ ] All instruction files (`.github/instructions/` and `.claude/rules/`) are under 4,000 characters; other `.md` files are exempt
- [ ] `.claude/learning/config.json` exists (continuous learning is active from first session)

### Step 7: Mark Setup Complete

This is the last step, and it runs only after every checklist item above passes.
It flips the two guards that tell `harness-eject` this clone is a real project,
not the template source.

1. Write `.claude/setup-complete`. Put today's date on the first line and a short
   note that `project-setup` completed (for example: `2026-06-07 project-setup completed`).
   This marker is gitignored, so it stays local and never commits back upstream.
2. Write the update anchor `.github/harness-version.json`: the harness source URL
   (or path) and the harness commit this project adopted, via
   `python .github/scripts/update.py --anchor <sha> --source <url>`. Derive the
   commit from the template clone's history or ask the developer. Unlike the
   marker, the anchor is committed; it is the base revision the `harness-update`
   skill merges from. See `docs/adr/adr-setup-add-harness-update-mechanism.md`.
3. Remove `.github/TEMPLATE_SOURCE` if present. This committed sentinel protects
   the upstream source; deleting it marks this clone as a consuming project, and
   the removal is a tracked change. Only template clones (GitHub template feature,
   activate-in-place) still carry it: the scaffold and adopt copy paths exclude it
   (audit G2), so on those paths this step is a no-op.

Do not run this step in the template source repository itself. The source never
completes `project-setup`; both guards must stay in place there.
