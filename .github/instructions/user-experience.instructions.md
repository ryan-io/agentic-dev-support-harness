---
applyTo: "**/*.xaml,**/*.tsx,**/*.jsx,**/*.vue,**/*.html,**/*.css,**/*.razor"
---

# User Experience Standards
UX behavior and interaction rules. Complements `user-interface.instructions.md` (implementation).

## Feedback and Responsiveness
- Every user action must produce visible feedback within a reasonable threshold.
- Long-running operations display progress or a loading indicator.
- Disable interactive elements during pending operations to prevent duplicate submissions.

## Error Presentation
- Display errors inline, near the element that triggered them.
- Error messages: plain language, suggest corrective action. Never expose stack traces or internal identifiers.

## Navigation and Layout
- Navigation must be predictable: the user always knows where they are and how to go back.
- Maintain consistent layout and component placement across views.

## Accessibility
- All interactive elements must be keyboard-accessible.
- Provide meaningful labels for screen readers on non-text elements.
- Maintain sufficient color contrast for text and interactive elements.

## Input Validation
- Validate input as early as practical; surface errors before submission.
- Preserve user input on validation failure: do not clear fields.
- Mark required fields visually before interaction.

## Defaults and State Preservation
- Provide sensible defaults for optional fields and settings.
- Preserve user selections and scroll position across navigation when appropriate.
