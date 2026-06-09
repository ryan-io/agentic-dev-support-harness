---
paths: ["**/*.cs", "**/*.lua", "**/*.py", "**/*.ts", "**/*.js", "**/*.jsx", "**/*.tsx", "**/test/**", "**/tests/**", "**/spec/**"]
---


# Testing Standards

> **Full guidance:** `.github/docs/testing-guide.md`

These standards extend `code-standards.instructions.md` with testing-specific rules. Stack-specific testing conventions belong in the project's stack-specific code standards file.

## Test Tiers

Unit tests verify isolated functions and components. No network, filesystem, database, or external service dependencies.

Integration tests verify interactions across boundaries (API, database, service calls). Separate from unit tests by directory or naming convention.

E2E tests exercise critical user flows through the full stack. Cover paths where failure would block users.

## FIRST

Good unit tests are Fast (milliseconds, no I/O), Isolated (independent, run in any order, no shared mutable state), Repeatable (same result every run, no leaking clock or randomness), Self-validating (a pass/fail assertion, never manual inspection), and Timely (written with the code, not bolted on later).

## Test Structure

Every test follows Arrange-Act-Assert. Keep each section short: small Arrange, a single Act, a focused Assert. If Arrange dominates the test, extract a factory or builder.

## Behavior Over Implementation

Test the observable contract: return values, state changes, and thrown errors. Do not assert private state or incidental call sequences. A test that breaks on a safe refactor is testing the wrong thing.

## Naming

Test names follow the pattern `Method_State_ExpectedBehavior`. The method under test comes first, then the scenario or input state, then the expected outcome. Names read as a sentence: `Withdraw_InsufficientFunds_ThrowsException`, `Parse_EmptyString_ReturnsNull`.

## Mocking and Stubbing

Mock or stub external dependencies at public API boundaries. Prefer fakes over mocks when the dependency has complex behavior.

Know the test doubles: a dummy fills a parameter, a stub returns canned values, a fake has a working lightweight implementation, a spy records calls, a mock asserts the calls it expects. Verify state where you can; verify interactions only when the interaction is the behavior. Do not over-mock. Mocking the type under test, types you do not own, or internal detail produces brittle tests that pass while production breaks.

## Test Data

Use factory functions or builders to create test data. Each test must be independent: do not rely on execution order or shared mutable state.

## Coverage

All new logic must have corresponding tests. Bug fixes must include a regression test that fails without the fix.

## Stack-Specific Hook

Framework configuration, runner setup, coverage tooling, and E2E framework selection are stack-specific concerns. Define them in the project's `{language}-code-standards.instructions.md` file under a dedicated testing section. The `project-setup` skill will prompt for these during initial setup.
