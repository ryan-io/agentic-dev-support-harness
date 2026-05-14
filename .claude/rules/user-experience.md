---
paths: ["**"]
---


# User Experience Standards
<!-- CUSTOMIZE: Narrow applyTo if UX rules only apply to specific file types. Replace placeholder sections with your project's UX conventions. -->
These standards define UX expectations for the project. They complement `user-interface.instructions.md` (implementation) with user-facing behavior and interaction rules.

## Feedback and Responsiveness
<!-- CUSTOMIZE: Define your project's rules for loading states, progress indicators, and perceived performance. -->
- Every user action must produce visible feedback within a reasonable threshold.
- Long-running operations must display progress or a loading indicator.
- Disable interactive elements during pending operations to prevent duplicate submissions.

## Error Presentation
<!-- CUSTOMIZE: Define how errors, warnings, and validation messages are surfaced to the user. -->
- Display errors inline and contextually: near the element that triggered the error.
- Error messages must be written in plain language and suggest a corrective action when possible.
- Never expose raw exception text, stack traces, or internal identifiers to the user.

## Navigation and Layout
<!-- CUSTOMIZE: Define navigation patterns, breadcrumbs, routing rules, and layout constraints. -->
- Navigation must be predictable: the user should always know where they are and how to go back.
- Maintain consistent layout and component placement across views.

## Accessibility
<!-- CUSTOMIZE: Define your project's accessibility requirements (e.g., WCAG level, screen reader support, keyboard navigation). -->
- All interactive elements must be keyboard-accessible.
- Provide meaningful labels for screen readers on non-text elements.
- Maintain sufficient color contrast for text and interactive elements.

## Input Validation
<!-- CUSTOMIZE: Define when and how validation runs (e.g., on blur, on submit, real-time). -->
- Validate user input as early as practical and surface errors before submission.
- Preserve user input on validation failure: do not clear fields.
- Mark required fields visually before the user interacts with them.

## Defaults and State Preservation
<!-- CUSTOMIZE: Define rules for default values, saved preferences, and session recovery. -->
- Provide sensible defaults for optional fields and settings.
- Preserve user selections and scroll position across navigation when appropriate.
