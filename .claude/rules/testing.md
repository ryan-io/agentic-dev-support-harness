---
paths: ["**"]
---


# Testing Standards

These standards extend `code-standards.instructions.md` with testing-specific rules. Both files apply when writing or reviewing tests. This file defines universal testing principles. Stack-specific testing conventions (framework, runner, directory layout) belong in the project's stack-specific code standards file and should cross-reference this file.

## Test Tiers

Unit tests verify individual functions, utilities, and components in isolation. They must not depend on the network, filesystem, database, or external services. Use mocks, stubs, or fakes for external dependencies.

Integration tests verify interactions across boundaries: API endpoints, database operations, service-to-service calls. They run in a controlled environment and are clearly separated from unit tests by directory, naming convention, or test runner configuration.

End-to-end tests exercise critical user flows through the full stack. Framework choice is language- and project-specific; define it in the stack-specific code standards file. E2E tests cover the paths where a failure would block users, not every permutation.

## Test Structure

Every test follows Arrange-Act-Assert. Arrange sets up preconditions and inputs. Act executes the behavior under test. Assert verifies the outcome. Keep each section short. If Arrange dominates the test, extract a factory or builder.

```csharp
[TestMethod]
public void Rotate_NegativeDegrees_ClampsToZero()
{
    // arrange
    var joint = new ServoJoint(minAngle: 0.0, maxAngle: 180.0);

    // act
    joint.Rotate(-15.0);

    // assert
    Assert.AreEqual(0.0, joint.CurrentAngle);
}
```

## Naming

Test names follow the pattern `Method_State_ExpectedBehavior`. The method under test comes first, then the scenario or input state, then the expected outcome. Names read as a sentence: `Withdraw_InsufficientFunds_ThrowsException`, `Parse_EmptyString_ReturnsNull`, `Login_ValidCredentials_RedirectsToDashboard`.

## Mocking and Stubbing

Mock or stub external dependencies at public API boundaries. Prefer fakes (lightweight implementations) over mocks when the dependency has complex behavior. Do not mock types you do not own unless wrapping them behind an abstraction first.

Avoid mocking internal implementation details. If a test requires mocking private methods or internal state, the code under test likely needs refactoring.

## Test Data

Use factory functions or builders to create test data. Avoid hardcoded literals scattered across tests. Shared fixtures are acceptable when they reduce duplication without obscuring test intent. Each test must be independent: do not rely on execution order or shared mutable state between tests.

## Coverage

All new logic must have corresponding tests. Bug fixes must include a regression test that fails without the fix. Coverage targets are a project-level decision, not a per-file mandate.

## Stack-Specific Hook

Framework configuration, runner setup, coverage tooling, and E2E framework selection are stack-specific concerns. Define them in the project's `{language}-code-standards.instructions.md` file under a dedicated testing section. The `project-setup` skill will prompt for these during initial setup.
