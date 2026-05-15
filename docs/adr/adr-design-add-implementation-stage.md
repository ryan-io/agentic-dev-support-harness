# ADR-DESIGN: Add a Pair-Programming Implementation Stage to the Design Pipeline

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-08 |
| Authors | @ryan-io   |

---

## Context

The design pipeline ends at `architecture.md`: named services classified into layers. The `docs/design/README.md` says these artifacts are "promoted into code, ADRs, or business rules," but nothing operationalizes the promotion into code. The architecture sits as a document, and `architecture.md` is a dead end for the one outcome the design exists to produce.

Turning an architecture into code is where design problems surface. A contract leaks the resource type, a Manager grows god-like, an Engine that the layering predicted turns out to have no real activity volatility. These show up only when someone writes the code. A batch generator that emits the whole solution in one shot hides them: it produces code no one reviewed incrementally and drifts from the design the moment reality pushes back.

The harness already supplies the build pieces. `scaffold.py` lays a base C#/WPF solution from `templates/`, backed by its own ADR, and `docs/process/` holds dated working plans. Reusing both avoids inventing parallel conventions. The stack is fixed for this project: C# backend, WPF frontend.

The quality attributes in tension are throughput against fidelity, and automation against developer control. A one-shot generator maximizes throughput but spends the developer's review budget all at once and lets the design and the code diverge silently. A human-in-the-loop pairing session is slower per service but keeps the design honest and catches decomposition errors while they are cheap to fix.

Doing nothing leaves `architecture.md` as a terminal document and leaves the README's "promoted into code" claim unbacked.

---

## Decision

We add a fourth pipeline stage, the `implementation` skill, that runs as an interactive pair-programming session. The agent drives, the developer navigates. It consumes any combination of `docs/design/{slug}/use-cases.md`, `volatilities.md`, and `architecture.md`, builds a backlog of services from the architecture, and implements them one at a time in C#/WPF: restate the contract, write the interface, write the implementation, write a test, build, go green, reflect, commit a small increment, move to the next service.

The skill reads upstream artifacts by file-handoff coupling, the convention the design-pipeline ADR set. A stage depends on the shape of an artifact, not on an upstream skill having run. With no artifacts present, the skill works from what the developer describes.

The design artifacts stay the source of truth. When the code wants to diverge from the architecture, the session stops and names it rather than silently diverging. A missed or extra volatility routes back to `volatility-decomposition` or `architecture-layering` to revise the artifact. The skill stays strictly to implementation: ADR governance for a new pattern, cross-cutting concern, or third-party dependency is not its job and stays with the always-on `agent-guardrails` rule.

Scaffolding is a bootstrap, not the point. When no solution exists to pair on, the skill offers to lay the base C#/WPF solution once via `scaffold.py`, then pairs on top of it. Pairing needs a codebase. The session keeps a lightweight backlog note in `docs/process/{date}-{slug}-implementation-plan.md` so the work resumes across sessions.

The skill is added to `architecture-design-pipeline` as a Close handoff offer, not a core stage. The orchestrator stays logic-free: it offers the next step the same way it already offers `sequence-diagram`.

A pairing session keeps the developer in control of the most consequential translation in the pipeline and surfaces decomposition errors while they are cheap. Reusing `scaffold.py` and `docs/process/` keeps the harness's conventions instead of forking new ones.

---

## Other Considerations

**Batch generate the whole solution in one pass.** Maximum throughput, and tempting because the architecture already names every service. Rejected: it spends the developer's review budget all at once, produces code reviewed only after the fact, and drifts from the design as soon as a contract or a Manager pushes back. The pairing loop exists precisely to catch those at the point they appear.

**A plan-only stage that writes a build plan and stops.** Useful and partly kept: the session keeps a backlog note in `docs/process/`. On its own it leaves the same gap this decision exists to close, the actual code, so it is folded into the pairing skill rather than chosen alone.

**Two separate skills, one planner and one implementer.** Cleaner descriptions, but the backlog and the pairing share one design and almost always run together. The split adds a handoff with no real decoupling benefit. Rejected. Revisit if planning proves useful without ever implementing.

**Make it a core orchestrator stage, like the three design stages.** Gives one command end to end, but implementation is interactive and open-ended, a different shape from the three bounded design passes, and not every design proceeds to build. Kept as an optional handoff instead.

**Stack-agnostic pairing that asks per run.** More reusable for the template, but this project is fixed on C#/WPF and the scaffolder's csharp templates already cover it. The skill targets C#/WPF and defers other stacks to a future change.

---

## Consequences

Pros: `architecture.md` now has a defined consumer, so the README's "promoted into code" path is real; the developer stays in control of the design-to-code translation and sees decomposition errors while they are cheap; drift back into the design artifacts is explicit, not silent; and the skill reuses `scaffold.py` and `docs/process/` rather than new conventions.

Cons: a fifth skill in the design family to keep registered and in sync; pairing is slower per service than batch generation; and the optional bootstrap couples the skill to the `scaffold.py` CLI and the csharp templates, so a change there can break that step.

Technical debt: the backlog note in `docs/process/` can fall out of date if the architecture changes after a session, since nothing re-syncs it to a revised `architecture.md`. The resume step recomputes the backlog from the artifacts and the code, but does not reconcile already-written code to a changed design. This is acceptable while the backlog is a working aid, not a gated record.

---

## Enforcement / Guidance

Register the skill in the four locations `skills/README.md` documents: the `SKILL.md`, the `skills/README.md` catalog, the `copilot-instructions.md` and mirrored `CLAUDE.md` hub list, and the `system-index.md` table. Then run `.github/scripts/sync-claude-rules.py`, and `.github/scripts/validate-system.py` must pass with zero failures.

The session works in small increments: one service at a time, a test before moving on (`code-standards`: all new logic has tests), and a conventional commit per increment (`agent-guardrails`). It does not write several services then build.

The design artifacts stay the source of truth. When code and architecture disagree, the session resolves it explicitly: fix the code, or revise the artifact through the relevant stage skill. The skill stays strictly to implementation. ADR governance for a new pattern or dependency is not embedded here; the always-on `agent-guardrails` rule already requires it, repo-wide.

The bootstrap step invokes `python .github/scripts/scaffold.py csharp --type wpf ...` (or `wpf-ef`) only when no solution exists, rather than writing base-solution files directly. Code follows `csharp-code-standards`: file-scoped namespaces, nullable enabled, `I`-prefixed interfaces, `Async` suffixes, constructor injection through the DI host. The layering dependency rules hold: Managers may call Engines, Engines never call Managers.

The orchestrator offers implementation at Close and adds no logic. If it accumulates pairing logic, that logic belongs in the skill.

---

## References

- Löwy, Juval. *Righting Software*. Addison-Wesley, 2019.
- `docs/adr/adr-design-establish-architecture-design-pipeline.md`
- `docs/adr/adr-scaffold-introduce-ah-ide-cli.md`
