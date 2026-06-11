---
name: adr-creation
description: >
  Interactively create an Architecture Decision Record (ADR). Walks through each section
  of the ADR template, validates against the project's ADR review policy, and saves the
  completed ADR to docs/adr/. Use this skill whenever the user wants to create an ADR,
  document an architectural decision, record a design decision, or mentions "new ADR".
---

# ADR Creation Skill

Create a complete, policy-compliant ADR by walking the user through each section interactively.

## Prerequisites

Before starting, read:
- `.github/docs/adr-template.md`: section structure and placeholder guidance
- `.github/instructions/writing-voice.instructions.md`: applies to all prose drafted in this skill

Apply writing-voice throughout: short paragraphs, plain declarative sentences, no em dashes, no filler. Every sentence must earn its place.

Note: validation rules (`adr-pr-review`) and template policy (`adr-template`) auto-load when working in `docs/adr/`.

## Workflow

### Step 1: Identify the Decision

Ask the user:
- What is the architectural decision? (short title, imperative phrase)
- What is the project prefix for the filename? (e.g., `SOC`, `GRID`, `APP`)

Use these to derive the filename: `adr-{project}-{kebab-case-title}.md`

### Step 2: Forces Discovery

Before writing Context, walk the user through these three questions to surface the forces driving the decision:

1. **What goes wrong if we do nothing?**: Identify the pain. If there is no cost to inaction, this may not need an ADR.
2. **What constraints does our environment impose that a textbook wouldn't assume?**: Desktop vs. web, team size, existing stack, deployment model.
3. **Where do quality attributes conflict?**: Testability vs. simplicity, performance vs. maintainability, flexibility vs. cognitive load.

Every force identified here should create tension that the Decision resolves and Consequences acknowledge. If a force does not connect to the decision, it does not belong.

### Step 3: Walk Through Sections

Present each section one at a time. After the user provides input, draft that section and confirm before moving on.

**Metadata**: Auto-fill Status as `Active`, Date as today. Ask for Authors (GitHub handle).

**Context**: Draft from the forces discovered in Step 2. Must describe the problem space, constraints, and relevant quality attributes. Reject vague or generic descriptions; ask follow-up questions if needed. Write in short paragraphs, one force per paragraph.

**Decision**: Active voice, explicit rationale referencing quality attribute tradeoffs from Context. State what was chosen and why, not just what was chosen.

**Other Considerations**: Document each alternative evaluated. For each: what problem it solves, why it was not chosen or how it complements the decision, whether it may be revisited. If only one option was viable, say so and explain why. Write each alternative as its own paragraph with a bold lead.

**Consequences**: Ask the user about pros, cons, and any technical debt. If no tech debt, write "None". Every force from Context should appear here. Use bullets only for the pros/cons lists; write technical debt as prose.

**Enforcement / Guidance**: Concrete and actionable. Ask: "How will the team verify conformance?" Examples: linter rules, CI checks, code review criteria, naming conventions, automated tests. Bullets are appropriate here.

### Step 4: Validate and Save

Before saving, validate the completed ADR against the rejection criteria in `adr-pr-review.instructions.md`:
- All required sections present with substantive content
- No placeholder text remains
- Status is `Active`, `Proposed`, or `Archived`
- Filename matches `adr-{project}-{kebab-case-title}.md`
- Prose conforms to writing-voice: no em dashes, no filler, paragraphs are short and direct

Save to `docs/adr/` and confirm the file path to the user.

### Step 4b: Update the ADR Index

After saving, append a row to `docs/adr/adr-index.md` so the new ADR is discoverable without loading it. Read the index first, then add one row with: the ADR name as a relative markdown link, its Status, its Context (the subsystem or concern, matching the style of existing rows), and a one-line synopsis of what it governs or enforces. Keep the synopsis to a single sentence and apply writing-voice. Do not touch other rows. If the placeholder `_None yet._` row is present, replace it.

### Step 5: Revise an Existing ADR

Use this step when the user wants to change an ADR that is already saved.

Read the existing file from `docs/adr/adr-{project}-{kebab-case-title}.md` first. Work from its current contents, not from memory.

Apply the requested change. Keep every other section, the metadata, and the writing-voice conventions intact. If the change alters the decision itself rather than wording, consider whether Status should move to `Archived` and a new ADR should supersede it; raise this with the user rather than silently rewriting history.

Re-validate against the Step 4 rejection criteria. Confirm before overwriting. Save to the same path, unless the title changes, in which case derive a new filename and tell the user the old file is now orphaned.

If the change alters the ADR's Status, Context, or what it governs, or renames the file, update its row in `docs/adr/adr-index.md` to match in the same pass. A row must never drift from the file it points to.
