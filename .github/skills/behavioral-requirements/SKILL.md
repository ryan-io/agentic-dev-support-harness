---
name: behavioral-requirements
description: >
  Interactively capture requirements as required behavior rather than functionality.
  Elicits use cases (sequences of activities), draws activity diagrams
  for anything with nested conditionals, and flags solutions masquerading as requirements
  for the volatility pass that follows. Use this skill when the user mentions "use cases",
  "required behavior", "behavior not functionality", "capture requirements", "activity
  diagram", "what should the system do", or wants to gather requirements before designing a
  system. This is the front end of the volatility-design pipeline: its output feeds the
  volatility-decomposition skill.
---

# Behavioral Requirements

This skill runs as an interactive session. The agent asks questions to draw out *how the system must operate*, then records the result as use cases. It is the first stage of the design pipeline: behavioral-requirements -> volatility-decomposition -> architecture-layering.

The guiding rule: **requirements should capture required behavior, not required functionality.** "The system should do A" leaves implementation open to interpretation. "When X happens, the system does B then C" specifies how the system operates.

## Output

A use-case spec saved to `docs/design/{slug}/use-cases.md`, where `{slug}` is a kebab-case name for the system. Phase 4 defines the contents.

If `docs/design/{slug}/use-cases.md` already exists, this is a revision. Read it first, apply the requested change, preserve all other content and the conventions below, confirm before overwriting, and save to the same path unless the user renames it.

## Starting the Session

Ask one question at a time. Do not monologue about the method.

Opening: "What system, feature, or problem do you want to capture requirements for?" Derive a kebab-case `{slug}` from the answer and confirm it. All pipeline artifacts for this work live in `docs/design/{slug}/`.

## Phase 1: Elicit Required Behavior

Requirements arrive as functionality, because that is the language of customers, management, and marketing: "the system should do this and that." Your job is to convert each into behavior.

For each stated need, ask: "Walk me through what happens. Who or what initiates it, what sequence of activities occurs, and what is the end state?" Capture the answer as a use case: a particular sequence of activities that accomplishes work and adds value. Use cases can describe end-user interactions, system-to-system interactions, or back-end processing.

## Phase 2: Choose a Representation

Capture use cases textually or graphically. Prefer graphical for anything with branching.

Rule of thumb: **if a use case contains a nested "if", draw it.** No reader parses a sentence with a nested conditional.

Prefer **activity diagrams** because they capture time-critical and sequential aspects of behavior. Do not confuse them with use-case diagrams, which are user-centric and carry no notion of time or sequence.

Capture activity diagrams as Mermaid `flowchart` blocks or Excalidraw markdown; both render natively in Obsidian. For interaction flows between participants (request/response, message passing), hand the use case to the `sequence-diagram` skill.

## Phase 3: Flag Solutions Masquerading as Requirements

Stated requirements are usually full of solutions disguised as needs. You do not have to resolve these here; the drilling technique lives in the `volatility-decomposition` skill. Your job is only to mark them.

For each use case, ask once: "Is this the actual need, or one way of meeting a deeper need?" Where the answer is "one way," note the candidate in a "Solutions to scrub" list so volatility-decomposition can drill into it.

## Phase 4: Write the Spec

Present the consolidated use-case list back to the user for confirmation, then write `docs/design/{slug}/use-cases.md`:

1. System summary (one or two sentences).
2. Use cases: each as a numbered behavior, with an activity diagram where Phase 2 warranted one.
3. "Solutions to scrub": the flagged candidates from Phase 3.
4. References section.

## Handoff

After saving, offer the next stage: "These use cases are ready. Want me to run volatility-decomposition against them to find what is likely to change?" If yes, that skill reads `docs/design/{slug}/use-cases.md` as its input.
