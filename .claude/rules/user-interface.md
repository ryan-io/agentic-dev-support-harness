---
paths: ["**"]
---


# User Interface Standards
<!-- CUSTOMIZE: Narrow applyTo to your UI file extensions (e.g., "**/*.xaml", "**/*.tsx", "**/*.vue"). Replace placeholder sections with your framework's conventions. -->
These standards extend `code-standards.instructions.md` with UI-specific rules. Both files apply when working in UI layers.

## Architecture
<!-- CUSTOMIZE: Define your UI architectural pattern (e.g., MVVM, MVC, MVP, component-based). -->
- Presentation logic must not reference view implementation details directly.
- Business logic belongs in dedicated service layers, not in the presentation layer.
- Use the framework's binding or reactivity system — avoid imperative UI updates for state-driven changes.
- Presentation-only logic (animations, focus management) may live in view code if scoped to a single component.

## Naming Conventions
<!-- CUSTOMIZE: Define naming rules for views, presenters/controllers/viewmodels, and UI element identifiers. -->
- Name UI components to reflect their purpose and layer role.
- Follow the project's established casing convention for UI element identifiers.

## Data Binding / State Management
<!-- CUSTOMIZE: Define your framework's preferred data flow (e.g., one-way binding, two-way binding, reactive stores). -->
- Prefer declarative binding over imperative property access.
- Use converters or computed properties for display transformations — do not embed formatting logic in the presentation layer.

## Commands / Event Handling
<!-- CUSTOMIZE: Define how user actions are wired to logic (e.g., ICommand, event handlers, action dispatchers). -->
- User actions must route through a defined command or event handling mechanism.
- Disable or hide controls when their associated action is invalid.

## Resource Management
<!-- CUSTOMIZE: Define where shared styles, themes, and assets live (e.g., resource dictionaries, CSS modules, theme files). -->
- Shared styles, themes, and templates belong in dedicated resource files, not inline in views.
- Avoid duplicate resource definitions across the project.

## Performance
<!-- CUSTOMIZE: Define UI-specific performance rules (e.g., virtualization, lazy loading, debouncing). -->
- Virtualize large collections to minimize rendering overhead.
- Avoid binding to properties that trigger expensive computation on every change — use throttling or batching where appropriate.
