---
name: volatility-decomposition
description: >
  Interactively decompose a problem, feature, or system by volatility: identify what is likely
  to change, encapsulate those volatilities behind stable interfaces, and structure components
  around change boundaries rather than business functions. Use this skill when the user mentions
  "volatility decomposition", "axes of volatility", "functional decomposition"
  (as a problem), "service boundaries", "how should I decompose this", "what's likely to
  change", or presents a system, feature, or problem they want to break down into components.
  Also use when reviewing a design that shows symptoms of functional or domain decomposition.
---

# Volatility-Based Decomposition

This skill runs as an interactive session. The agent asks questions to guide the user through decomposition, not lecture about the method. The user brings a problem, feature, or system; help them discover what changes, what doesn't, and where the boundaries belong.

The approach: observe the system aspect by aspect asking what changes, apply the two axes of volatility, scrub away solutions masquerading as requirements, compile a volatilities list, then define boundaries. Design comes last and goes fast. Identifying the correct volatilities is the slow, valuable work.

This is the middle stage of the design pipeline: behavioral-requirements -> volatility-decomposition -> architecture-layering. It can also run standalone.

## Input and Output

Input: if `docs/design/{slug}/use-cases.md` exists (from the behavioral-requirements skill), read it as the starting point, including its "Solutions to scrub" list. Otherwise work from what the user describes.

Output: a volatilities list and the change boundaries, saved to `docs/design/{slug}/volatilities.md`, where `{slug}` is a kebab-case name for the system. The file records the confirmed volatilities, the items set aside as variable or as nature-of-the-business, and the proposed boundaries.

If `docs/design/{slug}/volatilities.md` already exists, this is a revision. Read it first, apply the requested change, preserve all other content and the conventions below, confirm before overwriting, and save to the same path unless the user renames it.

## The Central Question

Every phase of this skill revolves around one question: **"Is this volatile, or just variable?"**

- **Volatile:** open-ended change that, unless encapsulated at the architecture level, ripples across the system. Deserves its own component behind a stable interface.
- **Variable:** bounded change you handle with conditional logic, configuration, or a code-level abstraction. Not an architectural concern.

When something is clearly variable (90%+ confidence), call it out immediately in whatever phase you are in. When the classification is ambiguous, collect it as a candidate and defer judgment to Phase 4, where the full context makes the distinction clearer.

## Starting the Session

Begin by understanding scope. Ask one question at a time; do not monologue about the method.

**Opening question:** "What is the system (or feature, or problem) you want to decompose?"

Derive a kebab-case `{slug}` from the answer and confirm it. If `docs/design/{slug}/use-cases.md` already exists, read it and confirm you are continuing the same work.

If they've already stated it, skip ahead. Once you understand the subject, ask:

"Describe the system at a high level. What are its major aspects, areas, or concerns? Don't think in terms of components yet, just tell me about the system."

The goal is to get the system on the table so you can observe it together. Do not propose components yet.

## Phase 1: Observe and Walk Through

Observe the system with the user, aspect by aspect, like walking through a house. For each aspect the user has described, ask whether it changes.

"Let's walk through the system. Consider [aspect]. Does this change over time? Has it changed before, or do you expect it to?"

For each aspect, follow up: "What specifically changes about it? The technology? The rules? The format? The provider?" Pin down the dimension of change.

As you walk through, maintain a running candidate list of things that seem volatile. Do not commit to design yet. You are compiling observations, not architecture.

If something is clearly variable (90%+ confidence), say so: "That sounds like something you'd handle in code, not an architectural boundary. Does that match your read?" Set it aside and move on.

## Phase 2: Apply the Axes of Volatility

Once you've walked through the system's aspects, apply the two axes systematically to surface anything the observational walk-through missed.

### Axis 1: Same customer over time

Ask: "If one customer used this system for the next five years, what parts would need to change as their situation evolves?"

Follow up on each answer to pin down the dimension of change.

One distinction is key: you wouldn't change the way you send emails based on connectivity type. The transport mechanism (dial-up, fiber) is volatile; the capability (send email) is stable. Encapsulate the volatility behind a stable interface.

### Axis 2: Across customers right now

Ask: "If you deployed this to a second customer today, what would be different?"

Follow up: "Would they use different [protocols / rules / integrations / workflows]? Where does their usage diverge?"

### Apply the Axes Iteratively (A -> B -> C)

Treat the system as one monolithic component (A) and peel it apart by repeating two questions:

1. "Could you use this with one customer forever?" If no, encapsulate what would change over time, producing (B).
2. "Could you use B across all customers right now?" If no, encapsulate what differs across customers, producing (C).

Repeat until every point on both axes is encapsulated. Axis assignment is just a discovery aid: a volatility like "neighbors" may surface on both axes, but once found the component handles it regardless of which axis revealed it.

### Design for Your Competitors

A strong discovery technique: ask the user to imagine building the same system for a competitor or another division. "What would have to change?" Those deltas are volatilities. FedEx and UPS both ship, track, insure, and route packages, yet their systems are not interchangeable; the barriers to reuse are exactly the volatilities.

Heuristic: if there are two ways of doing something, there are likely many more. That is a signal to encapsulate. If FedEx and UPS plan routes differently, route planning is volatile, so designate a component for it; if one later adopts the other's approach, only the implementation changes, not the decomposition.

### The "What if?" Stress Test

For any aspect that hasn't surfaced volatility through either axis, ask targeted questions:

- "What if you switched the database?"
- "What if a new regulation changed the validation rules?"
- "What if you added a mobile client?"
- "What if a third-party API you depend on changed its contract?"

Wherever the answer is "we'd have to change a lot," that's a candidate volatility.

## Phase 3: Scrub Solutions Masquerading as Requirements

Now examine the candidate volatilities list for solutions masquerading as requirements. Most requirements specs are full of them. This is not a problem to work around; it is a powerful analysis technique for discovering the true underlying volatilities.

For each candidate on the list, ask:

"Is [candidate] the only way to satisfy this need, or are there alternatives?"

If alternatives exist, the candidate is a solution, not the real requirement. Drill deeper: "What is the actual need that [candidate] satisfies?" Check whether the answer is itself a solution. Keep drilling until you reach a need with no further abstraction.

Watch for mutually exclusive requirements at each level. If two candidates can't coexist (e.g., "feeding" and "dieting"), that's a signal you haven't reached the true underlying need yet.

Example flow:
- Candidate: "Cooking support"
- Agent: "Is cooking the only way to satisfy this need?"
- User: "No, they could order food or eat out."
- Agent: "So the underlying need is feeding the occupants. But is feeding itself the real requirement? What if the occupants are dieting?"
- User: "The system should support both."
- Agent: "Feeding and dieting are mutually exclusive, which means feeding is still a solution. The real requirement is occupant wellbeing, which encompasses caloric intake, temperature, humidity, and more."

The drilling is repeatable. Each peeled-back solution gets closer to the true volatility. What survives the scrub is a strong candidate for encapsulation.

Why this matters: deploy a system with only `Cooking`, and the customer will ask for pizza delivery next, then dining out, then diet tracking, each iteration bloating or adding components in a cycle around the real requirement. Encapsulate the underlying need (wellbeing) and the design survives when solutions change.

## Phase 4: Confirm the Volatilities List

The volatilities list is an open-ended requirements-gathering artifact, not a scope document. Its job is to surface what could change and instill the right mindset. Some volatilities will be out of scope: designating a component costs almost nothing, so call them out and map them early. Start with the simple decisions.

Present the full picture to the user: confirmed volatilities from the walk-through and axes, items already filtered as variable, and any remaining ambiguous candidates.

For each ambiguous candidate, ask: "If [X] changed, would you need to restructure components and their interfaces, or would you just update code inside an existing component?" The former is volatile. The latter is variable.

Once a volatility is identified, validate it: is addressing it a requirement? Not every volatility warrants an architectural boundary.

### Worked Example (condensed): Trading System

A stock-trading requirements analysis surfaces a list like this. Note how several entries began as solutions masquerading as requirements:

- **Users** (traders, read-only customers, admins) and the **client apps** their differences drive (web, desktop, mobile).
- **Security**: domain accounts for in-house traders vs federated SSO for internet customers.
- **Notification**: "send an email" is a solution; the real volatility is notify (transport, recipient set, publisher).
- **Storage**: "local database" is a solution; the real volatility is "do not lose data" (local DB through distributed cache).
- **Connection and synchronization**: synchronous lock-step vs async queued calls.
- **Trade item** (stocks today; bonds, currencies, futures later) and the **workflow** each item drives.
- **Locale and regulations**, and **market feed** (source, format, rate, protocol).

The list's value is the mindset, not the scope. Several of these will not ship in v1.

Characterize the boundary between functional and volatile. A candidate can look volatile yet be a business function in disguise. Ask: "Does this represent an area of likely change, or something the system does?" If it maps to a business function rather than an axis of change, it is not a volatility boundary.

### The House Example (use to illustrate the distinction)

If the user is struggling with functional vs. volatility thinking, walk them through this example.

A functionally decomposed house would have components like `Kitchen`, `Bedroom`, `Bathroom`, each named for what the house *does* (cooking, sleeping, bathing). But those aren't areas of change. They're behaviors.

Volatility-based decomposition of a house asks: what actually changes?

**Axis 1 (same customer over time):** Furniture, Appliances (CRT to plasma to OLED), Occupants, Appearance, Utilities (dial-up to fiber).

**Axis 2 (different customers at the same time):** Structure, Location Context (neighbors, regulations, building codes, taxes).

Notice: there is no `Cooking` component. Cooking is not a volatility. It's behavior that emerges from interaction between Occupants, Appliances, and Utilities. If you see a component named after a behavior rather than an area of change, that's functional decomposition.

After resolving all candidates, present the consolidated list: "Here are the confirmed volatilities: [list]. Each would break the architecture if uncontained. Does this look right?"

## What Not to Encapsulate

Decomposition identifies both what to encapsulate and what to leave alone. Not everything that could change is volatile.

**The nature of the business.** The core business of a system tends to be constant and should not be encapsulated. FedEx has always been in shipment and delivery; designing for a theoretical pivot into healthcare is out of scope for architectural volatility analysis. Two indicators that a possible change belongs to the nature of the business: it is rare, and any attempt to encapsulate it can only be done poorly, with no practical investment making the encapsulation clean.

**Volatility is inversely related to longevity.** The longer something has been done the same way, the less volatile it is, and the lower the chance it will change. Weight stability over recency when judging.

**Speculative design.** Once volatility-based thinking clicks, it is easy to overdo it and see volatility everywhere. A design that accumulates a building block for every imagined change is itself a sign of bad design. Encapsulate the changes that are real, validated requirements, not the ones you can merely imagine.

Record the "do not encapsulate" decisions in the output alongside the volatilities. They are part of the analysis.

## Phase 5: Define Boundaries

Now propose components. Each encapsulates a coherent area of change behind a stable interface. The mapping from the volatilities list to components is rarely one-to-one: a single component can encapsulate more than one related volatility, so do not assume one volatility means one service.

Present each proposed boundary to the user and ask:

"Does [component] own one coherent area of change? Or is it mixing concerns?"

**Naming matters.** Components are named for what they encapsulate (the volatility), not what the system does. `BillingService` and `CookingModule` name business functions; a volatility-based name points at the area of change it contains. The naming conventions and the Manager/Engine/ResourceAccess taxonomy are applied in the next stage, the `architecture-layering` skill. Here, just keep names pointed at the volatility rather than the business function.

### Validate Independence

For each pair of components, ask: "Can [A] change without forcing [B] to change?"

If not, either they belong together or one is functionally decomposed. The axes should be independent: what changes along Axis 1 should not significantly change along Axis 2. Spanning both axes signals functional decomposition in disguise.

### Check for Missing Boundaries

Ask: "Is there a component here that doesn't map to either axis of volatility?"

If a component exists because the system "does" something rather than because something "changes," it's functional decomposition. Remove it or reframe it around the volatility it should encapsulate.

## Phase 6: Note Interactions and Hand Off

Behavior emerges from interaction between the encapsulated volatilities; there are no dedicated behavior services. Capture this insight, but do not design the structure here.

One thing to flag before handing off: if the client ends up stitching components together (A -> B -> C), the architecture is flat and the client will bloat into the system. Coordination belongs in an intermediary layer, not the client. Note where coordination is needed; deciding where it lives is the next stage's job.

The structural work, where coordination lives, how to classify each component, and how to name it, is the `architecture-layering` skill. Save the volatilities list and proposed boundaries to `docs/design/{slug}/volatilities.md`, then offer the handoff: "The volatilities and boundaries are ready. Want me to run architecture-layering to classify these into a layered architecture?"

## Reviewing an Existing Design

When the user presents an existing architecture for review, follow the same approach framed around what already exists. The most valuable move here is to catch what the user treats as volatile that is actually just variable, and what they treat as fixed that is actually volatile.

1. "Walk me through your current services and what each one is responsible for."
2. For each service, observe it the same way you'd observe an aspect of the system:
   - "Does this encapsulate something that changes, or something the system does?"
   - "If it changes, would the change break the architecture, or could you handle it inside this component?" (volatile vs. variable)
3. Build the volatility axis table interactively:

   | Service | Axis 1 (changes over time?) | Axis 2 (differs across customers?) | Volatile? |
   |---|---|---|---|

4. Check for solutions masquerading as requirements in the existing design:
   - "Is [service name] describing the real need, or a specific solution to a deeper need?"
5. Flag symptoms of functional decomposition (ask, don't assert):
   - "Is the client doing orchestration work that doesn't belong in a presentation layer?"
   - "If [requirement X] changed, how many services would you need to touch?"
   - "Can you integration-test [service] without wiring up the whole system?"
6. For each service that fails the volatility check, ask: "What volatility should this component encapsulate?"
7. For services that pass, verify scope: "Is this service encapsulating one axis of change, or has it absorbed concerns that are actually just variable rather than volatile?"

## Key Principles (for agent reference, not for lecturing)

These inform the agent's questions and reactions. Do not recite them to the user unprompted.

- Functional decomposition is valid for requirements discovery, not for system design. There should never be direct mapping between requirements and components.
- Domain decomposition (breaking by business domain) is functional decomposition in disguise.
- Design determines testability. If a system is hard to integration-test, the problem is the decomposition.

## References

- Parnas, David L. "On the Criteria to Be Used in Decomposing Systems into Modules." *Communications of the ACM*, 15(12), 1972.
- Nygard, Michael. *Release It!*
