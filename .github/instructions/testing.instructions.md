---
applyTo: "**"
---

# Testing Standards

These standards extend `code-standards.instructions.md` with testing-specific rules. Both files apply when writing or reviewing tests. This file defines universal testing principles. Stack-specific testing conventions (framework, runner, directory layout, naming patterns) belong in the project's stack-specific code standards file and should cross-reference this file.

## Unit vs Integration

Unit tests verify a single unit of logic in isolation. They must not depend on the network, filesystem, database, or external services. Use mocks, stubs, or fakes for external dependencies.

Integration tests verify that units work together or that the system interacts correctly with real external dependencies. They run in a controlled environment and are clearly separated from unit tests by directory, naming convention, or test runner configuration.

## Mocking and Stubbing

Mock or stub external dependencies at public API boundaries. Prefer fakes (lightweight implementations) over mocks when the dependency has complex behavior. Do not mock types you do not own unless wrapping them behind an abstraction first.

Avoid mocking internal implementation details. If a test requires mocking private methods or internal state, the code under test likely needs refactoring.

## Test Data

Use factory functions or builders to create test data. Avoid hardcoded literals scattered across tests. Shared fixtures are acceptable when they reduce duplication without obscuring test intent. Each test must be independent: do not rely on execution order or shared mutable state between tests.

## Coverage

All new logic must have corresponding tests. Bug fixes must include a regression test that fails without the fix. Coverage targets are a project-level decision, not a per-file mandate.

## Stack-Specific Hook

Test placement, naming patterns, framework configuration, runner setup, and coverage tooling are stack-specific concerns. Define them in the project's `{language}-code-standards.instructions.md` file under a dedicated testing section. The `project-setup` skill will prompt for these during initial setup.
