#!/usr/bin/env python3
"""
bootstrap-update.py
One-time installer for the harness-update mechanism into a project adopted
before the mechanism existed (audit G1). The update engine cannot deliver
itself: update.py reads a manifest and an anchor that a pre-mechanism
consumer does not have. This script closes that loop.

Run it FROM a harness clone, pointed AT the consumer:
  python .github/scripts/bootstrap-update.py --target <path> \
      [--anchor <sha>] [--record-source <url-or-path>] [--dry-run]

It installs, never overwriting an existing file (adopt collision policy):
  .github/scripts/update.py
  .github/scripts/update-manifest.json
  .github/skills/harness-update/   (recursive)
  .github/skills/harness-eject/    (recursive)
and writes .github/harness-version.json in the update.py anchor format.

--anchor defaults to the harness clone's HEAD; pass the commit the project
actually adopted for a tighter merge base (an approximate anchor can surface
extra conflicts on the first update). --record-source defaults to this
harness clone's path; pass a URL or a path that is durable on the
developer's machine, since future update runs clone from it.

Guards: refuses when the target carries .github/TEMPLATE_SOURCE (that is a
template source, not a consumer) or has no .github/ directory (not a
harness-governed project). Refuses to overwrite an existing anchor.

Skill registration is consumer-owned prose, so the script does not edit it;
it finishes by printing the registration checklist (hub On-Demand list,
system-index.md, skills README) and a reminder to commit.

Stdlib only. Decision record: docs/adr/adr-setup-add-harness-update-mechanism.md
(G1 delivery path; docs/process/2026-06-11-audit-gap-fix-plan.md Phase 1).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

# Harness clone root: two levels up from this file (.github/scripts/).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# What the mechanism needs downstream. Trees copy recursively; files copy
# verbatim. Paths are repo-relative on both sides.
FILE_INSTALLS = [
    os.path.join(".github", "scripts", "update.py"),
    os.path.join(".github", "scripts", "update-manifest.json"),
]
TREE_INSTALLS = [
    os.path.join(".github", "skills", "harness-update"),
    os.path.join(".github", "skills", "harness-eject"),
]
ANCHOR_REL = os.path.join(".github", "harness-version.json")
SENTINEL_REL = os.path.join(".github", "TEMPLATE_SOURCE")

ALWAYS_IGNORE = {"__pycache__", "*.pyc"}


class BootstrapError(Exception):
    """A guard or step failed in a way that should stop the run."""


def resolve_anchor_sha(ref):
    """Resolve ref to a full sha in the harness clone."""
    res = subprocess.run(["git", "rev-parse", ref],
                         capture_output=True, text=True, cwd=HARNESS_ROOT)
    if res.returncode != 0:
        raise BootstrapError(
            f"cannot resolve '{ref}' in {HARNESS_ROOT}: {res.stderr.strip()}")
    return res.stdout.strip()


def check_guards(target):
    if not os.path.isdir(target):
        raise BootstrapError(f"target not found: {target}")
    if os.path.abspath(target) == HARNESS_ROOT:
        raise BootstrapError("target is this harness clone itself.")
    if os.path.isfile(os.path.join(target, SENTINEL_REL)):
        raise BootstrapError(
            f"target carries {SENTINEL_REL}: it is a template source, "
            "not a consumer. Nothing to bootstrap.")
    if not os.path.isdir(os.path.join(target, ".github")):
        raise BootstrapError(
            "target has no .github/ directory: not a harness-governed "
            "project. Run the adopt path first (repository-setup.py --adopt).")
    if os.path.isfile(os.path.join(target, ANCHOR_REL)):
        raise BootstrapError(
            f"target already has {ANCHOR_REL}: the mechanism is bootstrapped. "
            "Use 'python .github/scripts/update.py --check' there instead.")


def install_file(rel, target, dry_run, report):
    src = os.path.join(HARNESS_ROOT, rel)
    dst = os.path.join(target, rel)
    if not os.path.isfile(src):
        raise BootstrapError(f"harness clone is missing {rel}; cannot install.")
    if os.path.exists(dst):
        report.append(f"  skip (exists): {rel}")
        return
    if dry_run:
        report.append(f"  [dry-run] would install: {rel}")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    report.append(f"  installed: {rel}")


def install_tree(rel, target, dry_run, report):
    src = os.path.join(HARNESS_ROOT, rel)
    if not os.path.isdir(src):
        raise BootstrapError(f"harness clone is missing {rel}/; cannot install.")
    ignore_fn = shutil.ignore_patterns(*ALWAYS_IGNORE)
    for dirpath, dirnames, filenames in os.walk(src):
        ignored = ignore_fn(dirpath, dirnames + filenames)
        dirnames[:] = [d for d in dirnames if d not in ignored]
        for fname in filenames:
            if fname in ignored:
                continue
            file_rel = os.path.relpath(os.path.join(dirpath, fname), HARNESS_ROOT)
            install_file(file_rel, target, dry_run, report)


def write_anchor(target, source, commit, dry_run, report):
    dst = os.path.join(target, ANCHOR_REL)
    if dry_run:
        report.append(f"  [dry-run] would write anchor: {commit[:9]} from {source}")
        return
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"source": source, "commit": commit}, fh, indent=2)
        fh.write("\n")
    report.append(f"  anchor written: {commit[:9]} from {source}")


def main(argv):
    parser = argparse.ArgumentParser(
        description="Install the harness-update mechanism into a "
                    "pre-mechanism consumer.")
    parser.add_argument("--target", required=True,
                        help="path to the consuming project")
    parser.add_argument("--anchor", default="HEAD",
                        help="harness commit the project adopted "
                             "(default: this clone's HEAD)")
    parser.add_argument("--record-source", default=HARNESS_ROOT,
                        help="source URL or path written into the anchor "
                             "(default: this harness clone's path)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change; write nothing")
    args = parser.parse_args(argv)

    target = os.path.abspath(args.target)
    try:
        check_guards(target)
        commit = resolve_anchor_sha(args.anchor)
        report = []
        for rel in FILE_INSTALLS:
            install_file(rel, target, args.dry_run, report)
        for rel in TREE_INSTALLS:
            install_tree(rel, target, args.dry_run, report)
        write_anchor(target, args.record_source, commit, args.dry_run, report)
    except BootstrapError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1

    print(f"Bootstrap {'preview' if args.dry_run else 'complete'}: {target}\n")
    for line in report:
        print(line)
    print("\nConsumer-side checklist (prose the script does not edit):")
    print("  1. Register harness-update and harness-eject in the hub's")
    print("     On-Demand skills list (.github/copilot-instructions.md),")
    print("     .github/docs/system-index.md, and .github/skills/README.md.")
    print("  2. Run the consumer's sync script, then validate-system.py.")
    print("  3. Commit. The anchor is the merge base for the first")
    print("     'harness-update' run; an approximate anchor can surface")
    print("     extra conflicts, so say so in the commit body.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
