# ADR-SCAFFOLD: Add a Test-Framework Dimension to ah-ide Scaffolding

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-08 |
| Authors | @ryan-io   |

---

## Context

The `ah-ide` scaffolder (ADR-SCAFFOLD: Introduce the ah-ide Scaffolding CLI) emits a test project with every C# layout, hardwired to NUnit. The package references and the sample test source carry NUnit directly: `NUnit` and `NUnit3TestAdapter` in the `.csproj`, `using NUnit.Framework`, `[TestFixture]`, `[Test]`, and `Assert.That` in the `.cs`. A developer who prefers xUnit or MSTest scaffolds the project, then rewrites the test project by hand before writing a first real test.

NUnit, xUnit, and MSTest are all first-class on .NET 10. The choice is a team preference, not a technical constraint, so the scaffolder should not impose one. The constraint that shapes the design is the existing engine principle: stacks are data, and the engine carries no stack-specific logic. A test-framework choice cuts across that. It is not a new stack and not a new layout. It is a variant within a layout, and the three frameworks differ in two files only: the test `.csproj` and the sample test `.cs`.

The competing forces are developer choice against engine simplicity. Encoding three frameworks as branches in `scaffold.py` would violate the engine principle the original ADR enforces. Duplicating each layout into three sibling templates (`csharp-classlib-nunit`, `-xunit`, `-mstest`) would triple the template count and the shared files within them.

---

## Decision

We add a test-framework dimension as manifest-declared data, selected at scaffold time with `--test-framework <NAME>`, and resolved through a generic overlay convention the engine applies uniformly. No framework names appear in engine code.

A template that ships selectable test frameworks declares them in its `manifest.json`:

```json
"test_frameworks": {
  "default": "NUnit",
  "options": ["NUnit", "xUnit", "MSTest"]
}
```

The framework-specific files live under a reserved `_testfw/<Framework>/` subtree inside the template, mirroring their final destination path. The engine excludes `_testfw/` from the normal copy, then overlays the selected framework's subtree as if its files sat at the template root, applying the same token replacement as every other file. `--test-framework` defaults to the manifest's `default`, so existing invocations are unchanged and still scaffold NUnit. The selected framework is recorded in the scaffold receipt so `undo` and audit see it.

This keeps the engine generic. The overlay mechanism is a per-template variant dimension, not a NUnit-or-xUnit conditional. A template without a `test_frameworks` block behaves exactly as before, and passing `--test-framework` to such a template is a usage error, not a silent no-op.

Package versions are pinned inside each overlay's `.csproj`, not exposed as a CLI argument. A framework pins several coordinated packages (NUnit pairs with NUnit3TestAdapter, xUnit with xunit.runner.visualstudio, MSTest with its adapter), so a single `--version` value cannot address them coherently. Pinning in one file per framework per layout keeps the bump a deliberate edit at a known location. Arbitrary version selection at scaffold time is a non-goal; the example `--test-framework NUnit@4.3.2` form is deliberately not supported, because the version belongs with the curated package set, not the command line.

---

## Other Considerations

**Three sibling templates per layout.** Copy each C# layout into one directory per framework. It needs no engine change and is pure data, consistent with the original ADR. Rejected because it multiplies nine template directories into the dozens and duplicates the shared `src/`, `.slnx`, and IDE assets across every copy, so a fix to shared content must be made three times. The overlay keeps shared files single-sourced and isolates the variance to the two files that actually differ.

**Framework branches in the engine.** A conditional in `scaffold.py` selecting package references and test source per framework. Rejected outright: it puts stack-and-tool knowledge into the engine, the exact failure mode the original ADR makes a review rejection.

**Post-scaffold rewrite by hand.** The status quo. The developer scaffolds NUnit and converts. Rejected as the problem being solved; it is routine, mechanical, and error-prone, and the scaffolder exists to remove exactly this kind of setup friction.

**Version override on the command line.** `--test-framework NUnit@4.3.2`. Solves the case where a team needs a specific framework version at scaffold time. Not chosen because a framework is a coordinated set of packages, not one, so a single version token is ambiguous, and the version is better pinned with its package set. May be revisited if a concrete need appears, as a manifest-declared version map rather than a free-form CLI value.

---

## Consequences

Pros:

- Developers choose their test framework at scaffold time; the default preserves existing behavior.
- The engine stays generic. Frameworks are data under `_testfw/`, added by authoring an overlay and a manifest line, never by editing the engine.
- Shared layout files remain single-sourced; only the two files that differ are duplicated, once per framework.

Cons:

- Each C# layout now carries three test-project variants, so a change to the shared test conventions (target framework, nullable settings) touches three `.csproj` files per layout.
- Pinned versions in overlays go stale and must be bumped per framework per layout. They are marked as the update point, the same pattern the original ADR uses for the WoW `.toc` Interface version.
- Textual token replacement still applies inside `_testfw/`; overlay authors keep the rename token out of partial-match contexts, unchanged from the original constraint.

Technical debt: the framework version pins are duplicated across layouts rather than centralized in a `Directory.Packages.props`. Acceptable while the layouts are few; central package management is a later option if the count grows.

---

## Enforcement / Guidance

- CI scaffolds every template for each declared test framework into a temp directory and builds the C# variants on a Windows runner, extending the existing per-template scaffold job to iterate `test_frameworks.options`.
- `validate-system.py` gains a check: when a manifest declares `test_frameworks`, it must include `default` and a non-empty `options` list, `default` must appear in `options`, and every option must have a non-empty `_testfw/<option>/` subtree.
- Engine code in `scaffold.py` must name no test framework. A framework string literal in the engine is a review rejection, consistent with the no-stack-logic rule of ADR-SCAFFOLD: Introduce the ah-ide Scaffolding CLI.
- New C# layouts that ship a test project declare the same three frameworks unless an ADR records a narrower set.

---

## References

- ADR-SCAFFOLD: Introduce the ah-ide Scaffolding CLI for Multi-Stack Solution Setup, `docs/adr/adr-scaffold-introduce-ah-ide-cli.md`, 2026-06-03.
- Microsoft, "Unit testing C# in .NET using dotnet test and xUnit / NUnit / MSTest", learn.microsoft.com, accessed 2026-06-08.
