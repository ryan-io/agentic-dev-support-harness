---
name: architecture-design-pipeline
description: >
  Run the volatility-based design method end to end as a guided pipeline: capture behavioral requirements,
  decompose by volatility, then layer the result into an architecture. Use this skill when the
  user wants the full design flow rather than one stage, or mentions "design this system",
  "the full design flow", "run the whole pipeline", or "requirements to
  architecture". This is a thin orchestrator over three standalone skills: behavioral-requirements,
  volatility-decomposition, and architecture-layering. Each of those can also be run on its own.
---

# Architecture Design Pipeline

This skill is a conductor, not a new method. It runs the three design skills in order, sharing one `docs/design/{slug}/` folder so each stage feeds the next. It adds no design logic of its own; all substance lives in the stage skills.

Pipeline: behavioral-requirements -> volatility-decomposition -> architecture-layering.

## Setup

Ask what system, feature, or problem to design. Derive a kebab-case `{slug}` and confirm it. Create `docs/design/{slug}/` if it does not exist. Tell the user the three stages and that they can stop after any one.

Check for existing artifacts in `docs/design/{slug}/`. If `use-cases.md`, `volatilities.md`, or `architecture.md` already exist, offer to resume from the first missing stage rather than redo completed work.

## Stage 1: Behavioral Requirements

Invoke the `behavioral-requirements` skill for `{slug}`. It produces `docs/design/{slug}/use-cases.md`. When it finishes, confirm the user wants to continue before moving on.

## Stage 2: Volatility Decomposition

Invoke the `volatility-decomposition` skill for `{slug}`. It reads `use-cases.md` as input and produces `docs/design/{slug}/volatilities.md`. Confirm before continuing.

## Stage 3: Architecture Layering

Invoke the `architecture-layering` skill for `{slug}`. It reads `volatilities.md` as input and produces `docs/design/{slug}/architecture.md`.

## Close

Summarize the three artifacts and their paths, then offer two handoffs. The `implementation` skill pair-programs the architecture into C#/WPF code, since building is the architecture's reason for existing. The `sequence-diagram` skill draws the service interactions, since behavior emerges from how the encapsulated volatilities interact.

## Running Stages Independently

Each stage skill works standalone and reads whatever upstream artifact exists in `docs/design/{slug}/`. A user who already has use cases can start at volatility-decomposition; a user with a volatilities list can start at architecture-layering.
