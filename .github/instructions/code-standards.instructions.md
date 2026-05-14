---
applyTo: "**"
---

# Code Standards (Universal)
These standards apply to all source files in the repository regardless of language or framework.
Stack-specific rules are defined in companion files (e.g., `{language}-code-standards.instructions.md`). A stack-specific file must accompany this file for every project — created during project setup via the `project-setup` skill.

## Null Safety
- Prefer explicit null handling over implicit assumptions.
- Use the language's null-safety features (nullable annotations, optional types, nil checks, etc.).
- Document any intentional use of force-unwrap or null-suppression operators with a comment explaining why.

## Async Discipline
- Never block on asynchronous code from synchronous contexts.
- Name asynchronous functions clearly to distinguish them from synchronous counterparts (follow language idiom).
<!-- CUSTOMIZE: Replace with your stack's async naming convention (e.g., suffix, keyword, decorator) -->
- Propagate cancellation or timeout mechanisms where supported by the language/runtime.
<!-- END CUSTOMIZE -->

## Decoupling & Dependency Management
- Depend on abstractions, not concrete implementations.
- Prefer constructor/initializer injection over service locators or global state.
- Register and resolve dependencies through a DI container or equivalent mechanism appropriate to the stack.

## Separation of Concerns
- UI code must not contain business logic.
- Business logic belongs in dedicated service/module layers, not in UI controllers, views, or event handlers.
- Follow the architectural pattern adopted by the project — do not mix patterns within the same module.

## Naming Conventions
- Follow the established idiom of the language (PascalCase, camelCase, snake_case, etc.).
- Names must be descriptive and unambiguous.
- Be consistent within a project — document any project-specific naming rules in the stack-specific standards file.

## Error Handling
- Never swallow errors or exceptions silently.
- Use structured logging appropriate to the stack — avoid raw print/console output in production code.
- Validate inputs at public API boundaries and fail early with clear error messages.

## Testing
- All new logic must have corresponding tests.
- Tests go in a dedicated test directory or project, not alongside production code (unless the language convention dictates otherwise).
- Test names must describe the scenario and expected outcome.
- Mock or stub external dependencies — tests must not rely on network, filesystem, or database unless explicitly integration tests.
