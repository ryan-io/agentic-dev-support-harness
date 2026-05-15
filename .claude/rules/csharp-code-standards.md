---
paths: ["**/*.cs"]
---


# C# Code Standards

These standards extend `code-standards.instructions.md` with C#-specific rules. Both files apply when writing or reviewing C# code.

## Language Version and Target

Target the latest stable C# language version supported by the project's SDK. Use file-scoped namespaces, global usings, and primary constructors where supported. Do not use preview features without an ADR.

## Null Safety

Enable nullable reference types project-wide (`<Nullable>enable</Nullable>`). Treat all nullable warnings as errors. Use the null-forgiving operator (`!`) only when the compiler cannot prove safety and add a comment explaining why.

Prefer pattern matching (`is not null`, `is null`) over equality operators (`!= null`, `== null`) for null checks.

## Naming

Follow the .NET naming guidelines. Public members use PascalCase. Parameters and local variables use camelCase. Private fields use `_camelCase` with an underscore prefix. Constants use PascalCase, not UPPER_SNAKE_CASE. Interface names start with `I`. Type parameter names start with `T`.

## Async

Suffix all async methods with `Async`. Return `Task` or `ValueTask`, never `async void` (except event handlers). Pass `CancellationToken` through every async call chain. Use `ConfigureAwait(false)` in library code, omit it in application code that needs the synchronization context.

## Dependency Injection

Register services in a composition root. Prefer constructor injection. Do not resolve services from `IServiceProvider` inside business logic (service locator pattern). Scoped services must not be injected into singletons.

## Error Handling

Throw specific exception types, not bare `Exception`. Use exception filters (`when`) to avoid catching exceptions you cannot handle. Let unrecoverable exceptions propagate. Use `ILogger<T>` for structured logging, not `Console.Write` or `Debug.Print`.

## LINQ

Prefer method syntax for simple queries and query syntax when the expression involves multiple `from`, `let`, or `join` clauses. Do not use LINQ in hot paths where allocation pressure matters; measure first. Materialize queries (`.ToList()`, `.ToArray()`) at the boundary, not inside a loop.

## Collections

Use `IReadOnlyList<T>`, `IReadOnlyCollection<T>`, or `IEnumerable<T>` for public return types when mutation is not intended. Use concrete types (`List<T>`, `Dictionary<TKey, TValue>`) for internal implementation. Prefer collection expressions (`[1, 2, 3]`) where the language version supports them.

## Testing

Use MSTest as the test framework. Test projects follow the naming convention `{ProjectName}.Tests`. Test classes mirror the class under test: `FooServiceTests` for `FooService`. Test methods follow `Method_State_ExpectedBehavior` as defined in `testing.instructions.md`.

Use Moq or NSubstitute for mocking. Prefer `Verify` calls over `Setup` with `Returns` when testing interactions. Use `AutoFixture` or factory methods for test data construction.

## Code Organization

One top-level type per file. File name matches the type name. Group members in this order: constants, fields, constructors, properties, public methods, private methods. Use `#region` sparingly and only for interface implementations that would otherwise clutter the file.
