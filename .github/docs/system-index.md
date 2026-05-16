# System Index

Quick-reference map of the project setup template's system files.

## Golden Rule
`.github/instructions/` is the source of truth. `.claude/rules/` are synced copies with `paths` frontmatter.

## Constraints
- Agent-loaded `.md` files must be ≤ 4,000 characters; `README.md` files are exempt.
- Instruction files must have correct frontmatter (`applyTo` for Copilot, `paths` for Claude).
- No stack-specific content in agnostic files
- Status values: `Active` (default) or `Archived`

## File Map

### Entry Points (identical, synced by script)
| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Source of truth, agent entry point |
| `CLAUDE.md` | Synced copy for Claude Code |

### Instruction Files (synced to .claude/rules/)

Copies in `.claude/rules/` drop the `.instructions` segment (e.g., `code-standards.instructions.md` becomes `code-standards.md`).

| Source | Scope |
|--------|-------|
| `code-standards.instructions.md` | `**` |
| `pr-review.instructions.md` | `**` |
| `patterns.instructions.md` | `**` |
| `writing-voice.instructions.md` | `**` |
| `research.instructions.md` | `**` |
| `agent-guardrails.instructions.md` | `**` |
| `testing.instructions.md` | `**` |
| `user-interface.instructions.md` | `**` |
| `user-experience.instructions.md` | `**` |
| `adr-template.instructions.md` | `docs/adr/**` |
| `adr-pr-review.instructions.md` | `docs/adr/**` |
| `br-review.instructions.md` | `docs/business-rules/**` |
| `csharp-code-standards.instructions.md` | `**/*.cs` |
| `lua-code-standards.instructions.md` | `**/*.lua` |

### Guide Files (on-demand deep docs, not auto-loaded)
| Guide | Companion Rule |
|-------|----------------|
| `writing-voice-guide.md` | `writing-voice.instructions.md` |
| `agent-guardrails-guide.md` | `agent-guardrails.instructions.md` |
| `testing-guide.md` | `testing.instructions.md` |
| `pr-review-guide.md` | `pr-review.instructions.md` |

### On-Demand (read by skills at runtime)
| File | Purpose |
|------|---------|
| `.github/docs/adr-template.md` | ADR template |
| `.github/docs/br-template.md` | BR template |
| `.github/skills/adr-creation/SKILL.md` | ADR creation |
| `.github/skills/create-business-rule/SKILL.md` | BR creation |
| `.github/skills/system-review/SKILL.md` | System audit |
| `.github/skills/project-setup/SKILL.md` | Stack onboarding |
| `.github/skills/convention-discovery/SKILL.md` | Rules from git history |
| `.github/skills/continuous-learning/SKILL.md` | Review learned patterns |

### Infrastructure
| File | Purpose |
|------|---------|
| `.github/pull_request_template.md` | PR template |
| `.github/scripts/sync-claude-rules.py` | Syncs instructions → rules |
| `.github/scripts/validate-system.py` | System validation |
| `.github/scripts/setup/` | Sync runner, repo init (Windows + Unix) |
| `setup.bat` / `setup.sh` / `sync.bat` / `sync.sh` | Root shims |
| `.github/hooks/pre-commit` | Runs sync + validation on commit |
| `.github/hooks/observe.json` | Hook config for learning |
| `.github/scripts/learning/` | `observe.py` → `analyze.py` → `propose.py` |
| `.github/workflows/` | `validate-system.yml`, `convention-discovery.yml`, `learning-summary.yml` |
| `.claude/learning/config.json` | Learning thresholds |
| `.gitignore` / `.gitattributes` | Ignores and line endings |

Each major directory has a `README.md` (human-facing, size-limit exempt).

## Cross-References
- Skills read templates in `.github/docs/`; scoped rules auto-load by directory
- Learning chain: `observe.json` → `observe.py` → `analyze.py` → `propose.py` → `continuous-learning`

## Size Management
All agent-loaded files must stay under 4,000 characters. At 3,800: trim stale markers and redundant cross-references. Hub at 3,800: move detail here. Learning proposal over 4,000: split into a new scoped file. Rule file needs depth: extract to a companion guide (`{name}-guide.md`), add a `Full guidance` directive.
