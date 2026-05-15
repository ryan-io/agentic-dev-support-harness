---
name: implementation
description: >
  Pair-program a design into working C#/WPF code. The agent drives, the developer navigates.
  Consumes any combination of the design pipeline's artifacts (use-cases.md, volatilities.md,
  architecture.md) and implements the named services one at a time, test first, keeping the
  design as the source of truth. Use this skill when the user wants to "implement this", "build
  this", "pair with me", "pair program", "let's code this", "turn the design into code", "work
  through the architecture", or has an architecture.md and wants to start building. This is the
  final stage of the design pipeline: behavioral-requirements -> volatility-decomposition ->
  architecture-layering -> implementation.
---

# Implementation (Pair-Programming)

This skill runs as a pairing session, not a batch generator. The agent is the driver: it writes the code in small steps and thinks aloud. The developer is the navigator: they steer, review, and make the calls. The work moves one service at a time through the architecture, staying green, with the design artifacts as the source of truth.

This is the back end of the design pipeline. It turns `architecture.md` into running C#/WPF code. The stack is fixed for this project: C# backend, WPF frontend.

The decision behind this stage is recorded in `docs/adr/adr-design-add-implementation-stage.md`.

## Input

Read whatever exists in `docs/design/{slug}/`, in any combination:

- `architecture.md` (from `architecture-layering`): the named services, layers, and the volatility each encapsulates. This is the backlog.
- `volatilities.md` (from `volatility-decomposition`): the change boundaries behind each service.
- `use-cases.md` (from `behavioral-requirements`): the required behavior each Manager orchestrates.

This is file-handoff coupling: the skill depends on the shape of the artifacts, not on an upstream skill having run. If none exist, ask the developer to point at the design or describe the target, and suggest running the design pipeline first.

## Durable trace

The session keeps a lightweight backlog note at `docs/process/{date}-{slug}-implementation-plan.md`: the service list, the build order, and what is done versus pending. It is a working aid for resuming across sessions, not a gated record. The real output is the code and its tests.

## Setup

Confirm the `{slug}`. Load the artifacts that exist and summarize the architecture back to the developer: the services, their layers, and what each encapsulates. That summary is the backlog.

Check the codebase. Is there a C#/WPF solution to pair on? If not, offer to bootstrap one once:

```
python .github/scripts/scaffold.py csharp --type wpf    --name {Name}
python .github/scripts/scaffold.py csharp --type wpf-ef --name {Name}   # when a database Resource exists
```

Use `wpf-ef` when the architecture has a Resource backed by a database; otherwise `wpf`. Bootstrapping is optional and is not the point of the skill; pairing needs a codebase to pair on.

Agree on the build order. Follow the architecture's top-down gradient in reverse: implement the least volatile, most reusable parts first, because the things above depend on them.

1. ResourceAccess (atomic business verbs over the resources).
2. Engines (activity logic the Managers reuse).
3. Managers (orchestration over Engines and ResourceAccess).
4. Client last (WPF views and view models).

Utilities (Security, Logging, Pub/Sub) come in when the first service needs them, wired through the DI host.

## The Pairing Loop

Repeat per service, smallest useful increment at a time.

### 1. Pick the next unit

Take the next service off the backlog. State what it encapsulates and which layer it lives in. Confirm it is the right next step before writing anything.

### 2. Restate the contract

Name the interface before implementing it. The contract differs by component type:

- **ResourceAccess:** atomic business verbs (`Credit`, `Debit`), never CRUD or IO verbs that leak the resource type.
- **Engine:** the activity it performs, no workflow knowledge.
- **Manager:** the use-case orchestration, no domain logic of its own.
- **Client:** the entry point, no business logic.

Confirm the contract with the developer. This is the cheapest place to catch a decomposition error.

### 3. Drive

Write in small steps: interface, then implementation, then a test. Narrate intent briefly and pause at decision points for the navigator. Follow `csharp-code-standards`: file-scoped namespaces, nullable enabled, `I`-prefixed interfaces, `Async` suffix on async methods, `CancellationToken` through the chain, constructor injection. Register the service in the DI host (`App.xaml.cs`); no service locators or global state.

### 4. Go green

Build and run the test. Show the result. Red to green before moving on. Every new unit gets a test (`code-standards`: all new logic has tests; mock external dependencies).

### 5. Reflect on fidelity

Ask whether the code still matches the design. Watch for the smells the layering skill named:

- A ResourceAccess contract leaking `Select`/`Insert`/`Open`/`Read`: the resource type is bleeding through. Rephrase in business verbs.
- A Manager accreting domain logic: it is becoming a god service. Push the logic into an Engine, or question the use-case boundary.
- Two Managers reaching for two Engines that do the same thing: duplication or a missed activity volatility. Consolidate or name the axis.
- An Engine calling a Manager: forbidden. The dependency runs one way.

Drift is a signal, not a nuisance. When the code and the architecture disagree, resolve it out loud: fix the code, or revise the artifact through `volatility-decomposition` or `architecture-layering`. Never diverge silently.

### 6. Commit a small increment

One conventional commit per unit (`feat`, `test`, `refactor`), imperative, present tense. Then take the next unit.

## Layer-to-Solution Mapping (C#/WPF)

- **Client** -> the WPF App project (`src/{Name}.App`): views and view models.
- **Managers and Engines** -> the Core project (`src/{Name}.Core`): business logic.
- **ResourceAccess** -> Core, or a Data project when using the `wpf-ef` template.
- **Resource** -> external systems, or EF Core SQLite via `wpf-ef`.
- **Utilities** -> cross-cutting services, registered in the DI host in `App.xaml.cs`.

## Close

Summarize what was implemented this session, what is left on the backlog, and any drift flagged back into the design. Update the backlog note. For interaction flows worth a picture, hand off to `sequence-diagram`. Offer to continue next session.

## Resuming a Session

Use this when returning to a design already in progress.

Re-read the design artifacts and the current code first. Work from what is on disk, not from memory. Recompute the backlog: compare the services the architecture lists against what the code already implements, and continue from the first unimplemented unit. Do not regenerate code that exists; read it, then extend it. If the architecture changed since the last session, reconcile it with the developer before writing more code.

## Key Principles (for agent reference, not for lecturing)

- The developer navigates. Surface decisions; do not bury them in a wall of generated files.
- Small steps, frequent green. Do not write three services then build.
- The design is the source of truth. Code serves the architecture, and disagreements get resolved, not hidden.
- Tests are part of the increment, not a later phase.

## References

- Löwy, Juval. *Righting Software*. Addison-Wesley, 2019.
- `docs/adr/adr-design-add-implementation-stage.md`
- `docs/adr/adr-scaffold-introduce-ah-ide-cli.md`
