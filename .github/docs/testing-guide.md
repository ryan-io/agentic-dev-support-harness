# Testing Guide

Companion to `testing.instructions.md`. Read this before writing or reviewing tests.

## Test Tiers: Detailed Descriptions

Unit tests verify individual functions, utilities, and components in isolation. They must not depend on the network, filesystem, database, or external services. Use mocks, stubs, or fakes for external dependencies.

Integration tests verify interactions across boundaries: API endpoints, database operations, service-to-service calls. They run in a controlled environment and are clearly separated from unit tests by directory, naming convention, or test runner configuration.

End-to-end tests exercise critical user flows through the full stack. Framework choice is language- and project-specific; define it in the stack-specific code standards file. E2E tests cover the paths where a failure would block users, not every permutation.

## Test Structure: Worked Example

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

## Mocking Rationale

Avoid mocking internal implementation details. If a test requires mocking private methods or internal state, the code under test likely needs refactoring. This is a design signal, not a testing problem.

Do not mock types you do not own unless wrapping them behind an abstraction first. The mock cannot track breaking changes in the real dependency, so mocked tests pass while production breaks.

## Test Data Patterns

Avoid hardcoded literals scattered across tests. Shared fixtures are acceptable when they reduce duplication without obscuring test intent. Each test must be independent: do not rely on execution order or shared mutable state between tests.

## Coverage Philosophy

Coverage targets are a project-level decision, not a per-file mandate. High coverage numbers do not guarantee correctness. Focus on testing behavior and edge cases rather than chasing a percentage.
