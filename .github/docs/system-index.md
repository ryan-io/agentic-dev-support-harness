# System Index

Quick-reference map of the project setup template's system files.

## Golden Rule
ALL files must work in: GitHub website Copilot PR review, GitHub Copilot chat, and Claude Code chat. `.github/instructions/` files are the source of truth. `.claude/rules/` are synced copies with `paths` frontmatter.

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

| Source (Copilot) | Copy (Claude) | Scope |
|------------------|---------------|-------|
| `code-standards.instructions.md` | `code-standards.md` | `**` |
| `pr-review.instructions.md` | `pr-review.md` | `**` |
| `adr-template.instructions.md` | `adr-template.md` | `docs/adr/**` |
| `adr-pr-review.instructions.md` | `adr-pr-review.md` | `docs/adr/**` |
| `br-review.instructions.md` | `br-review.md` | `docs/business-rules/**` |
| `patterns.instructions.md` | `patterns.md` | `**` |
| `user-interface.instructions.md` | `user-interface.md` | `**` |
| `user-experience.instructions.md` | `user-experience.md` | `**` |
| `writing-voice.instructions.md` | `writing-voice.md` | `**` |
<!-- CUSTOMIZE: Add stack-specific rows for your project (e.g., csharp-code-standards.instructions.md) -->
<!-- END CUSTOMIZE -->

### On-Demand (read by skills at runtime)
| File | Purpose |
|------|---------|
| `.github/docs/adr-template.md` | Copyable ADR template |
| `.github/docs/br-template.md` | Copyable BR template |
| `.github/skills/adr-creation/SKILL.md` | Interactive ADR creation |
| `.github/skills/create-business-rule/SKILL.md` | Interactive BR creation |
| `.github/skills/system-review/SKILL.md` | System audit checklist |
| `.github/skills/project-setup/SKILL.md` | Stack onboarding / template tailoring |
| `.github/skills/convention-discovery/SKILL.md` | Generate rules from git history |
| `.github/skills/continuous-learning/SKILL.md` | Review and apply learned patterns |

### Infrastructure
| File | Purpose |
|------|---------|
| `.github/pull_request_template.md` | PR template |
| `.github/scripts/sync-claude-rules.py` | Syncs instructions → rules |
| `.github/scripts/setup/sync.bat` | Sync runner |
| `.github/scripts/setup/repository-setup.bat` | Init or activate repo (Windows) |
| `.github/scripts/setup/repository-setup.sh` | Init or activate repo (Unix) |
| `setup.bat` / `setup.sh` / `sync.bat` | Root shims |
| `.github/hooks/pre-commit` | Runs sync + validation on commit |
| `.github/hooks/observe.json` | Hook config for learning |
| `.github/scripts/learning/observe.py` | Records observations |
| `.github/scripts/learning/analyze.py` | Creates instincts |
| `.github/scripts/learning/propose.py` | Promotes to proposals |
| `.github/scripts/validate-system.py` | System validation |
| `.github/workflows/validate-system.yml` | Validation on PR |
| `.github/workflows/convention-discovery.yml` | Git analysis on merge |
| `.github/workflows/learning-summary.yml` | Weekly proposal summary |
| `.claude/learning/config.json` | Learning thresholds |
| `.gitignore` | Ignores + learning data |

## Cross-References
- `copilot-instructions.md` is source of truth; `CLAUDE.md` is synced
- ADR skill reads: `adr-template.md` (rules auto-load for `docs/adr/**`)
- BR skill reads: `br-template.md` (rules auto-load for `docs/business-rules/**`)
- Learning: `observe.json` → `observe.py` → `analyze.py` → `propose.py` → `continuous-learning` skill
- Learning data (gitignored): `observations.jsonl`, `instincts/`, `proposals/`
