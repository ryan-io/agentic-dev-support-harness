# Agentic Dev Support Harness

A repository template that gives GitHub Copilot and Claude Code a shared set of instructions, review standards, and architectural conventions so both agents behave consistently inside the same codebase. Drop it on top of an empty directory and you get a working scaffold for ADRs, business rules, PR reviews, and a self-improving learning pipeline.

## What it does

The harness solves a specific problem: every coding agent reads its own rules file, in its own location, with its own syntax. Maintain them separately and they drift; an ADR written for Copilot's review pass gets ignored by Claude on the next commit. This template keeps one source of truth (`.github/copilot-instructions.md` and the files under `.github/instructions/`) and mirrors it to the locations Claude expects (`CLAUDE.md` and `.claude/rules/`). A pre-commit hook runs the sync so the two never fall out of step.

On top of that scaffolding sits a small body of opinions about how a project should be run: code standards, UI/UX standards, a PR review format with explicit severity and category labels, ADR and business-rule templates with their own validation rules, and a registry for documenting adopted design patterns.

## Layout

Each subsystem has its own README with the detail. The high-level map:

- `.github/instructions/`: canonical rule files, scoped by frontmatter
- `.github/skills/`: on-demand procedures the agent invokes by name
- `.github/scripts/`: sync, validation, setup, and the learning pipeline
- `.github/docs/`: copyable templates and the system index
- `docs/adr/`: Architecture Decision Records
- `docs/business-rules/`: business-owned constraints
- `.claude/rules/`: synced mirror of the instructions (do not edit by hand)
- `.claude/learning/`: local per-developer learning data

`.github/copilot-instructions.md` and `CLAUDE.md` are the agent entry points, identical content, kept in sync by `.github/scripts/sync-claude-rules.py` on every commit.

## Setup

Every path requires one activation step. GitHub's template feature copies files but cannot set git config, so `core.hooksPath` has to be configured per clone. That is what the setup scripts handle. The GitHub Actions workflows run on their own; only the local pre-commit hook needs activation.

### Path A: GitHub template repository (recommended)

1. Click "Use this template" on the GitHub repo page and create a new repo.
2. Clone the new repo locally.
3. From the repo root, run `setup.sh` (Unix/macOS) or `setup.bat` (Windows).
4. The script detects the files are already in place, configures `core.hooksPath`, makes the hook executable, and runs an initial sync.
5. Run the `project-setup` skill to tailor CUSTOMIZE markers to your stack.
6. Make your initial commit.

### Path B: scaffold into an empty directory

1. Create an empty directory for your new project.
2. From inside the empty directory, run `setup.sh` or `setup.bat` with no arguments.
3. The script detects the empty target, initializes git, copies template files, configures hooks, and runs sync.
4. Run the `project-setup` skill.
5. Make your initial commit.

### Path C: bootstrap scripts

1. Copy `harness-bootstrap.sh` or `harness-bootstrap.bat` from `.bootstrap/` into an empty directory.
2. Run it with the path to your local template checkout as the first argument: `./harness-bootstrap.sh /path/to/agentic-dev-support-harness` (or the `.bat` equivalent on Windows).
3. The script initializes git, copies files, configures hooks, and runs sync.
4. Run the `project-setup` skill.
5. Make your initial commit.

### After setup

Regardless of which path you used, the `project-setup` skill is the next step. It walks through the `<!-- CUSTOMIZE -->` markers in the instruction files, generates a `{language}-code-standards.instructions.md` for your stack, and removes placeholders. Run `python .github/scripts/validate-system.py` to confirm everything passes before your first commit.

## Continuous learning

A three-stage pipeline runs from hooks defined in `.github/hooks/observe.json`. `observe.py` records tool calls, `analyze.py` aggregates them into instincts, and `propose.py` promotes high-confidence instincts into markdown proposals that suggest concrete edits to the instruction files. The confidence threshold and staleness windows live in `.claude/learning/config.json` (currently 0.7 confidence, 20 observations before analysis, 30/60-day decay/archive). The `continuous-learning` skill walks you through reviewing and accepting pending proposals. A weekly GitHub Action (`learning-summary.yml`) opens an issue summarizing what is waiting.

## Constraints worth knowing

Every agent-loaded markdown file must stay at or below 4,000 characters, both Copilot and Claude have context limits the harness respects. README files are exempt; they are for humans, not loaded into agent context. All instruction files must carry valid frontmatter or the validation workflow (`validate-system.yml`) will fail the PR. Stack-specific content does not belong in the agnostic files; that is what the `{language}-code-standards` file is for.

## Current state

The template is initialized but unconfigured. The `<!-- CUSTOMIZE -->` markers in `copilot-instructions.md`, `system-index.md`, and `.gitignore` are placeholders waiting for stack details. `docs/adr/` and `docs/business-rules/` contain only `.gitkeep` files, no decisions or rules have been authored yet. No language-specific code-standards file exists. The learning pipeline is wired and will start collecting observations on the first agent session, but has no instincts or proposals to act on yet.

Run the `project-setup` skill to take it from template to project.
