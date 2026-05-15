#!/usr/bin/env python3
"""ah-ide: scaffold a base solution for a stack into this repository clone.

Stacks are data: each directory under templates/ carries a manifest.json
declaring its stack, layout type, rename token, and IDE-asset mapping.
The engine copies the tree, replaces the token in paths and text content,
and includes IDE assets per the --ide choice. Adding a stack is a new
template directory, never an engine change.

Every scaffold writes a receipt (.ah-ide-scaffold.json) of emitted files
with content hashes. 'ah-ide undo' removes the most recent scaffold,
refusing to delete files modified since emission unless --force.

No shell or batch wrapper ships; invoke the engine through Python (ADR-SCAFFOLD
Amendment 2026-06-08).

Decision record: docs/adr/adr-scaffold-introduce-ah-ide-cli.md

Usage:
    python .github/scripts/scaffold.py csharp --type wpf-ef --name MyApp --ide both
    python .github/scripts/scaffold.py csharp --type classlib --name MyLib --test-framework xUnit
    python .github/scripts/scaffold.py lua --name MyAddon
    python .github/scripts/scaffold.py undo [--out DIR] [--force]
    python .github/scripts/scaffold.py help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "templates"
MANIFEST_NAME = "manifest.json"
RECEIPT_NAME = ".ah-ide-scaffold.json"
# How the engine is invoked, shown in help and argparse usage. No shell/batch
# wrapper ships (ADR-SCAFFOLD Amendment 2026-06-08); Python is the entry point.
INVOKE = "python .github/scripts/scaffold.py"
IDE_CHOICES = ("vscode", "vs2026", "both")
# Reserved template subtree holding test-framework overlays. The engine
# excludes it from the normal copy and overlays the selected framework's
# subtree (_testfw/<Framework>/) at the template root. See
# docs/adr/adr-scaffold-add-test-framework-dimension.md.
TESTFW_DIR = "_testfw"
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def load_templates():
    """Map (stack, type) -> template directory, discovered from manifests."""
    templates = {}
    if not TEMPLATES_DIR.is_dir():
        return templates
    for directory in sorted(TEMPLATES_DIR.iterdir()):
        manifest_path = directory / MANIFEST_NAME
        if not manifest_path.is_file():
            continue
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        templates[(manifest["stack"], manifest.get("type"))] = directory
    return templates


def excluded_ide_roots(manifest, ide):
    """Top-level template paths to skip for the chosen IDE."""
    excluded = set()
    for target, roots in manifest.get("ide_assets", {}).items():
        if ide != "both" and ide != target:
            excluded.update(roots)
    return excluded


def resolve_test_framework(manifest, requested):
    """Resolve the test framework to scaffold, or return an error string.

    Returns (selected, None) on success or (None, message) on a usage error.
    A template without a test_frameworks block accepts no --test-framework;
    one that declares it falls back to its declared default when unspecified.
    """
    cfg = manifest.get("test_frameworks")
    if not cfg:
        if requested is not None:
            return None, ("this template has no selectable test frameworks; "
                          "--test-framework is not valid here")
        return None, None
    options = cfg.get("options", [])
    if requested is None:
        return cfg.get("default"), None
    if requested not in options:
        return None, (f"unknown --test-framework '{requested}'. "
                      f"Available: {', '.join(options)}")
    return requested, None


def is_text_file(path):
    try:
        path.read_bytes().decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_receipt(out_dir):
    receipt_path = out_dir / RECEIPT_NAME
    if not receipt_path.is_file():
        return []
    with open(receipt_path, encoding="utf-8") as fh:
        return json.load(fh)


def write_receipt(out_dir, runs):
    receipt_path = out_dir / RECEIPT_NAME
    if runs:
        # newline="\n" keeps output byte-identical across OSes; the default
        # translates to os.linesep, emitting CRLF on Windows against the
        # repo's eol=lf policy (.gitattributes).
        receipt_path.write_text(
            json.dumps(runs, indent=2) + "\n", encoding="utf-8",
            newline="\n")
    elif receipt_path.exists():
        receipt_path.unlink()


def scaffold(template_dir, name, ide, out_dir, force, test_framework=None):
    with open(template_dir / MANIFEST_NAME, encoding="utf-8") as fh:
        manifest = json.load(fh)
    token = manifest["token"]
    excluded = excluded_ide_roots(manifest, ide)

    sources = []
    for src in sorted(template_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(template_dir)
        if rel.name == MANIFEST_NAME:
            continue
        # The test-framework overlay subtree is never copied wholesale; the
        # selected framework's files are overlaid separately below.
        if rel.parts and rel.parts[0] == TESTFW_DIR:
            continue
        if rel.parts and rel.parts[0] in excluded:
            continue
        sources.append((src, Path(str(rel).replace(token, name))))

    # Overlay the selected framework's files as if they sat at the template
    # root, stripping the _testfw/<Framework>/ prefix. Same token replacement
    # as every other file.
    if test_framework:
        overlay_root = template_dir / TESTFW_DIR / test_framework
        if not overlay_root.is_dir():
            print(f"error: template '{template_dir.name}' declares test "
                  f"framework '{test_framework}' but has no "
                  f"{TESTFW_DIR}/{test_framework}/ overlay", file=sys.stderr)
            return 1
        for src in sorted(overlay_root.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(overlay_root)
            sources.append((src, Path(str(rel).replace(token, name))))

    if not sources:
        print(f"error: template '{template_dir.name}' has no files",
              file=sys.stderr)
        return 1

    collisions = [dest for _, dest in sources if (out_dir / dest).exists()]
    if collisions and not force:
        print("error: refusing to overwrite existing files (use --force):",
              file=sys.stderr)
        for dest in collisions:
            print(f"  {dest}", file=sys.stderr)
        return 1

    emitted = []
    for src, dest in sources:
        target = out_dir / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        if is_text_file(src):
            # newline="\n" matches the repo's eol=lf policy; the default
            # would emit CRLF on Windows, making scaffolds differ by OS.
            target.write_text(
                src.read_text(encoding="utf-8").replace(token, name),
                encoding="utf-8", newline="\n")
        else:
            target.write_bytes(src.read_bytes())
        emitted.append({"path": dest.as_posix(), "sha256": sha256_of(target)})
        print(f"  {dest}")

    runs = read_receipt(out_dir)
    run = {
        "template": template_dir.name,
        "name": name,
        "ide": ide,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": emitted,
    }
    if test_framework:
        run["test_framework"] = test_framework
    runs.append(run)
    write_receipt(out_dir, runs)

    fw_note = f", tests: {test_framework}" if test_framework else ""
    print(f"\nScaffolded '{template_dir.name}' as '{name}' "
          f"(IDE: {ide}{fw_note}) into {out_dir}")
    suffix = f" --out {out_dir}" if out_dir != Path.cwd() else ""
    print(f"  undo with: {INVOKE} undo{suffix}")
    for note in manifest.get("post_scaffold_notes", []):
        print(f"  next: {note.replace('{name}', name)}")
    return 0


def predict_empty_dirs(out_dir, file_paths):
    """Predict which directories will become empty after removing file_paths.

    Walks up from each file's parent to out_dir, collecting directories
    whose only contents are files being removed or subdirs also being removed.
    """
    # Build a set of all files that will be gone.
    removing = {out_dir / p for p in file_paths}

    # Gather candidate directories (parents of removed files, walked upward).
    candidates = set()
    for p in removing:
        current = p.parent
        while current != out_dir:
            candidates.add(current)
            current = current.parent

    # Check deepest first: a dir is empty-after-removal if every child is
    # either a file being removed or a dir that is itself empty-after-removal.
    will_remove = set()
    for directory in sorted(candidates, key=lambda d: len(d.parts),
                            reverse=True):
        if not directory.is_dir():
            continue
        all_gone = True
        for child in directory.iterdir():
            if child in removing or child in will_remove:
                continue
            all_gone = False
            break
        if all_gone:
            will_remove.add(directory)

    return will_remove


def _within_out_dir(out_dir, rel_path):
    """Resolve a receipt-relative path under out_dir.

    Returns the resolved Path if it stays inside out_dir, otherwise None.
    Absolute paths and any '..' traversal are rejected; resolve() collapses
    symlinks too, so a path that escapes through a symlink is caught. The
    receipt is local, editable data, so undo must not trust it to delete
    outside the scaffold output directory.
    """
    if Path(rel_path).is_absolute():
        return None
    root = out_dir.resolve()
    target = (out_dir / rel_path).resolve()
    if target == root or root in target.parents:
        return target
    return None


def undo(out_dir, force, yes):
    runs = read_receipt(out_dir)
    if not runs:
        print(f"error: no scaffold receipt found in {out_dir}",
              file=sys.stderr)
        return 1

    run = runs[-1]

    # Refuse the whole undo if any recorded path escapes out_dir, before
    # touching the filesystem. A tampered receipt must not turn undo into
    # an arbitrary-delete primitive.
    escaping = [
        entry["path"]
        for entry in run["files"]
        if _within_out_dir(out_dir, entry["path"]) is None
    ]
    if escaping:
        print("error: receipt contains paths outside the output directory; "
              "refusing to undo:", file=sys.stderr)
        for rel in escaping:
            print(f"  {rel}", file=sys.stderr)
        return 1

    # Paths also recorded by earlier scaffolds in this directory (shared
    # files such as .vscode/ assets). Undoing this run must leave them in
    # place; the retaining run still owns them.
    retained = {
        entry["path"]
        for earlier in runs[:-1]
        for entry in earlier["files"]
    }

    modified = []
    missing = []
    present = []
    shared = []
    for entry in run["files"]:
        if entry["path"] in retained:
            shared.append(entry["path"])
            continue
        path = out_dir / entry["path"]
        if not path.is_file():
            missing.append(entry["path"])
        elif sha256_of(path) != entry["sha256"]:
            modified.append(entry["path"])
        else:
            present.append(entry["path"])

    if modified and not force:
        print("error: files modified since scaffolding; refusing to delete "
              "(use --force):", file=sys.stderr)
        for path in modified:
            print(f"  {path}", file=sys.stderr)
        return 1

    # Combine files that will be removed (present + modified when --force).
    to_remove = present + (modified if force else [])

    # Predict directories that will become empty after file removal.
    empty_dirs = predict_empty_dirs(out_dir, to_remove)
    dir_list = sorted(
        (str(d.relative_to(out_dir)) for d in empty_dirs), reverse=True)

    # Show preview and prompt for confirmation.
    print(f"Undo scaffold '{run['template']}' (name: {run['name']})")
    print(f"  scaffolded: {run.get('timestamp', 'unknown')}")
    print()
    print(f"Files to remove ({len(to_remove)}):")
    for p in sorted(to_remove):
        label = " (modified)" if p in modified else ""
        print(f"  {p}{label}")
    if missing:
        print(f"\nAlready missing ({len(missing)}):")
        for p in sorted(missing):
            print(f"  {p}")
    if shared:
        print(f"\nKept, shared with an earlier scaffold ({len(shared)}):")
        for p in sorted(shared):
            print(f"  {p}")
    if dir_list:
        print(f"\nDirectories to remove ({len(dir_list)}):")
        for d in sorted(dir_list):
            print(f"  {d}/")

    if not to_remove and not missing and not shared:
        print("\nNothing to undo.")
        return 0

    if not yes:
        print()
        try:
            answer = input("Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 1
        if answer not in ("y", "yes"):
            print("Aborted.")
            return 0

    # Remove files, skipping any path an earlier scaffold still owns.
    removed_dirs = set()
    for entry in run["files"]:
        if entry["path"] in retained:
            continue
        path = out_dir / entry["path"]
        if path.is_file():
            path.unlink()
            removed_dirs.add(path.parent)

    # Prune directories the scaffold created, deepest first, only if empty.
    for directory in sorted(removed_dirs, key=lambda p: len(p.parts),
                            reverse=True):
        current = directory
        while (current != out_dir and current.is_dir()
               and not any(current.iterdir())):
            current.rmdir()
            current = current.parent

    write_receipt(out_dir, runs[:-1])

    summary = f"Undid scaffold '{run['template']}' (name: {run['name']})"
    if missing:
        summary += f"; {len(missing)} file(s) were already gone"
    print(f"\n{summary}.")
    if runs[:-1]:
        print(f"  {len(runs) - 1} earlier scaffold(s) remain; "
              "run undo again to remove the next most recent.")
    return 0


def print_help(templates):
    """Overview help built from template manifests."""
    lines = [
        "ah-ide - scaffold a base solution into this repository clone",
        "",
        "USAGE",
        f"  {INVOKE} <stack> [--type TYPE] --name NAME",
        f"      [--ide vscode|vs2026|both] [--test-framework NAME] [--out DIR] [--force]",
        f"  {INVOKE} undo [--out DIR] [--force]",
        f"  {INVOKE} help",
        "",
        "COMMANDS",
    ]

    example_name = {"csharp": "MyApp", "lua": "MyAddon"}
    ordered = sorted(templates.items(),
                     key=lambda kv: (kv[0][0], kv[0][1] or ""))
    for (stack, layout), directory in ordered:
        with open(directory / MANIFEST_NAME, encoding="utf-8") as fh:
            manifest = json.load(fh)
        summary = (manifest.get("summary")
                   or manifest.get("description", "").split(". ")[0])
        cmd = stack + (f" --type {layout}" if layout else "")
        name = example_name.get(stack, "MyProject")
        lines += [
            f"  {cmd}",
            f"      {summary}",
            f"      example: {INVOKE} {cmd} --name {name}",
        ]
        tf_cfg = manifest.get("test_frameworks")
        if tf_cfg:
            opts = ", ".join(tf_cfg.get("options", []))
            lines.append(
                f"      test frameworks: {opts} "
                f"(default {tf_cfg.get('default')})")
        lines.append("")

    lines += [
        "  undo",
        "      Preview and remove the most recent scaffold using its",
        "      receipt (.ah-ide-scaffold.json). Shows files and directories",
        "      that will be deleted, then prompts for confirmation. Refuses",
        "      to delete files modified since scaffolding; --force overrides.",
        "      Pops one scaffold per run (most recent first).",
        f"      example: {INVOKE} undo",
        f"      example: {INVOKE} undo --yes   (skip confirmation)",
        "",
        "OPTIONS",
        "  --type TYPE                layout within the stack",
        "  --name NAME                project name (letters, digits, underscore)",
        "  --ide vscode|vs2026|both   IDE assets to emit (default: both)",
        "  --test-framework NAME      test framework where the template offers",
        "                             a choice (default: template's default)",
        "  --out DIR                  output directory (default: current dir)",
        "  --force                    overwrite (scaffold) or delete modified",
        "                             files (undo)",
        "  --yes, -y                  skip confirmation prompt (undo only)",
        "",
        f"Details per command: {INVOKE} <stack> --help, {INVOKE} undo --help",
    ]
    print("\n".join(lines))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "-h", "--help"):
        print_help(load_templates())
        return 0

    if sys.argv[1] == "undo":
        parser = argparse.ArgumentParser(
            prog=f"{INVOKE} undo",
            description="Remove the most recent scaffold using its receipt.")
        parser.add_argument("--out", default=".",
                            help="directory that was scaffolded into "
                                 "(default: current directory)")
        parser.add_argument("--force", action="store_true",
                            help="delete even files modified since scaffolding")
        parser.add_argument("--yes", "-y", action="store_true",
                            help="skip confirmation prompt")
        args = parser.parse_args(sys.argv[2:])
        return undo(Path(args.out).resolve(), args.force, args.yes)

    templates = load_templates()
    stacks = sorted({stack for stack, _ in templates})

    parser = argparse.ArgumentParser(
        prog=INVOKE,
        description="Scaffold a base solution into this repository clone.",
        epilog=f"Use '{INVOKE} undo' to remove the most recent scaffold, "
               f"'{INVOKE} help' for a command overview.")
    parser.add_argument("stack", choices=stacks or None,
                        help="stack to scaffold "
                             f"({', '.join(stacks) or 'none found'})")
    parser.add_argument("--type", dest="layout", default=None,
                        help="layout within the stack "
                             "(csharp: classlib, wpf, wpf-ef)")
    parser.add_argument("--name", required=True,
                        help="project name (identifier: letters, digits, "
                             "underscore)")
    parser.add_argument("--ide", choices=IDE_CHOICES, default="both",
                        help="IDE assets to emit (default: both)")
    parser.add_argument("--test-framework", dest="test_framework",
                        default=None,
                        help="test framework for templates that offer a "
                             "choice (e.g. csharp: NUnit, xUnit, MSTest)")
    parser.add_argument("--out", default=".",
                        help="output directory (default: current directory)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing files")
    args = parser.parse_args()

    if not NAME_PATTERN.match(args.name):
        parser.error(
            f"invalid --name '{args.name}': must match {NAME_PATTERN.pattern}")

    key = (args.stack, args.layout)
    if key not in templates:
        layouts = sorted(t or "(default)" for s, t in templates
                         if s == args.stack)
        parser.error(
            f"no template for stack '{args.stack}' with type "
            f"'{args.layout or '(default)'}'. Available types: "
            f"{', '.join(layouts)}")

    with open(templates[key] / MANIFEST_NAME, encoding="utf-8") as fh:
        manifest = json.load(fh)
    test_framework, tf_error = resolve_test_framework(
        manifest, args.test_framework)
    if tf_error:
        parser.error(tf_error)

    return scaffold(templates[key], args.name, args.ide,
                    Path(args.out).resolve(), args.force, test_framework)


if __name__ == "__main__":
    sys.exit(main())
