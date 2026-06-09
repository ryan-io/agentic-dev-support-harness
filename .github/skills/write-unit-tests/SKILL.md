---
name: write-unit-tests
description: >
  Write unit tests for code that already exists, one unit at a time, applying the project's
  testing standards. Use when the developer wants to "write tests", "add unit tests", "cover this
  with tests", "test this class", "test this method", or "add test coverage", or hands over a class
  and asks for tests. Produces NUnit 4 tests with Moq for C#, following testing.instructions.md and
  the stack-specific code standards. Enumerates behaviors and edge cases first, writes
  Arrange-Act-Assert, mocks only at owned boundaries, verifies outcomes, and runs the suite green.
  Also revises an existing test file in place. For test-first pairing on a new design, use
  implementation instead.
---

# Write Unit Tests

This skill turns a unit of code into a focused test suite. It is a procedure, not a standard. The standards live in `testing.instructions.md` (universal) and the stack-specific code standards file. Read those first and follow them; this skill applies them rather than restating them.

The stack default for this project is C# with NUnit 4 and Moq, per `csharp-code-standards.instructions.md`. The deeper rationale is in `.github/docs/testing-guide.md`.

## When to use

Invoke when the developer wants tests for code that already exists, or that is being written next to the tests. For test-first pairing that builds a new design service by service, use `implementation` instead. This skill produces the tests themselves.

## Input

Point at the unit under test: a class, a method, or a file. Read it and the collaborators it depends on. If the target is ambiguous or spans many types, ask the developer to name one unit. Per `agent-guardrails`, ask rather than guess.

## Workflow

Work one unit at a time. For each unit:

1. Understand the contract. Read the code under test and its public surface. Identify what it returns, what state it changes, what it throws, and which collaborators it calls. The contract is what you test, not the implementation.

2. Enumerate cases before writing any test. List the happy path, the boundaries (empty, null, zero, max, off-by-one), the error paths, and every branch in the code. One behavior per test. If the list is long, show it to the developer before writing.

3. Write each test as Arrange-Act-Assert. Small Arrange, a single Act, a focused Assert. Name it `Method_State_ExpectedBehavior` so it reads as a sentence. Use the simplest inputs that prove the behavior.

4. Mock only at owned boundaries. Substitute external dependencies (clock, network, filesystem, database, other services) through the abstraction the code already depends on. Do not mock the type under test, types you do not own, or private detail. If a test can only work by reaching private state, that is a design signal, not a mocking problem. Prefer a fake over a mock when the dependency has real behavior. Over-mocking is the most common failure mode for generated tests: it produces suites that pass while production breaks.

5. Verify outcomes, not interactions. Assert on the observable result first: the return value, the changed state, the thrown exception. Verify a collaborator call only when that call is the behavior under test (a command, such as "sends the email"). Do not assert every interaction or the order of calls.

6. Run the suite. It must be green and fast. A test that needs the real network, filesystem, or wall clock is not a unit test; isolate the dependency or move the test to the integration tier.

7. Cover the fix. When the unit under test is a bug fix, add a test that fails without the fix and passes with it.

## C#: NUnit 4 and Moq

NUnit 4 uses the constraint model. Assert with `Assert.That(actual, Is.EqualTo(expected))`, not the classic `Assert.AreEqual`. The classic asserts moved to `NUnit.Framework.Legacy.ClassicAssert` in NUnit 4; do not reach for them in new tests. Use `[Test]` for a case, `[TestCase(...)]` for parametrized inputs, `[TestCaseSource]` for complex data, and `[SetUp]` for shared arrange. Assert an expected exception with `Assert.That(() => sut.Do(), Throws.TypeOf<ArgumentException>())`.

Moq mocks default to Loose, which is the right default. Set up only what the test needs, return values through the abstraction, and verify the one or two calls that are the behavior. Avoid `MockBehavior.Strict` and a blanket `VerifyAll`: they couple the test to call order and incidental setup and make it brittle. Layout: a `{ProjectName}.Tests` project, one test class per type (`FooServiceTests`), factory methods for test data.

Moq's 4.20.0 SponsorLink component was removed in 4.20.2, and current 4.x is clean. If the developer raises supply-chain or build-dependency policy, note NSubstitute as the common MIT-licensed alternative and confirm before switching frameworks, per `pattern-fidelity`.

## Revising existing tests

When asked to change a test file that already exists, read it first. Match its established patterns: framework version, naming, fixture and `[SetUp]` style, and helper methods. Apply only the requested change, preserve every other test and the file's conventions, confirm before overwriting, and save to the same path unless the developer renames it.

## Done

Each behavior and edge case of the unit has a test, the names read as sentences, mocks sit only at owned boundaries, the assertions check outcomes, and the suite runs green. Summarize what was covered, and name any behavior you chose not to test and why.
