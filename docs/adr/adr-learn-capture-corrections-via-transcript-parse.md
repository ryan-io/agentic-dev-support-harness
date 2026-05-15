# ADR-LEARN: Capture User Corrections via Transcript Parse

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-01 |
| Authors | @ryan-io   |

Amended 2026-06-05: capture path implemented in `observe.py` with its `validate-system.py` privacy check. The parse runs on SessionEnd, not Stop: SessionEnd is the project's session boundary (Stop fires after every assistant turn) and carries the same transcript path. The explicit developer signal remains deferred per the Decision. Classifier precision is unproven until real sessions flow; the first correction batches get developer review before the signal is trusted, per Enforcement.

---

## Context

The correction detector is named for a signal it cannot see. The audit's P3 goal is to capture a real correction: a user rejecting, contradicting, or redirecting the agent's work. The current observation stream cannot express that. `observe.py` records only tool name, path, extension, domain hint, and outcome. It strips content and never sees the conversation. A user rejecting a successful edit ("no, do it the other way") leaves no trace, because the edit succeeded and the redo looks like ordinary iteration.

The stopgap shipped this session catches a narrower, honest case: the agent's own tool call failed and was retried inside a tight window. That is self-correction, not user rejection. It removed the false positives that fired on ordinary multi-file editing, but it does not capture the signal the audit named. No heuristic over the current stream can recover that signal, because the signal lives in the transcript, not in tool metadata.

Claude Code passes the transcript path to the Stop hook. That is the one place the agent's own machinery can read what the user actually said. Copilot has no hook system, so the learning loop already runs under Claude Code only, and reading the transcript narrows the supported surface no further.

The transcript is the richest source and the most sensitive. It holds every file, command, and secret the agent saw. The shared-vs-local boundary from the project-memory ADR keeps raw observation data local and strips content from what is committed. Any transcript handling inherits that constraint: derived fields only, raw text stays on the machine, nothing sensitive enters the committed store.

`observe.py` never blocks and always exits zero. A transcript parse on Stop runs in that same path, so a malformed or oversized transcript must fail closed, swallow its error, and let the hook exit cleanly.

Three quality attributes conflict. Precision fights recall: an explicit signal the developer triggers is almost never wrong but catches only what the developer marks, while parsing every user turn catches more and reopens the false-positive risk the stopgap just closed. Signal richness fights privacy: the fuller the captured context, the wider the sensitive surface. Automation fights trust: a hands-free classifier keeps the loop running unattended, but one misclassification feeds the detector the same kind of bad signal that started the P3 saga.

---

## Decision

We will capture corrections from the Stop-hook transcript as the primary signal, recording a new `correction` observation that carries derived fields only. This replaces inference-from-repetition with consumption of the actual user language, and it keeps the privacy boundary the project-memory ADR set.

On Stop, the parser walks user turns and classifies each as corrective or not. A corrective turn rejects, contradicts, or redirects the immediately prior agent action. The parser pairs that turn with the agent action and the file or topic it touched, then writes a `correction` observation with three derived fields: the target file or topic, a short normalized description of what changed, and the trigger-phrase category. Raw transcript text is never written to the observation log.

A real correction is strong evidence, so a correction instinct seeds higher than the 0.30 proxy and needs fewer reinforcements to promote. The classifier is conservative by construction: an ambiguous turn is not a correction. This holds precision high at the cost of recall, the safer trade for a detector whose past failure was false positives.

We keep two secondary sources. The explicit developer signal, a slash command or marker phrase recognized at submit time, is added as a high-precision supplement once the capture path exists. The tool-failure self-correction from the stopgap stays, labeled as agent self-correction rather than user rejection, so the two are never conflated.

This ADR authorizes the design and the schema addition. It does not implement them. The quick fidelity wins shipped first; implementation follows under this record, which is why the status is Proposed.

---

## Other Considerations

**Explicit developer signal as the only source.** A slash command or marker phrase the developer uses when correcting, recognized by a `UserPromptSubmit` hook, has near-zero false positives. Its recall depends entirely on developer discipline: a correction phrased in normal conversation without the marker is missed. It is too lossy to stand alone, so it is kept as a supplement to the transcript parse rather than the primary source.

**Tool-failure self-correction as the permanent answer.** The stopgap already captures this, with no transcript handling and no privacy surface. It only sees the agent's own failed-and-retried edits, never a user rejecting a successful one. It is the signal the audit explicitly called insufficient, so it remains a labeled secondary rather than the answer.

**Keep inferring corrections from tool repetition.** This is the pre-stopgap design the audit failed. It fired on ordinary multi-file editing and promoted instincts like "user corrected approach nine times" from a docs session that held no correction. It is the problem statement, not an option.

**Per-turn classification by a model call inside the hook.** Classifying each turn live, as it arrives, would give immediate signal. It adds latency and cost to every turn and places a model call in a hook that must never block. A Stop-time batch parse sees the whole session at once, runs off the critical path, and is cheaper. The richer real-time variant is deferred, not adopted.

**Commit raw transcript or correction text for richer detection.** Storing the verbatim exchange would let the detector use full context. It breaks the shared-vs-local boundary and leaks file contents and commands into git history. Derived fields only, raw text local, is the boundary the project-memory ADR already drew, and this decision honors it.

---

## Consequences

**Pros**

- The detector finally consumes the signal it is named for. The audit's P3 goal moves from unmet to addressable.
- Correction instincts seed on strong evidence, so a genuine correction promotes faster than the 0.30 proxy did.
- The explicit signal gives developers a high-precision way to flag a correction the parser would miss.
- The privacy boundary holds. Only derived fields reach the observation log; raw transcript stays local.
- The design rides the existing Stop hook and observation schema. No new infrastructure.

**Cons**

- Transcript classification is itself a heuristic with its own false-positive risk. It must stay conservative, and its precision must be earned before its instincts are trusted.
- The capability is Claude Code only. Copilot has no hook to read the transcript, so a Copilot-only contributor produces no correction signal.
- `observe.py` grows transcript-handling code on the Stop path, which must fail closed and never block.
- The observation schema and the `continuous-learning` review surface both grow to carry the new observation type.
- The explicit signal is only as good as developer adoption.

**Technical debt**

The classifier's precision is unproven until it runs against real sessions. Until then, correction instincts seed conservatively and a developer reviews the first batches before the seed confidence is trusted. The explicit-signal opt-in is specified here but not built in the first implementation pass. The parser depends on the Claude Code transcript format, an external structure that can change across versions. That dependency should be pinned, and the parse should degrade quietly if the format shifts rather than block the hook.

---

## Enforcement / Guidance

- The `correction` observation carries only derived fields: target file or topic, a normalized change description, and the trigger-phrase category. `observe.py` must never write raw transcript text to `observations.jsonl`. A `validate-system.py` check should assert the correction path emits no transcript content.
- Transcript parsing lives in the Stop branch of `observe.py`, wrapped so any read or parse error is swallowed and the hook still exits zero.
- Raw transcripts and any locally derived intermediates stay gitignored, consistent with the project-memory boundary. Only curated instincts and the memory digest cross machines.
- Correction instincts seed above the 0.30 proxy but still require reinforcement before promotion. The classifier's precision is validated against real sessions, and the developer reviews early correction proposals, before the seed confidence is relied on.
- Implemented 2026-06-05: `parse_transcript_for_corrections` in `observe.py` (SessionEnd branch, fail-closed, 10 MB size guard, format pinned to Claude Code JSONL), fixture-driven privacy check in `validate-system.py`, mock-transcript tests in `.github/scripts/learning/tests/test_corrections.py`. This ADR now governs the capture path.

---

## References

- Continuous Learning Subsystem Audit, agentic-dev-support-harness, 2026-06-01. Defines the P3 goal this ADR addresses.
- Continuous Learning P3 Redesign Plan, agentic-dev-support-harness, 2026-06-01. The detailed design this ADR formalizes, including the signal-source ranking and the schema addition.
- ADR-LEARN: Establish Shared Project Memory, `docs/adr/adr-learn-establish-shared-project-memory.md`. Source of the shared-vs-local boundary and the content-stripping constraint this decision inherits.
