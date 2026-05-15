# ADR-LEARN: Establish Shared Project Memory

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-01 |
| Authors | @ryan-io   |

Amended 2026-06-05, resolving both Technical-debt items. Confirmed-instinct serialization: instincts stay local and gitignored, including confirmed ones; confidence and decay state are per-machine and do not travel. Confirmed knowledge crosses machines only through its two committed carriers, applied proposals and the memory digest. This keeps the curated-vs-raw boundary this ADR drew rather than adding a third committed store. Ceiling revisit trigger: when `memory.instructions.md` exceeds 3,500 characters at curation time, the curation step must propose the pointer-file fallback (capped digest plus fuller local file) before adding the next entry, so the limit is hit by plan rather than by a failed sync. Curation cadence is config-driven: the session-start notice nudges when the local session log exceeds `thresholds.memory_curation_nudge_blocks` (default 5).

---

## Context

The continuous-learning loop now runs. The prior fix registered the observation hooks in `.claude/settings.json`, so observe, analyze, and propose produce data. That output dies on one machine. `observations.jsonl`, `instincts/`, `session-delta.md`, and `last-modified.json` are gitignored; only `proposals/` is tracked. A fresh clone, a new teammate, or a second machine starts from zero. "Learns within a project" is really "learns on one developer's machine."

The harness also requires that an agent not re-orient to the codebase each session. Today the only continuity artifact is `session-delta.md`, and it fails three ways at once. `generate_session_delta` opens it with `"w"`, so each session overwrites the last and nothing accumulates. It is gitignored. No entry-point file references it, so no agent reads it on turn one. Fast orientation falls back to the static, hand-maintained `CLAUDE.md`.

The harness targets two agents with different loading mechanisms. Copilot auto-loads `copilot-instructions.md` and scoped files in `.github/instructions/` via `applyTo` frontmatter; it has no import mechanism and will not follow a pointer to an arbitrary file. Claude Code loads `.claude/rules/` via `paths` frontmatter. The two entry files are kept byte-identical by `sync-claude-rules.py`. Any memory surface that must load for both agents has to ride that pipeline, not a Claude-only import or a free-floating file.

Instruction files carry a hard 4,000-char limit. `sync-claude-rules.py` fails any file whose output exceeds it, and the pre-commit hook runs sync then validate, so an oversized file blocks the commit. A memory surface delivered as an instruction file inherits this ceiling.

The Stop hook sees only low-fidelity data: tool name, path, extension, domain hint, outcome. It cannot derive durable understanding such as a confirmed convention or a decision the session reached. Anything it writes unattended is a thin breadcrumb, not knowledge.

Three quality attributes conflict. Guaranteed turn-one loading for both agents forces the 4,000-char ceiling, which limits capacity. Full automation keeps memory current but commits unreviewed, low-fidelity content, which erodes trust. Committing all learning data maximizes sharing but fills git history with high-churn, path-leaking noise and invites merge conflicts.

---

## Decision

We will establish a committed project-memory file delivered through the existing instruction-file pipeline, and draw a clear boundary between shared and local learning data. This serves the no-re-orientation requirement with a surface that loads on turn one for both agents, and it makes the learning loop's durable output survive a clone.

Memory is authored as `.github/instructions/memory.instructions.md` with `applyTo: "**"` and synced to `.claude/rules/memory.md`. This is the only mechanism that guarantees a turn-one load for both Copilot and Claude Code, because Copilot has no way to follow a pointer to a separate file. The cost is the 4,000-char ceiling, accepted deliberately: committed memory is a curated digest, not a growing log.

We commit the curated layer and keep the raw layer local. The memory digest is committed now; the confirmed-instinct store joins it once its serialization is defined (see Technical debt). `observations.jsonl`, `instincts/`, `.session-notices/`, `last-modified.json`, and the accumulating `session-delta.md` log stay gitignored. This shares durable knowledge so a clone inherits it, while keeping high-churn, path-leaking raw data out of git history.

Durable facts are curated, not auto-committed. The Stop hook changes from overwriting `session-delta.md` to appending each session as a new block, so the local, gitignored log accumulates across sessions. The `continuous-learning` skill gains a step that reads that log, proposes durable facts, and on approval writes them into the memory source file. This routes memory through the same human-reviewed promotion the rest of the pipeline uses, and it respects the instruction-integrity guardrail, since the memory source lives under `.github/instructions/`.

---

## Other Considerations

**Committed memory file with a pointer from the entry files.** A standalone `.claude/memory.md` referenced as "read first" removes the 4,000-char ceiling and allows unbounded accumulation. It fails the cross-agent requirement: Copilot has no import mechanism and will not auto-load or follow a pointer to an arbitrary file, so the turn-one guarantee holds for Claude only. This stays the fallback if curated memory proves too large for the cap; it would then pair a capped digest with a fuller local file.

**Claude `@import` plus an inlined Copilot copy.** Claude's native `@import` gives the strongest Claude-side load. Maintaining an inlined Copilot copy breaks the byte-identical entry-file invariant that `sync-claude-rules.py` enforces and would require sync-script changes. The added divergence is not worth a marginal loading gain over the instruction-file pipeline.

**Commit all learning data.** Tracking `observations.jsonl`, `instincts/`, and the deltas maximizes sharing. The raw observation file rotates at 1,000 entries and records paths and command fragments, so committing it pollutes history, leaks local detail, and produces merge conflicts on nearly every session. The curated-layer boundary captures the sharing benefit without the noise.

**Keep all learning data local.** This is the status quo the ADR exists to change. It keeps git history clean but leaves every clone and teammate starting from zero, and it leaves the no-re-orientation requirement unmet. It is the problem statement, not a viable option.

**Let the Stop hook append durable facts directly to committed memory.** This keeps memory current with no review step. The hook has only low-fidelity data, so it would commit unreviewed breadcrumbs, churn the file every session, and risk breaching the 4,000-char cap unattended, which would block commits. Curation under review trades immediacy for trust and a bounded file.

---

## Consequences

**Pros**

- Both agents orient on turn one from a shared, committed digest. The no-re-orientation requirement is met for the first time.
- A fresh clone, a new teammate, or a second machine inherits the curated digest and the confirmed-instinct store.
- Memory updates flow through the existing human-reviewed promotion path. No new trust surface is introduced.
- Raw, noisy, path-leaking data stays local. Git history stays clean.
- No new infrastructure. The design rides the sync pipeline, the pre-commit validation, and the `continuous-learning` skill.

**Cons**

- Committed memory is hard-capped at 4,000 chars, shared with the always-loaded instruction budget. That is roughly one tight page.
- Memory is only as current as the last curation pass. Between passes, the committed digest lags the local log.
- The `continuous-learning` skill grows a curation step, and the memory file needs a defined format.
- The accumulating delta log is itself local. Only its promoted digest crosses machines, so raw session history is not shared.

**Technical debt**

The 4,000-char ceiling may prove too small for useful memory. If it does, the trigger to revisit the pointer-file option should be recorded rather than discovered by hitting a failed sync. Separately, committing the confirmed-instinct store needs a defined serialization and a decision on whether confidence and decay state travel with it, since `instincts/` is gitignored today and its files were never shaped for review diffs.

---

## Enforcement / Guidance

- The memory source is `.github/instructions/memory.instructions.md` with `applyTo: "**"`; the sync mirrors it to `.claude/rules/memory.md`. `validate-system.py` checks it like any other rule: frontmatter present, body non-empty, under 4,000 chars, sync state current. The pre-commit hook blocks a broken or oversized state.
- `observe.py` `generate_session_delta` appends each session as a new block to the local, gitignored `session-delta.md` instead of overwriting it. The Stop hook never writes committed memory.
- The `continuous-learning` skill gains a step: read the delta log, propose durable facts, and on developer approval write them into the memory source file, never the synced mirror. Edits to the source follow the instruction-integrity guardrail.
- `.gitignore` needs no change for memory: the source under `.github/instructions/` and the mirror under `.claude/rules/` are already tracked, while `observations.jsonl`, `instincts/`, `.session-notices/`, `last-modified.json`, and the `session-delta.md` log stay ignored. Sharing the confirmed-instinct store is a later step, gated on the serialization decision in Technical debt.
- `copilot-instructions.md` and `CLAUDE.md` list memory under the universal instruction files so its role is documented where the other rules are.

---

## References

- Continuous Learning Subsystem Audit, agentic-dev-support-harness, 2026-06-01. Source of the P1 items this ADR resolves.
- ADR-PROJECT: Add a Research Instruction File, `docs/adr/adr-project-add-research-instruction-file.md`. Prior art for delivering a universal rule through the instruction-file pipeline.
