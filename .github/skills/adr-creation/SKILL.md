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

Before starting, read the template to populate:
- `.github/docs/adr-template.md`

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

**Context**: Draft from the forces discovered in Step 2. Must describe the problem space, constraints, and relevant quality attributes. Reject vague or generic descriptions, ask follow-up questions if needed.

**Decision**: Must be active voice with explicit rationale referencing quality attribute tradeoffs identified in Context.

**Consequences**: Ask the user about pros, cons, and any technical debt introduced. If no tech debt, write "None". Every force from Context should be addressed here.

**Enforcement / Guidance**: Must be concrete and actionable. Ask: "How will the team verify conformance?" Examples: linter rules, CI checks, code review criteria, naming conventions, automated tests.

### Step 4: Validate and Save

Before saving, validate the completed ADR against the rejection criteria in `adr-pr-review.instructions.md`:
- All required sections present with substantive content
- No placeholder text remains
- Status is `Active`
- Filename matches `adr-{project}-{kebab-case-title}.md`

Save to `docs/adr/` and confirm the file path to the user.
