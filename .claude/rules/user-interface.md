---
paths: ["**/*.xaml", "**/*.tsx", "**/*.jsx", "**/*.vue", "**/*.html", "**/*.css", "**/*.razor"]
---

# User Interface Standards
Extends `code-standards.instructions.md` with UI-specific rules. Both files apply when working in UI layers.

## Architecture
- Presentation logic must not reference view implementation details directly.
- Business logic belongs in service layers, not the presentation layer.
- Use the framework's binding or reactivity system; avoid imperative UI updates for state-driven changes.
- Presentation-only logic (animations, focus management) may live in view code if scoped to a single component.

## Naming Conventions
- Name UI components to reflect their purpose and layer role.
- Follow the project's casing convention for UI element identifiers.

## Data Binding / State Management
- Prefer declarative binding over imperative property access.
- Use converters or computed properties for display transformations; do not embed formatting logic in the presentation layer.

## Commands / Event Handling
- User actions route through a defined command or event handling mechanism.
- Disable or hide controls when their associated action is invalid.

## Resource Management
- Shared styles, themes, and templates belong in dedicated resource files, not inline in views.
- Avoid duplicate resource definitions across the project.

## Performance
- Virtualize large collections to minimize rendering overhead.
- Avoid binding to properties that trigger expensive computation on every change; use throttling or batching.
