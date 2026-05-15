---
name: sequence-diagram
description: >
  Create a Mermaid sequence diagram from a structured specification or natural-language
  description. Guides the user through identifying participants, messages, and interaction
  patterns (loops, conditionals, parallel flows), then generates a markdown file with a
  rendered Mermaid code block. Use this skill when the user mentions "sequence diagram",
  "interaction diagram", "message flow", "call sequence", "request/response flow",
  or describes a workflow between actors, services, or components and wants it diagrammed.
---

# Sequence Diagram Creation

Create a Mermaid sequence diagram from user input. The agent asks targeted questions to clarify participants, message flow, and interaction patterns, then produces a markdown file with the diagram source.

## Output

A single markdown file saved to `docs/diagrams/` containing:

1. A title and brief description of the interaction being modeled.
2. A Mermaid `sequenceDiagram` fenced code block.
3. A References section (if the diagram derives from a book, paper, or external source).

Filename format: `seq-{kebab-case-title}.md`

## Workflow

### Step 1: Understand the Interaction

Ask what interaction the user wants to diagram. If they've already described it, skip ahead.

"What interaction do you want to diagram? Describe the workflow at a high level: who initiates it, what systems or components are involved, and what the end state is."

### Step 2: Identify Participants

Extract participants from the description. Confirm with the user.

"Here are the participants I see: [list]. Are these correct? Should any be added, removed, or renamed?"

Decide participant types with the user:

- `participant` for services, systems, databases, queues.
- `actor` for humans or external callers.

Use aliases when full names are long: `participant GW as API Gateway`.

### Step 3: Map the Message Flow

Walk through the interaction step by step. For each message, clarify:

- **Direction:** Who sends to whom?
- **Synchronous or asynchronous?** Solid arrow (`->>`) for sync, open arrow (`-)`) for async. Dashed arrows (`-->>`) for responses.
- **Label:** What is the message? Use concise labels: `POST /orders`, `validate()`, `OrderCreated event`, not full sentences.

Present the message list back to the user for confirmation before generating.

### Step 4: Identify Interaction Patterns

Ask whether any of these patterns apply. Do not assume they do.

- **Activations:** "Are there points where a participant is actively processing (waiting for a response before continuing)?"
- **Loops:** "Does any part of this flow repeat? Retry logic, polling, batch processing?"
- **Conditionals:** "Are there branching paths? Success vs. failure, different response types?"
- **Parallel flows:** "Do any messages happen concurrently?"
- **Notes:** "Are there any clarifying details that should appear as annotations on the diagram?"

Only include patterns the user confirms.

### Step 5: Generate the Diagram

Produce the Mermaid code block. Follow these conventions:

```
sequenceDiagram
    autonumber
    actor U as User
    participant A as Service A
    participant B as Service B

    U->>A: request
    activate A
    A->>B: downstream call
    activate B
    B-->>A: response
    deactivate B
    A-->>U: response
    deactivate A
```

Conventions:

- Always include `autonumber` unless the user opts out.
- Indent message lines for readability.
- Group related messages with `rect rgb(...)` blocks sparingly, only when the user has identified logical groupings.
- Use `Note over` for annotations that span participants, `Note right of` for single-participant context.
- Keep message labels short. If a label exceeds roughly 40 characters, shorten it and add a Note with the full detail.

### Step 6: Review and Save

Present the generated diagram to the user. Ask:

"Does this capture the interaction correctly? Anything to add, remove, or reorder?"

Iterate until the user confirms. Then save to `docs/diagrams/seq-{kebab-case-title}.md`.

### Step 7: Revise an Existing Diagram

Use this step when the user wants to change a diagram that is already saved, whether from this session or an earlier one.

Read the existing file from `docs/diagrams/seq-{kebab-case-title}.md` first. Work from its current contents, not from memory.

Apply the requested change. Common revisions:

- **Wording:** Adjust message labels, the title, or the description prose.
- **Participants:** Add, remove, or rename a participant. When renaming, update every message line that references the old alias.
- **Message flow:** Add, remove, or reorder messages, or change arrow types.
- **Patterns:** Add or remove a loop, conditional, parallel block, activation, or note.

Keep all other content unchanged. Preserve the conventions from Step 5 (autonumber, indentation, alias usage).

Present the revised diagram and confirm before overwriting, same as Step 6. Save to the same path. Create a new file only if the user renames the diagram; use the new kebab-case filename.

## Mermaid Syntax Reference

Quick reference for the agent. Do not recite this to the user.

### Arrow Types

| Arrow | Meaning |
|---|---|
| `->>` | Synchronous request (solid, filled head) |
| `-->>` | Synchronous response (dashed, filled head) |
| `-)` | Asynchronous message (solid, open head) |
| `--)` | Async response (dashed, open head) |

### Interaction Blocks

```
loop Description
    A->>B: message
end

alt Success
    A-->>B: 200 OK
else Failure
    A-->>B: 500 Error
end

par Task 1
    A->>B: message
and Task 2
    A->>C: message
end

critical Establish connection
    A->>B: connect
option Timeout
    A->>A: retry
end
```

### Notes

```
Note right of A: Single participant note
Note over A,B: Spans both participants
Note left of B: Left-side note
```

### Activations

```
activate A
deactivate A

%% Shorthand: +/- suffix on arrows
A->>+B: request
B-->>-A: response
```

## References

- [Mermaid Sequence Diagram Syntax](https://mermaid.js.org/syntax/sequenceDiagram.html)
