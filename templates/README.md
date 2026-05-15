# Scaffolding Templates

Templates consumed by the ah-ide scaffolder, invoked as
`python .github/scripts/scaffold.py`. Decision record:
`docs/adr/adr-scaffold-introduce-ah-ide-cli.md`.

## Usage

Invoke the scaffolder through Python. It scaffolds into the current directory
by default (`--out` overrides):

```
python .github/scripts/scaffold.py csharp --type classlib --name MyLib
python .github/scripts/scaffold.py csharp --type classlib --name MyLib --test-framework xUnit
python .github/scripts/scaffold.py csharp --type wpf     --name MyApp --ide vscode
python .github/scripts/scaffold.py csharp --type wpf-ef  --name MyApp --ide both
python .github/scripts/scaffold.py lua    --name MyAddon
python .github/scripts/scaffold.py undo
```

Every scaffold writes a receipt (`.ah-ide-scaffold.json`) of emitted files
with content hashes. `python .github/scripts/scaffold.py undo` removes the most
recent scaffold using that receipt: it deletes only files the scaffold emitted, refuses if any were
modified since (override with `--force`), prunes emptied directories, and
pops one scaffold per run (LIFO). Use it when you picked the wrong project
type and want a clean slate before re-running.

`--test-framework` (NUnit | xUnit | MSTest, default NUnit) selects the test
project for C# templates. Each framework is a data overlay under the
template's `_testfw/<Framework>/` subtree; the engine excludes `_testfw/` from
the normal copy and overlays only the selected framework at the test project
path. Versions are pinned in each overlay's `.csproj`, the single place to
bump them. Decision record:
`docs/adr/adr-scaffold-add-test-framework-dimension.md`.

`--ide` (vscode | vs2026 | both, default both) controls only IDE-asset
emission (`.vscode/`). The scaffold lands in the current directory (or
`--out`); the expected workflow targets a harness clone so the solution sits
next to the agent assets (`CLAUDE.md`, `.claude/`), which are never
re-emitted. Setup makes no changes outside the repository. A clone that ran an
older setup, which put the repo root on PATH, can clean it up with
`python .github/scripts/setup/repository-setup.py --remove-path`.

## Templates

| Directory          | Stack  | Type     | Contents                                            |
|--------------------|--------|----------|-----------------------------------------------------|
| `csharp-classlib`  | csharp | classlib | Class library + tests (NUnit/xUnit/MSTest), `.slnx` |
| `csharp-wpf-di`    | csharp | wpf      | WPF + Microsoft DI host, Core layer, tests (NUnit/xUnit/MSTest), `.slnx` |
| `csharp-wpf-di-ef` | csharp | wpf-ef   | WPF + DI host, Core and EF Core (SQLite) Data layers, tests (NUnit/xUnit/MSTest), `.slnx` |
| `lua-wow-addon`    | lua    | (none)   | WoW addon: `.toc`, Ace3 embeds, `.pkgmeta`, luacheck |

## Related

- [Scripts](../.github/scripts/README.md): `scaffold.py`, the engine behind `ah-ide`.
- [Scaffolding ADR](../docs/adr/adr-scaffold-introduce-ah-ide-cli.md): why the CLI is built this way.
- [Repo map](../README.md): the high-level overview of every system.
