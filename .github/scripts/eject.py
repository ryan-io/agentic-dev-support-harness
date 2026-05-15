#!/usr/bin/env python3
"""
eject.py
The harness-eject engine. Trims template-only machinery from a clone once a
downstream project has run project-setup.

Phase 0 scope (this file): load the removal manifest, classify paths, enforce
the keep-set guard (the engine never acts on a protected path), and report
guard state read-only. The destructive run (dry-run preview, removal, reversal
commit, reference scrub) lands in Phase 1.

Stdlib only. Fails clean: a bad manifest raises ManifestError; nothing is
deleted in this phase. Run from the repo root:
  python .github/scripts/eject.py --list    # classification, read-only
  python .github/scripts/eject.py --check    # validate manifest + guard state

Decision record: docs/adr/adr-setup-introduce-harness-eject.md
Plan: docs/process/2026-06-07-harness-eject-plan.md
"""

import json
import os
import sys

MANIFEST_PATH = os.path.join(".github", "scripts", "eject-manifest.json")


class ManifestError(Exception):
    """Raised when the manifest is malformed or violates the keep-set guard."""


def load_manifest(path=MANIFEST_PATH):
    """Load and parse the manifest. Raises ManifestError on read/parse failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise ManifestError(f"manifest not found: {path}")
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}")
    if "categories" not in data or "protected_roots" not in data:
        raise ManifestError("manifest missing 'categories' or 'protected_roots'")
    return data


def _norm(p):
    return p.replace("\\", "/").strip()


def is_protected(path, protected_roots):
    """True when path is a protected root or sits under one."""
    p = _norm(path).rstrip("/")
    for root in protected_roots:
        r = _norm(root)
        if r.endswith("/"):
            base = r.rstrip("/")
            if p == base or p.startswith(base + "/"):
                return True
        elif p == r:
            return True
    return False


def removal_entries(manifest, keep_scaffolder=False):
    """
    Flatten the manifest into a list of entries the engine would act on.
    Each entry: {path, type, category, action, keep}. Honors the
    --keep-scaffolder opt-out by dropping Category B.
    """
    entries = []
    for cat_key, cat in manifest["categories"].items():
        if keep_scaffolder and cat.get("optional") and cat.get("optout_flag") == "--keep-scaffolder":
            continue
        cat_action = cat.get("action")
        for item in cat.get("paths", []):
            entries.append({
                "path": _norm(item["path"]),
                "type": item.get("type", "file"),
                "category": cat_key,
                "action": item.get("action", cat_action),
                "keep": item.get("keep", []),
            })
    return entries


# Actions that delete content. "reset" rewrites a kept file and is allowed to
# target protected files (e.g. the memory instruction file); deleting ones are not.
DESTRUCTIVE_ACTIONS = {"remove", "clear"}


def validate_manifest(manifest):
    """
    Keep-set guard. Returns a list of violation strings; empty means valid.
    A destructive action whose path is a protected root, or sits under one, is
    a violation: the engine must never delete a Category D path.
    """
    violations = []
    roots = manifest.get("protected_roots", [])
    # Consider both run modes so an opt-out cannot smuggle a bad entry past the check.
    seen = set()
    for keep in (False, True):
        for entry in removal_entries(manifest, keep_scaffolder=keep):
            key = (entry["path"], entry["action"])
            if key in seen:
                continue
            seen.add(key)
            if entry["action"] in DESTRUCTIVE_ACTIONS and is_protected(entry["path"], roots):
                violations.append(
                    f"{entry['category']}: '{entry['path']}' "
                    f"({entry['action']}) is under a protected root"
                )
    return violations


def guard_state(manifest):
    """
    Read-only report of the two run-context guards. Returns
    (can_eject, reasons). Does not enforce; callers decide.
    """
    guards = manifest.get("guards", {})
    marker = guards.get("require_marker")
    sentinel = guards.get("refuse_if_present")
    reasons = []
    can = True
    if marker and not os.path.isfile(marker):
        can = False
        reasons.append(f"required marker absent: {marker} (project-setup not completed)")
    if sentinel and os.path.exists(sentinel):
        can = False
        reasons.append(f"upstream sentinel present: {sentinel} (this looks like the template source)")
    if can:
        reasons.append("guards satisfied: project-setup completed and not the template source")
    return can, reasons


def cmd_list(manifest):
    print("harness-eject removal plan (read-only)\n")
    for cat_key in sorted(manifest["categories"]):
        cat = manifest["categories"][cat_key]
        tag = f" [opt-out: {cat['optout_flag']}]" if cat.get("optout_flag") else ""
        print(f"Category {cat_key}: {cat.get('label', '')}{tag}")
        for item in cat.get("paths", []):
            action = item.get("action", cat.get("action", "?"))
            exists = "ok " if os.path.exists(_norm(item["path"])) else "MISSING"
            print(f"  [{exists}] {action:7} {item['path']}")
        print()


def cmd_check(manifest):
    violations = validate_manifest(manifest)
    if violations:
        print("FAIL: manifest violates the keep-set guard:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("PASS: manifest respects the keep-set guard")
    can, reasons = guard_state(manifest)
    print(f"\nGuard state: {'CAN eject' if can else 'will REFUSE'}")
    for r in reasons:
        print(f"  - {r}")
    return 1 if violations else 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    try:
        manifest = load_manifest()
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if argv[0] == "--list":
        cmd_list(manifest)
        return 0
    if argv[0] == "--check":
        return cmd_check(manifest)
    if argv[0] in ("--dry-run", "--run"):
        print("Eject execution is not implemented yet (Phase 1). "
              "Use --list or --check.", file=sys.stderr)
        return 2
    print(f"Unknown argument: {argv[0]} (try --help)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
