# ADR-DESIGN: Establish a Staged Skill Pipeline and docs/design Artifact Convention

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-03 |
| Authors | @ryan-io   |

---

## Context

The harness carries skills for Juval Löwy's Method. The `volatility-decomposition` skill covered volatility identification. The reference material it draws on has since grown to cover two more activities: capturing requirements as behavior rather than functionality, and classifying volatilities into the Method's layered structure (the Four Questions, the Manager/Engine/ResourceAccess taxonomy, naming conventions).

Folding all three activities into one skill produces a god skill. It mixes requirements discovery, volatility identification, and structural classification, which are three distinct activities used at different times. Its frontmatter description would have to span all three, and skills are matched by that description. A broad description misfires: it fires on unrelated prompts and dilutes triggering on the prompts it should catch.

The three activities are also used independently. A user often wants only volatility decomposition, or only the layering pass against a list they already have. A single skill forces the whole flow or none of it.

The competing quality attributes are cohesion against convenience, and composability against duplication. Single-purpose skills are cohesive and trigger precisely, but a user who wants the full flow then has to invoke three skills in order. The stages also need to share intermediate results without becoming coupled: a downstream stage should work whether the upstream stage ran or the input was written by hand.

Doing nothing leaves the new material trapped in one bloating skill or in personal notes, and leaves the skill description imprecise.

---

## Decision

We adopt three single-purpose skills forming a pipeline, `behavioral-requirements` then `volatility-decomposition` then `architecture-layering`, plus a thin orchestrator, `architecture-design-pipeline`, that sequences them. Each stage skill also runs standalone.

Stages hand off through files in a new per-run directory, `docs/design/{slug}/`, holding `use-cases.md`, `volatilities.md`, and `architecture.md`. Each stage reads the upstream artifact if it exists and writes its own. This is file-handoff coupling, not code coupling: a stage depends on the shape of an artifact, not on the upstream skill having run, so any stage works from hand-written input.

Single-purpose skills keep each description precise, which improves trigger accuracy, and keep each stage independently usable and testable. The file handoff keeps stages composable while decoupled. The orchestrator gives one-command convenience without a god skill, because it adds no design logic of its own. The new `docs/design/` location separates ephemeral design working files from `docs/adr/` and `docs/business-rules/`, which hold durable records that must not be deleted.

---

## Other Considerations

One combined `righting-software` skill solves discoverability through a single name, but it is the god skill this decision exists to avoid: imprecise triggering, mixed concerns, and hard to revise one activity without disturbing the others. Rejected. It may be revisited only if the stages prove never to be used independently, which the usage pattern makes unlikely.

Handoff prompts with no orchestrator, where each skill offers to invoke the next, is lighter and was partly adopted: the handoff prompts exist. On its own it gives no single entry point for the full flow, so it is complemented by the thin orchestrator rather than chosen alone.

Reusing existing directories, sending activity diagrams to `docs/diagrams/` and the rest to the skill workspace folder, avoids a new convention but scatters one logical design across unrelated locations and gives no per-run grouping. Rejected for the volatility and architecture artifacts. Activity diagrams still defer to the existing `sequence-diagram` skill, which writes to `docs/diagrams/`.

A single evolving document, one `docs/design/{slug}.md` that every stage appends to, has the smallest file count but conflates three separately review-worthy artifacts and makes partial reruns awkward. Rejected in favor of one file per stage inside a per-run folder.

---

## Consequences

Pros: skill descriptions trigger precisely; each stage is independently usable and testable; stages compose through stable artifact shapes; design working files are cleanly separated from durable records; and the pattern, staged single-purpose skills sharing file artifacts, is reusable for future multi-step skills.

Cons: a new top-level `docs/design/` directory to learn and maintain; four skills to keep registered and in sync instead of one, each touching the five registration points in `skills/README.md`; and the orchestrator must be policed to stay logic-free.

Technical debt: the `{slug}` convention is by agreement, not enforced by tooling, so a mistyped slug breaks a handoff silently. Artifact shapes are conventional, not schema-validated, and `docs/design/` is not yet referenced by `validate-system.py` or any review rule, so nothing checks their structure. This is acceptable while the artifacts are working files. Revisit if they become review-gated.

---

## Enforcement / Guidance

When adding or changing a stage skill, register it in the five locations `.github/skills/README.md` documents: the `SKILL.md`, the `skills/README.md` catalog, the `copilot-instructions.md` and mirrored `CLAUDE.md` hub list, and the `system-index.md` table. Then run `.github/scripts/sync-claude-rules.py`, and `.github/scripts/validate-system.py` must pass with zero failures.

A stage skill must read `docs/design/{slug}/<upstream-artifact>.md` if it exists and write its own artifact to the same folder. The `{slug}` is derived once from the system name and confirmed with the user. Design working files live only under `docs/design/`; durable decisions still go to `docs/adr/` and durable constraints to `docs/business-rules/`.

The orchestrator adds no design logic. If it accumulates any, that is the signal that a stage boundary is wrong and the logic belongs in a stage skill.

---

## References

- Löwy, Juval. *Righting Software*. Addison-Wesley, 2019.
- Parnas, David L. "On the Criteria to Be Used in Decomposing Systems into Modules." *Communications of the ACM*, 15(12), 1972.
