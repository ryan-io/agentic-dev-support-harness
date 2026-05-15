---
name: architecture-layering
description: >
  Classify identified volatilities into a layered architecture. Applies the
  Four Questions (who/what/how/how/where), assigns components to the Client, Business Logic,
  ResourceAccess, and Resource layers plus the Utilities bar, distinguishes Managers (sequence
  volatility) from Engines (activity volatility) and ResourceAccess, and validates names against
  naming conventions. Use this skill when the user mentions "the four questions",
  "Manager Engine ResourceAccess", "layered architecture", "which layer", "classify services",
  "name this service", "service taxonomy", "architecture layers", or has a list of volatilities and
  wants them structured into an architecture. This is the back end of the volatility-design
  pipeline: it consumes the output of the volatility-decomposition skill.
---

# Architecture Layering

This skill runs as an interactive session. It takes a set of identified volatilities and structures them into a layered architecture. It is the final stage of the design pipeline: behavioral-requirements -> volatility-decomposition -> architecture-layering.

This stage produces system architecture, not detailed design: classification and naming, not implementation. Done well, the layering makes the architecture readable and the boundaries defensible.

## Input and Output

Input: a volatilities list. If `docs/design/{slug}/volatilities.md` exists, read it as the starting point. Otherwise ask the user to enumerate the volatilities (and suggest running volatility-decomposition first).

Output: a layered architecture saved to `docs/design/{slug}/architecture.md` containing the layer assignment table, the named services, and the classification rationale.

If `docs/design/{slug}/architecture.md` already exists, this is a revision. Read it first, apply the requested change, preserve all other content and the conventions below, confirm before overwriting, and save to the same path unless the user renames it.

## The Four Questions

The four layers loosely map to who, what, how, and where. Use the questions as the first cut: bin each volatility by which question it answers.

- **Who** interacts with the system -> Client layer
- **What** is required of the system -> Managers
- **How** the system performs business activities -> Engines
- **How** the system accesses resources -> ResourceAccess
- **Where** the system state lives -> Resources

The result will not be perfect. Not every "what" maps one-to-one to a Manager, and crossover happens. If the volatility encapsulation is justified, trust it.

Litmus test as you go: are all Clients purely "who" with no "what"? Are all Managers purely "what" with no "who" or "where"? If a name feels wrong against its question, the classification is probably off.

## Layering

Four horizontal layers, top to bottom, with one cross-cutting vertical bar:

1. **Client** entry points: end-user apps or other systems.
2. **Business Logic**, in two tiers: Managers (orchestration) above Engines (domain logic).
3. **ResourceAccess**: abstraction over the actual resources.
4. **Resource**: data stores and external systems.
5. **Utilities** (vertical): Security, Logging, Diagnostics, Pub/Sub, Message Bus, Hosting. Spans all layers; not a fifth layer, a shared slice every layer can use.

Layers enable layered encapsulation: services inside a layer encapsulate volatility from each other. Even simple systems should be layered. Use only a handful, terminating at a layer of physical resources.

## Phase 1: Client Layer

The layer is called "client", not "presentation", because consumers are not only humans; a client can be another system. Calling it the client layer equalizes all consumers: same entry points, same access security, same data types. The client layer encapsulates volatility in clients and is often the most volatile part of the system.

Ask: "Which volatilities are about who consumes the system, or how they reach it?" Those are Client candidates.

## Phase 2: Business Logic, Managers vs Engines

The business logic layer implements the system's required behavior, best expressed as use cases. A use case changes in only two ways, and the two are orthogonal:

- The **sequence** of activities changes (parallel, sequential, conditional ordering).
- The **activities themselves** change.

That split drives the two component types:

- **Managers** encapsulate volatility in the *sequence* (orchestration, workflow). A Manager tends to own a family of related use cases.
- **Engines** encapsulate volatility in the *activities* (business rules, computation). Engines have narrower scope.

Mapping to known patterns: a Manager is an Orchestrator / Mediator / Saga orchestrator (it sequences calls, holds no domain logic). An Engine is a Strategy / Domain Service (it computes, unaware of workflow context).

Dependency rule: Managers may call Engines and other Managers. **Engines never call Managers.** Managers use zero or more Engines; Engines are shared across Managers because the same activity recurs across use cases. Design Engines for reuse.

Duplicate-Engine smell: if two Managers use two different Engines for the same activity, it is either functional decomposition (Engines named by caller, not by volatility, so consolidate) or missed activity volatility (the Engines differ but the axis was not named). Litmus: if swapping one Engine for the other breaks nothing, it is duplication.

Ask, for each Manager candidate: "Does the ordering of steps change independently from the steps themselves?" Sequence volatility justifies the Manager. Then ask whether any activity inside it has "an unknown number of ways of being done." Only then does an Engine exist.

## Phase 3: ResourceAccess and Resource

**ResourceAccess** encapsulates volatility in *how* a resource is accessed, and the volatility in the resource itself (local DB vs cloud, durable vs in-memory). A resource change invariably changes ResourceAccess.

Watch for leaky contracts. Most access layers expose CRUD-like (`Select`, `Insert`, `Delete`) or IO-like (`Open`, `Read`, `Write`, `Seek`) operations that betray the resource type through the contract surface. Changing a leaky contract ripples to every Engine and Manager that depends on it. Phrase ResourceAccess operations in **atomic business verbs** instead: the lowest-level business operations that cannot be expressed by any other (e.g., credit and debit for a transfer). Atomicity is defined from the business perspective, even if a verb takes several system steps to implement.

ResourceAccess can be shared between Managers and Engines; design it for reuse.

**Resource** holds the actual physical resources: databases, file systems, caches, queues. A resource may be internal or an entire external system that, to yours, looks like just a Resource.

## Phase 4: Utilities

Place cross-cutting infrastructure in the Utilities bar: Security, Logging, Diagnostics, Instrumentation, Pub/Sub, Message Bus, Hosting. These follow different rules from the layered components and are available to every layer. Identity propagation across a call chain (chain-of-trust: OAuth2 token exchange, JWT claim propagation, mTLS identity headers) lives here; the propagation mechanism is volatile, the need for identity flow is stable.

## Phase 5: Name the Services

A taxonomy used in name only still produces functional decomposition; naming is where it is most easily faked.

Conventions:

- Service names are two-part compound words in PascalCase.
- Suffix is the type: `Manager`, `Engine`, or `Access` (for ResourceAccess).
- Prefix by type: Manager takes a noun for the use-case volatility (`TradeManager`); Engine takes a noun for the activity (`PricingEngine`); ResourceAccess takes a noun for the resource provided (`AccountAccess`).
- **Gerunds (-ing) are valid only for Engines.** Engines "do" things: aggregate, validate, calculate, transform, translate, locate, search. `CalculatingEngine` is fine. A gerund prefix on a Manager or Access signals functional decomposition.
- Atomic business verbs do not belong in service names; reserve them for ResourceAccess operation names.

Good: `AccountManager`, `AccountAccess`, `PricingEngine`. Smells: `BillingManager`, `BillingAccess` (gerund-flavored "doing"), `AccountEngine` (no activity volatility; reads as domain decomposition).

Validate each name against its question: a Manager prefix should read as "what," an Engine prefix as "how (business)," a ResourceAccess prefix as "how (access)." If it does not, the classification is probably wrong.

## Phase 6: Sanity Checks

**Manager-to-Engine ratio.** Most designs end up with fewer Engines than expected. An Engine exists only where there is fundamental operational volatility, an unknown number of ways of doing something. Such volatilities are uncommon. A large number of Engines signals inadvertent functional decomposition. Orchestration complexity and activity complexity correlate: a single correctly scoped Manager usually implies zero or one Engine. Multiple Engines under one Manager may mean the Manager is a god service hiding several use-case families.

**Functional decomposition coexists, at the code level only.** Inside a component, normal OOP factoring (extract method, helper classes, SRP) is fine and expected. That is code-level functional decomposition. The mistake is promoting an internal helper to an architectural Engine without volatility justification, or decomposing the architecture functionally and relabeling it with these terms. No volatility means no Engine; the Manager holds the logic inline. That is correct design, not laziness.

**The top-down gradient.** In a well-designed system, volatility decreases going down the layers and reuse increases, the inverse of each other. Clients are the most volatile and hardly ever reusable. Managers change when use cases change. Engines change only when the business changes how it performs an activity, which is rarer. ResourceAccess is less volatile still and the most reusable, callable by both Engines and Managers. Validate the classification against the gradient: a proposed Engine more volatile than the Manager above it, or a Client expected to be reused, signals a wrong layer assignment.

**Manager expendability.** Managers fall into three categories: expensive, expendable, and almost expendable. An expensive Manager holds too much logic and is likely a god service hiding several use-case families. An expendable Manager encapsulates no real use-case volatility and exists only to satisfy the taxonomy; that is always a design flaw. A well-designed Manager is almost expendable: it merely orchestrates Engines and ResourceAccess, encapsulating sequence volatility. Litmus: a proposed use-case change should require only contemplative adaptation of the Manager, not a rewrite.

## Phase 7: Write the Architecture

Present the layer assignment, then write `docs/design/{slug}/architecture.md`:

1. Layer assignment table: each service, its layer, the volatility it encapsulates, and the question it answers.
2. Named services with one-line rationale each.
3. Sanity-check notes (ratio, gradient, Manager expendability, anything left unencapsulated on purpose).
4. References, if the design cites external sources.

Where a cohesive set of services (a Manager with its Engines and ResourceAccess) implements a family of use cases, group them in the document as a subsystem: a vertical slice of the system.

For the interactions between these services, hand off to the `sequence-diagram` skill: behavior emerges from how the encapsulated volatilities interact, and that is best shown as a diagram. When the developer is ready to build, hand off to the `implementation` skill to pair-program these services into C#/WPF code.
