---
paths: ["**/*.cs"]
---


# C# Code Standards

Extends `code-standards.instructions.md`. Draws from [ktaranov/naming-convention](https://github.com/ktaranov/naming-convention) and the [.NET runtime coding style](https://github.com/dotnet/runtime/blob/main/docs/coding-guidelines/coding-style.md).

## Language Version

Target the latest stable C# version supported by the project SDK. Use file-scoped namespaces, global usings, and primary constructors where supported. No preview features without an ADR.

## Naming

| Identifier | Convention | Example |
|---|---|---|
| Class, struct, record | PascalCase | `ClientActivity` |
| Interface | `I` + PascalCase | `IGroupable` |
| Method | PascalCase | `CalculateStatistics` |
| Property | PascalCase | `DateOpened` |
| Public field | PascalCase | `Reserves` |
| Private field | `_camelCase` | `_registrationDate` |
| Parameter, local | camelCase | `itemCount` |
| Constant | PascalCase | `ShippingType` |
| Enum type | PascalCase, singular | `Color` |
| Enum flags | PascalCase, plural | `Dockings` |
| Type parameter | `T` + PascalCase | `TResult` |
| Namespace | `Company.Product.Module` | |

No Hungarian notation. No `SCREAMING_CAPS`. No underscores except the private field prefix. Abbreviations of 3+ chars use PascalCase (`XmlDocument`). Two-char abbreviations stay uppercase (`UI`, `IO`).

## Null Safety

Enable nullable reference types project-wide (`<Nullable>enable</Nullable>`). Treat nullable warnings as errors. Use the null-forgiving operator (`!`) only when the compiler cannot prove safety, with a comment explaining why. Prefer `is not null` / `is null` over `!=` / `==` for null checks.

## Async

Suffix async methods with `Async`. Return `Task` or `ValueTask`, never `async void` except event handlers. Pass `CancellationToken` through every async chain. Use `ConfigureAwait(false)` in library code.

## Dependency Injection

Register services in a composition root. Constructor injection only. Do not resolve from `IServiceProvider` inside business logic. Scoped services must not be injected into singletons.

## Error Handling

Throw specific exception types, not bare `Exception`. Custom exceptions use the `Exception` suffix (`BarcodeReadException`). Use exception filters (`when`) to avoid catching what you cannot handle. Use `ILogger<T>` for structured logging.

## Type Usage

Use C# aliases (`int`, `string`, `bool`) for declarations. Use framework names (`Int32.TryParse`, `String.Join`) for static member access. Use `var` for locals when the type is obvious from the right side; use explicit types for primitives.

## LINQ

Method syntax for simple queries, query syntax for multiple `from`, `let`, or `join` clauses. Avoid LINQ in hot paths where allocation matters. Materialize (`.ToList()`, `.ToArray()`) at the boundary, not inside loops.

## Collections

Use `IReadOnlyList<T>`, `IReadOnlyCollection<T>`, or `IEnumerable<T>` for return types when mutation is not intended. Concrete types internally. Prefer collection expressions (`[1, 2, 3]`) where supported.

## Enums

Singular names for standard enums, plural for `[Flags]`. Do not suffix with `Enum` or `Flags`. Do not specify underlying type or explicit values unless required (bit fields).

## Events

Event args suffix with `EventArgs`, delegate types with `EventHandler`. Handlers take `object sender` and typed `e`.

## Code Organization

One type per file, name matches type. Allman braces. Members top-down: static fields, instance fields, constructors, properties, public methods, private methods. Namespaces follow `Company.Product.Module`.

## Testing

NUnit as the test framework. Projects named `{ProjectName}.Tests`. Classes mirror the type under test (`FooServiceTests`). Methods follow `Method_State_ExpectedBehavior` per `testing.instructions.md`. Use Moq for mocking, factory methods for test data.
