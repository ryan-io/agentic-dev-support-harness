# System Index

Quick-reference map of the project setup template's system files.

## Golden Rule
`.github/instructions/` is the source of truth. `.claude/rules/` are synced copies with `paths` frontmatter.

## Constraints
- Instruction files (`.github/instructions/`, `.claude/rules/`) must be ≤ 4,000 chars. All other markdown files (docs, guides, templates, skills, READMEs) are exempt.
- Frontmatter: `applyTo` (Copilot), `paths` (Claude).
- No stack-specific content in agnostic files
- Status: ADRs use `Active`/`Proposed`/`Archived`; business rules use `Active`/`Archived`

## File Map

### Entry Points (identical, synced by script)
| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Source of truth, agent entry point |
| `CLAUDE.md` | Synced copy for Claude Code |

### Instruction Files (synced to .claude/rules/)

Copies in `.claude/rules/` drop the `.instructions` segment (e.g., `code-standards.instructions.md` becomes `code-standards.md`).

#### Core (universal, all files)
| Source | Scope |
|--------|-------|
| `code-standards.instructions.md` | `**` |
| `writing-voice.instructions.md` | `**` |
| `research.instructions.md` | `**` |
| `agent-guardrails.instructions.md` | `**` |
| `pattern-fidelity.instructions.md` | `**` |
| `memory.instructions.md` | `**` |

#### Extended (scoped by file type)
| Source | Scope |
|--------|-------|
| `testing.instructions.md` | `**/*.cs,**/*.lua,**/*.py,**/*.ts,**/*.js,**/*.jsx,**/*.tsx,**/test/**,**/tests/**,**/spec/**` |
| `pr-review.instructions.md` | `**/*.cs,**/*.lua,**/*.py,**/*.ts,**/*.js,**/*.jsx,**/*.tsx,**/*.xaml,**/*.html,**/*.css,**/*.vue` |
| `user-interface.instructions.md` | `**/*.xaml,**/*.tsx,**/*.jsx,**/*.vue,**/*.html,**/*.css,**/*.razor` |
| `user-experience.instructions.md` | `**/*.xaml,**/*.tsx,**/*.jsx,**/*.vue,**/*.html,**/*.css,**/*.razor` |
| `patterns.instructions.md` | deprecated (placeholder, not synced) |

#### Domain-specific
| Source | Scope |
|--------|-------|
| `adr-template.instructions.md` | `docs/adr/**` |
| `adr-pr-review.instructions.md` | `docs/adr/**` |
| `br-review.instructions.md` | `docs/business-rules/**` |
| `csharp-code-standards.instructions.md` | `**/*.cs` |
| `lua-code-standards.instructions.md` | `**/*.lua` |
| `unity-code-standards.instructions.md` | `**/Assets/**/*.cs` |

### Guide Files (on-demand deep docs, not auto-loaded)
| Guide | Companion Rule |
|-------|----------------|
| `writing-voice-guide.md` | `writing-voice.instructions.md` |
| `agent-guardrails-guide.md` | `agent-guardrails.instructions.md` |
| `testing-guide.md` | `testing.instructions.md` |
| `pr-review-guide.md` | `pr-review.instructions.md` |
| `learning-system-guide.md` | root `README.md` (learning system summary) |
| `context-efficiency-guide.md` | root `README.md` (design notes) |

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
| `.github/skills/behavioral-requirements/SKILL.md` | Requirements as behavior (pipeline stage 1) |
| `.github/skills/volatility-decomposition/SKILL.md` | Volatility-based decomposition (pipeline stage 2) |
| `.github/skills/architecture-layering/SKILL.md` | Layered architecture classification (pipeline stage 3) |
| `.github/skills/architecture-design-pipeline/SKILL.md` | Orchestrates the three-stage design pipeline |
| `.github/skills/implementation/SKILL.md` | Pair-program a design into C#/WPF code (pipeline stage 4) |
| `.github/skills/write-unit-tests/SKILL.md` | Write unit tests for existing code (NUnit 4 + Moq) |
| `.github/skills/sequence-diagram/SKILL.md` | Mermaid sequence diagram creation |
| `.github/skills/harness-eject/SKILL.md` | Post-setup teardown of template machinery |
| `.github/skills/harness-update/SKILL.md` | Pull harness updates into an adopted project |

### Infrastructure
| File | Purpose |
|------|---------|
| `.github/pull_request_template.md` | PR template |
| `.github/scripts/sync-claude-rules.py` | Syncs instructions → rules |
| `.github/scripts/validate-system.py` | System validation |
| `.github/scripts/setup/repository-setup.py` | Repo-init engine (Python; `python ...repository-setup.py`) |
| `.github/scripts/eject.py` | harness-eject engine (Python; `python ...eject.py`) |
| `.github/scripts/update.py` | harness-update engine (Python; `python ...update.py`) |
| `.github/scripts/update-manifest.json` | harness-update file classification (overwrite/merge/exclude) |
| `.github/scripts/eject-manifest.json` | Eject category manifest (A/B/C removable paths) |
| `.github/hooks/pre-commit` | Runs sync + validation on commit (only shell script) |
| `.claude/settings.json` | Claude Code hook registration for learning |
| `.github/scripts/learning/` | `observe.py` → `analyze.py` → `propose.py` |
| `.github/scripts/scaffold.py` | ah-ide scaffolding engine (`python ...scaffold.py`) |
| `.github/scripts/tests/test_eject.py` | Tests for the harness-eject engine |
| `.github/scripts/tests/test_update.py` | Tests for the harness-update engine |
| `.github/scripts/tests/test_repository_setup.py` | Tests for the repo-init engine |
| `templates/` | Stack templates consumed by the scaffolder |
| `templates/README.md` | Template authoring guide |
| `.github/workflows/` | `validate-system.yml`, `convention-discovery.yml`, `learning-summary.yml`, `scaffold-matrix.yml` |
| `.claude/learning/config.json` | Learning thresholds |
| `.gitignore` / `.gitattributes` | Ignores and line endings |

Each major directory has a `README.md` (human-facing, size-limit exempt).

### Content Directories
| Directory | Purpose |
|-----------|---------|
| `docs/adr/` | Architecture decision records |
| `docs/business-rules/` | Business rule definitions |
| `docs/design/` | Use cases, volatilities, architecture docs (design pipeline) |
| `docs/diagrams/` | Mermaid diagrams (sequence-diagram skill) |
| `docs/process/` | Backlogs, subsystem plans, working notes |

### Documentation Indexes
Triage tables an agent consults before loading full records, so whole documents stay out of context until one is relevant. Scan by status and context, then open the source file only when it governs the change. This file is the systems index; the other two cover the content directories above.

| Index | Covers | Maintained by |
|-------|--------|---------------|
| `.github/docs/system-index.md` | System files (this file) | Hand-curated; section-18 validation enforces completeness |
| `docs/adr/adr-index.md` | All ADRs (name, status, context, synopsis) | `adr-creation` skill appends a row per new ADR |
| `docs/business-rules/br-index.md` | All business rules (name, status, domain, related ADRs, synopsis) | `create-business-rule` skill appends a row per new rule |

The index-first protocol is enforced by `pattern-fidelity.instructions.md` (universal), `adr-pr-review.instructions.md` (`docs/adr/**`), and `br-review.instructions.md` (`docs/business-rules/**`).

## Cross-References
- Skills read templates in `.github/docs/`; scoped rules auto-load by directory
- Learning chain: `.claude/settings.json` (hooks) → `observe.py` → `analyze.py` → `propose.py` → `continuous-learning`

## Size Management
Instruction files must stay under 4,000 chars. At 3,800: trim redundancy. Over 4,000: split or extract to a companion guide (`{name}-guide.md`). Other docs (guides, templates, hub) are not size-limited.
