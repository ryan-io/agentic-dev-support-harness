---
paths: ["**"]
---

# Code Standards (Universal)
Apply to all source files regardless of language. Stack-specific rules live in `{language}-code-standards.instructions.md`. A stack file may supersede specific rules within its glob; supersessions are stated explicitly in that file (see `unity-code-standards` for `Assets/**`).

## Null Safety
- Prefer explicit null handling over implicit assumptions.
- Use the language's null-safety features (nullable annotations, optional types, nil checks).
- Document intentional force-unwrap or null-suppression with a comment explaining why.

## Async Discipline
- Never block on async code from synchronous contexts.
- Name async functions distinctly from sync counterparts (follow language idiom).
- Propagate cancellation or timeout mechanisms where the runtime supports them.

## Decoupling & Dependency Management
- Depend on abstractions, not concrete implementations.
- Prefer constructor/initializer injection over service locators or global state.
- Resolve dependencies through a DI container or equivalent.

## Separation of Concerns
- UI code must not contain business logic. Business logic belongs in service/module layers.
- Follow the project's architectural pattern; do not mix patterns within a module.

## Naming Conventions
- Follow the language idiom (PascalCase, camelCase, snake_case, etc.).
- Names must be descriptive and unambiguous.
- Document project-specific naming rules in the stack-specific standards file.

## Error Handling
- Never swallow errors silently.
- Use structured logging; avoid raw print/console output in production code.
- Validate inputs at public API boundaries and fail early with clear messages.

## Testing
- All new logic must have corresponding tests.
- Tests go in a dedicated test directory, not alongside production code (unless language convention dictates otherwise).
- Test names describe the scenario and expected outcome.
- Mock external dependencies; tests must not rely on network, filesystem, or database unless explicitly integration tests.
