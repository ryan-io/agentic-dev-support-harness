# Testing Guide

Companion to `testing.instructions.md`. Read this before writing or reviewing tests.

## Test Tiers: Detailed Descriptions

Unit tests verify individual functions, utilities, and components in isolation. They must not depend on the network, filesystem, database, or external services. Use mocks, stubs, or fakes for external dependencies.

Integration tests verify interactions across boundaries: API endpoints, database operations, service-to-service calls. They run in a controlled environment and are clearly separated from unit tests by directory, naming convention, or test runner configuration.

End-to-end tests exercise critical user flows through the full stack. Framework choice is language- and project-specific; define it in the stack-specific code standards file. E2E tests cover the paths where a failure would block users, not every permutation.

## FIRST: What a Unit Test Owes You

A unit test should be Fast, Isolated, Repeatable, Self-validating, and Timely. Fast means milliseconds and no I/O, so the suite runs on every change. Isolated means tests do not depend on each other and pass in any order, with no shared mutable state. Repeatable means the same result every run; a test that reads the real clock, a random seed, or a live service is not repeatable. Self-validating means the test asserts pass or fail on its own, never by manual inspection of output. Timely means tests are written with the code, not bolted on weeks later when the design has hardened around untestable seams.

## Test Structure: Worked Example

The project uses NUnit 4. Assert through the constraint model with `Assert.That`. The classic asserts (`Assert.AreEqual` and friends) moved to `NUnit.Framework.Legacy.ClassicAssert` in NUnit 4; do not use them in new tests.

```csharp
[Test]
public void Rotate_NegativeDegrees_ClampsToZero()
{
    // arrange
    var joint = new ServoJoint(minAngle: 0.0, maxAngle: 180.0);

    // act
    joint.Rotate(-15.0);

    // assert
    Assert.That(joint.CurrentAngle, Is.EqualTo(0.0));
}
```

Parametrize repeated cases with `[TestCase(...)]`, and source complex data with `[TestCaseSource]`, rather than copying a test body. Assert an expected exception with `Assert.That(() => joint.Rotate(double.NaN), Throws.TypeOf<ArgumentException>())`.

## The Test Doubles

Test double is the umbrella term (Meszaros, popularized by Fowler). A dummy is passed only to fill a parameter and is never used. A stub returns canned answers to the calls the test makes. A fake has a real but lightweight implementation, such as an in-memory repository, unfit for production. A spy is a stub that also records how it was called. A mock is preprogrammed with the calls it expects and fails verification if it does not get them. The practical split: a stub answers queries (state verification), a mock verifies commands (behavior verification). Reach for the simplest double that proves the behavior.

## Mocking Rationale

Avoid mocking internal implementation details. If a test requires mocking private methods or internal state, the code under test likely needs refactoring. This is a design signal, not a testing problem.

Do not mock types you do not own unless wrapping them behind an abstraction first. The mock cannot track breaking changes in the real dependency, so mocked tests pass while production breaks.

Over-mocking is the dominant failure mode for generated tests. The trap is verifying interactions instead of outcomes: asserting that a method was called, in a certain order, with exact arguments, when the test should assert what the code produced. Verify a call only when the call is the behavior, such as "sends the confirmation email." Assert the observable result for everything else. Over-verified tests are brittle: they break on safe refactors and give false confidence.

With Moq, prefer the default Loose behavior. Set up only the calls the test needs and verify the one or two that matter. Avoid `MockBehavior.Strict` and a blanket `mock.VerifyAll()`; both couple the test to incidental setup and call order. Moq's 4.20.0 release briefly bundled the SponsorLink component, which read the local git email; it was removed in 4.20.2 and current 4.x is clean. If build-dependency policy rules Moq out, NSubstitute is the common MIT-licensed alternative; confirm before switching frameworks.

## Test Data Patterns

Avoid hardcoded literals scattered across tests. Shared fixtures are acceptable when they reduce duplication without obscuring test intent. Each test must be independent: do not rely on execution order or shared mutable state between tests.

## Coverage Philosophy

Coverage targets are a project-level decision, not a per-file mandate. High coverage numbers do not guarantee correctness. Focus on testing behavior and edge cases rather than chasing a percentage.
