# ADR-SCAFFOLD: Introduce the ah-ide Scaffolding CLI for Multi-Stack Solution Setup

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Active     |
| Date    | 2026-06-03 |
| Authors | @ryan-io   |

---

## Amendment 2026-06-08: Setup moves to Python; all shell and batch wrappers removed except the git hook

This amendment revises the repository-setup portion of the original Decision and supersedes the original Enforcement rule that `ah-ide.bat` and `ah-ide` must remain wrappers. The scaffold engine, CLI grammar, and template-as-data model below are unchanged. Amendments are recorded here rather than by editing the original text, per the ADR permanence policy.

**What changed and why.** Setup logic lived in `repository-setup.sh` and a `.bat` twin, roughly 240 lines each kept in parity, and registered the repo root on the user's PATH by editing `~/.bashrc`, `~/.zshrc`, and the Windows user-scope environment. Editing global shell config from a repository setup script is an out-of-repo change a careful developer audits before trusting, and it is disproportionate to its only benefit: typing `ah-ide` from outside the clone. More broadly, the template shipped a spread of `.sh` / `.bat` files (setup, sync, and the `ah-ide` wrappers) whose only job was to find Python and forward arguments. Shell and batch scripts are the thing that makes a developer hesitate to run a clone. They are also redundant: every one of them wraps a Python entry point that already works when called directly.

**Revised decision.**

- Setup logic moves into a stdlib-only Python engine, `repository-setup.py`, matching `scaffold.py` and `eject.py`. It is invoked directly: `python .github/scripts/setup/repository-setup.py`.
- All convenience shell and batch wrappers are removed: `setup.sh`/`.bat`, `repository-setup.sh`/`.bat`, `sync.sh`/`.bat` (root and `setup/`), and the `ah-ide`/`ah-ide.bat` scaffolder wrappers, plus the `.bootstrap/` shell scripts. The scaffolder is invoked as `python .github/scripts/scaffold.py`; sync as `python .github/scripts/sync-claude-rules.py`.
- The one exception is the git pre-commit hook, which git must execute as a shell script and which cannot be Python. It stays, and it remains the only shell script in the template.
- PATH registration is removed. Setup no longer edits `~/.bashrc`, `~/.zshrc`, or the Windows user environment. `repository-setup.py` keeps a `--remove-path` migration that strips PATH entries an earlier setup wrote, so a clone that ran the superseded version can clean up.
- Setup gains `--dry-run`, parity with eject, printing every action before it runs. Git-hook installation is unchanged in behavior: `core.hooksPath` plus the disclosed `.git/hooks` compatibility symlink.

**Consequences of the amendment.** The repository ships exactly one shell script, the git hook, and every other entry point is a `python ...` command in the repository's own automation language. The trust surface shrinks to near nothing: no out-of-repo writes, nothing to audit beyond short Python scripts. The cost is the loss of bare-name and double-click invocation: there is no `ah-ide` on PATH and no `setup.sh` to run, so docs name the full `python` command. Cross-impact: harness-eject Category A now targets only `repository-setup.py`, Category B drops the `ah-ide` wrappers, and the `validate-system.py` setup checks (file existence, engine integrity, the former `.sh`/`.bat` parity and Python-detection checks) change to match in the same pass.

**Enforcement of the amendment.** `repository-setup.py` is the only setup logic. No new `.sh` or `.bat` file is added to the template except a git hook under `.github/hooks/`; any other shell or batch script is a review rejection. No setup path writes outside the repository tree; a write to a shell rc file or system environment from setup is a review rejection. `validate-system.py` asserts the setup engine exists and carries every operation, with no shell/batch parity check to satisfy.

Implementation plan: `docs/process/2026-06-08-setup-python-engine-plan.md`.

---

## Context

The harness is distributed as a template repository clone. The agentic system files (`CLAUDE.md`, `.claude/`, `.github/instructions/`) must live in the same repository as the solution they support, because Claude Code and the Visual Studio 2026 extensions resolve them relative to the working directory. A fresh clone contains no application scaffold; every project hand-builds its solution layout and IDE assets, which is slow and drifts from project standards.

The scaffold targets two IDEs: VS Code with the official Claude Code extension, and Visual Studio 2026 with a third-party extension wrapping the Claude Code CLI. Extensions are installed per machine and out of scope. Both paths consume the same repo-level agent assets; only IDE assets (`.vscode/`) differ.

Two stacks are in scope now: C# (.NET 10, three layouts: class library, WPF with Microsoft DI, WPF with DI and EF Core, all `.slnx` only) and Lua (World of Warcraft addon: `.toc` manifest, Ace3 bootstrap, BigWigsMods packager metadata, luacheck). More stacks may follow. A Lua addon has no `dotnet` toolchain on the machine, so the scaffolding engine cannot assume any stack's toolchain is present.

Usability is command-line first: clone, run one command (`ah-ide`). Shell and batch scripts are wrappers, not the engine. The competing quality attributes are single-engine maintainability against per-stack flexibility: one generic engine must scaffold layouts as different as a `.slnx` solution and a WoW addon without encoding stack knowledge in the engine.

---

## Decision

We ship a Python scaffolding engine at `.github/scripts/scaffold.py`, invoked through thin `ah-ide.bat` (Windows) and `ah-ide` (Unix) wrappers at the repository root. Python is already the repository's automation language (sync, validation, learning pipeline), so this follows existing precedent and adds no new runtime.

The CLI grammar is stack-first, the prevailing convention (`dotnet new <template>`, `cargo new`): `ah-ide <stack> [--type <layout>] --name <Name> [--ide vscode|vs2026|both]`. `--ide` defaults to `both` and controls only IDE-asset emission.

Stacks are data, not code. Each directory under `templates/` is a template with a `manifest.json` declaring its stack, layout type, rename token, and IDE-asset mapping. The engine copies the tree, replaces the token in paths and text content, and excludes IDE assets per the `--ide` choice. Adding a stack is a new directory, never an engine change.

Repository setup registers the repo root on the user's PATH (Windows user-scope environment from the batch script, shell rc files from the bash script), so `ah-ide` runs from any directory. (Superseded by the Amendment 2026-06-08 above: PATH registration is removed.) The scaffold emits into the caller's current directory by default (`--out` overrides); templates always resolve relative to the engine's own location, not the caller's. The expected workflow remains scaffolding into a harness clone next to the agent assets, which are never re-emitted.

---

## Other Considerations

**dotnet new template pack.** Native conditional templating for the C# layouts, and the first pass of this work used it. Rejected as the engine once scope widened beyond .NET: it would force the .NET SDK onto machines scaffolding Lua addons, and its conditional syntax buys nothing for non-.NET trees. Could return as a published distribution channel for the C# templates specifically.

**Cookiecutter or Yeoman.** Mature general-purpose scaffolders solving exactly this problem. Rejected because both add a foreign dependency chain (Python packaging or Node) when a dependency-free stdlib script covers the requirement.

**Pure shell and batch generation.** No engine at all. Rejected because token replacement, manifest parsing, and collision handling would be implemented twice in two script dialects. The wrappers stay thin by policy.

**Per-stack repositories.** One template repo per stack. Rejected: the agent harness is the shared core, and forking it per stack duplicates everything the harness exists to centralize.

---

## Consequences

Pros:

- One command from a fresh clone covers every stack and IDE combination. (Per the Amendment 2026-06-08, invoked as `python .github/scripts/scaffold.py` rather than by bare name on PATH.)
- Stacks are data; adding one requires no engine change and no new toolchain.
- Python engine matches the repository's existing automation precedent.
- `.slnx`-only C# output needs no solution GUIDs, keeping templates trivially maintainable.

Cons:

- Templates have no compile-time validation; a broken template is found at scaffold or build time, so CI must build each variant.
- Token replacement is textual, not syntax-aware; template authors must keep the token (`ProjectName`) out of contexts where partial matches occur.
- WPF variants build only on Windows, constraining CI runners.
- The WoW `.toc` Interface version goes stale with each game patch; templates carry it as a marked update point.

Technical debt: the C# templates are not distributable outside a clone (no NuGet template pack). Acceptable while the clone is the only channel.

---

## Enforcement / Guidance

- CI job scaffolds every template in `templates/` for each `--ide` choice into a temp directory; C# variants run `dotnet build` on a Windows runner, Lua variants run `luacheck`.
- `validate-system.py` gains a check that every `templates/*/manifest.json` parses and declares `stack`, `token`, and `ide_assets`.
- Changes under `templates/` and to `scaffold.py` are reviewed against this ADR; engine changes that encode stack-specific logic are a rejection, as is re-emitting repo-level agent assets.
- `ah-ide.bat` and `ah-ide` must remain argument-forwarding wrappers; logic in wrappers is a review rejection. (Superseded by the Amendment 2026-06-08 above: the wrappers are removed and the scaffolder is invoked as `python .github/scripts/scaffold.py`.)

---

## References

- Microsoft, "Custom templates for dotnet new", learn.microsoft.com, accessed 2026-06-03.
- Microsoft, "Introducing support for SLNX in the .NET CLI", devblogs.microsoft.com, accessed 2026-06-03.
- WowAce, "Ace3 Getting Started", wowace.com, accessed 2026-06-03.
- BigWigsMods, "packager" (.pkgmeta reference), github.com/BigWigsMods/packager, accessed 2026-06-03.
