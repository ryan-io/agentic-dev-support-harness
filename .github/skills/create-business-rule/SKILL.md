---
name: create-business-rule
description: >
  Interactively create a Business Rule document. Walks through each section to capture
  the rule's intent, conditions, and exceptions, then saves to
  docs/business-rules/. Use this skill whenever the user wants to create a business rule,
  document a domain constraint, capture a business requirement, or mentions "new business rule".
---

# Business Rule Creation Skill

Create a complete business rule document by walking the user through each section interactively.

## Prerequisites

Before starting, read the template to populate:
- `.github/docs/br-template.md`

Note: validation rules (`br-review`) auto-load when working in `docs/business-rules/`.

## File Conventions

- Filename must be lowercase: `br-{project}-{kebab-case-title}.md`
- Heading inside the file uses uppercase: `# BR-PROJECT: [Short Title]`
- Save to `docs/business-rules/`

## Workflow

### Step 1: Identify the Rule

Ask the user:
- What is the business rule? (short title, imperative phrase)
- What is the project prefix? (e.g., `SOC`, `GRID`, `APP`)
- What domain or feature area does this rule belong to?

Use these to derive the filename: `br-{project}-{kebab-case-title}.md`

### Step 2: Discovery

Walk the user through these questions to surface the rule's intent:

1. **What business outcome does this rule protect?**: Revenue, compliance, data integrity, user safety, etc.
2. **What triggers this rule?**: A user action, a system event, a time condition, a data state.
3. **What happens if this rule is violated?**: Identify the business impact of non-compliance.

### Step 3: Walk Through Sections

Present each section one at a time. After the user provides input, draft that section and confirm before moving on.

**Metadata**: Auto-fill Date as today. Ask for Authors, Status (`Active` or `Archived`, default `Active`), Domain, and Related ADRs (default "None").

**Description**: Plain language statement of the rule. Must be specific and unambiguous. One rule per document.

**Conditions**: When does this rule apply? Define the triggering context, inputs, and any preconditions.

**Expected Behavior**: What must happen when the rule is triggered? Define the outcome precisely.

**Exceptions**: Are there cases where this rule does not apply? If none, write "None".

### Step 4: Validate and Save

Before saving, validate:
- All required sections present with substantive content
- No placeholder text remains
- Filename is lowercase and matches `br-{project}-{kebab-case-title}.md`

Save to `docs/business-rules/` and confirm the file path to the user.

### Step 4b: Update the Business Rule Index

After saving, append a row to `docs/business-rules/br-index.md` so the new rule is discoverable without loading it. Read the index first, then add one row with: the rule name as a relative markdown link, its Status, its Domain, its Related ADRs (copy both from the rule's Metadata), and a one-line synopsis of what it governs. Keep the synopsis to a single sentence and apply writing-voice. Do not touch other rows. Replace the placeholder `_None yet._` row when adding the first rule.

### Step 5: Revise an Existing Business Rule

Use this step when the user wants to change a business rule that is already saved.

Read the existing file from `docs/business-rules/br-{project}-{kebab-case-title}.md` first. Work from its current contents, not from memory.

Apply the requested change. Keep every other section and the metadata intact. One rule per document still holds: if the change introduces a second rule, create a separate file instead.

Re-validate against the Step 4 criteria. Confirm before overwriting. Save to the same path, unless the title changes, in which case derive a new lowercase filename and tell the user the old file is now orphaned.

If the change alters the rule's Status, Domain, Related ADRs, or what it governs, or renames the file, update its row in `docs/business-rules/br-index.md` to match in the same pass. A row must never drift from the file it points to.
