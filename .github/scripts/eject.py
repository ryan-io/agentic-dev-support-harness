#!/usr/bin/env python3
"""
eject.py
The harness-eject engine. Trims template-only machinery from a clone once a
downstream project has run project-setup.

Phase 1 scope: manifest load, path classification, keep-set guard, dry-run
preview, categorized removal, resets, the closing sync-and-validate gate, and
the single eject commit whose revert restores the pre-eject tree.

Phase 2 scope (also this file): after removal, scrub backtick path references
to removed paths from the two validator-gated files and every README, and trim
the scaffolder step from the project-setup skill when Category B is removed.
The validator itself is already eject-aware (its setup-engine and templates
checks gate on .claude/setup-complete), so no validator edit happens here.

Stdlib only. Fails clean: a bad manifest raises ManifestError, a failed run
step raises EjectError after rolling back; a partial eject never lands. Run
from the repo root:
  python .github/scripts/eject.py --list                  # classification, read-only
  python .github/scripts/eject.py --check                 # validate manifest + guard state
  python .github/scripts/eject.py --dry-run               # preview the run, no changes
  python .github/scripts/eject.py --run                   # the destructive run
  python .github/scripts/eject.py --run --keep-scaffolder # retain Category B

Decision record: docs/adr/adr-setup-introduce-harness-eject.md
Plans: docs/process/2026-06-07-harness-eject-plan.md,
       docs/process/2026-06-10-finalize-unity-adopt-plan.md
"""

import json
import os
import re
import shutil
import subprocess
import sys

MANIFEST_PATH = os.path.join(".github", "scripts", "eject-manifest.json")
SYNC_SCRIPT = os.path.join(".github", "scripts", "sync-claude-rules.py")
VALIDATE_SCRIPT = os.path.join(".github", "scripts", "validate-system.py")
EJECT_COMMIT_MESSAGE = "chore: eject harness template machinery"

# The two files whose backtick path references the validator gates (check 5),
# plus the skill the scaffolder trim edits.
GATED_REFERENCE_FILES = [
    os.path.join(".github", "copilot-instructions.md"),
    os.path.join(".github", "docs", "system-index.md"),
]
PROJECT_SETUP_SKILL = os.path.join(".github", "skills", "project-setup", "SKILL.md")
SKILLS_README = os.path.join(".github", "skills", "README.md")


class ManifestError(Exception):
    """Raised when the manifest is malformed or violates the keep-set guard."""


class EjectError(Exception):
    """Raised when a run step fails; the run rolls back before raising."""


# --- Reset skeletons -------------------------------------------------------
# "reset" rewrites a kept file to a new-project skeleton. The project name is
# derived from the repository directory at run time.

README_SKELETON = """# {name}

Describe the project here: what it is, who it serves, how to build and test it.

This repository is governed by the agentic-dev-support-harness: instruction
files under `.github/instructions/` (mirrored to `.claude/rules/`), decisions
under `docs/adr/`, business rules under `docs/business-rules/`, and a
continuous-learning pipeline under `.claude/learning/`.
"""

MEMORY_SKELETON = """---
applyTo: "**"
---

# Project Memory

Durable, curated facts about this project. This file loads on turn one for every session so an agent starts oriented instead of rediscovering the codebase. The `continuous-learning` skill maintains it by promoting entries from the local session log under developer review. Do not hand-edit it mid-task; propose changes through that skill. Keep the whole file under 4,000 characters. When it fills, prune the least useful entry rather than letting it overflow.

## Orientation

This is {name}. Describe the project in two or three sentences: what it is, the stack, where the logic lives. Instruction source of truth is `.github/`; `CLAUDE.md` and `.claude/rules/` are generated mirrors kept consistent by `sync-claude-rules.py`.

## Key file map

Decisions: `docs/adr/`. Business rules: `docs/business-rules/`. Learning pipeline: `.github/scripts/learning/`; data in `.claude/learning/`. Validation: `.github/scripts/validate-system.py`, run by the pre-commit hook.

## Confirmed conventions

None recorded yet. Entries are promoted here by `continuous-learning` under developer review.

## Decisions and constraints

None recorded yet.

## Open threads

None recorded yet.
"""

RESET_CONTENT = {
    "README.md": README_SKELETON,
    ".github/instructions/memory.instructions.md": MEMORY_SKELETON,
}


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


# --- Phase 1: execution ----------------------------------------------------

def _git(args, check=True):
    res = subprocess.run(["git"] + args, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise EjectError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res


def working_tree_clean():
    return _git(["status", "--porcelain"]).stdout.strip() == ""


def _rmtree(path):
    def onerror(func, p, exc_info):
        os.chmod(p, 0o700)
        func(p)
    shutil.rmtree(path, onerror=onerror)


def _prune_empty_parents(path):
    """Remove now-empty parent directories, stopping at the repo root."""
    parent = os.path.dirname(_norm(path).rstrip("/"))
    while parent and parent not in (".", "/"):
        try:
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
            else:
                break
        except OSError:
            break
        parent = os.path.dirname(parent)


def apply_entry(entry, protected_roots, dry_run):
    """
    Perform (or preview) one manifest entry. Returns a one-line report.
    Runtime keep-set guard: refuses destructive actions on protected paths
    even if a bad manifest slipped past validation.
    """
    action = entry["action"]
    path = entry["path"].rstrip("/")
    if action in DESTRUCTIVE_ACTIONS and is_protected(path, protected_roots):
        raise EjectError(f"refusing destructive action on protected path: {path}")

    exists = os.path.exists(path)
    prefix = "[dry-run] would" if dry_run else "did"

    if action == "remove":
        if not exists:
            return f"  skip (absent)     {path}"
        if not dry_run:
            if os.path.isdir(path):
                _rmtree(path)
            else:
                os.remove(path)
            _prune_empty_parents(path)
        return f"  {prefix} remove    {path}"

    if action == "clear":
        if not exists:
            return f"  skip (absent)     {path}"
        keep = set(entry.get("keep", []))
        if not dry_run:
            for child in os.listdir(path):
                if child in keep:
                    continue
                full = os.path.join(path, child)
                if os.path.isdir(full):
                    _rmtree(full)
                else:
                    os.remove(full)
        kept = f" (keeping {', '.join(sorted(keep))})" if keep else ""
        return f"  {prefix} clear     {path}{kept}"

    if action == "reset":
        template = RESET_CONTENT.get(path)
        if template is None:
            raise EjectError(f"no reset skeleton registered for: {path}")
        if not dry_run:
            name = os.path.basename(os.path.abspath("."))
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(template.format(name=name))
        return f"  {prefix} reset     {path}"

    raise EjectError(f"unknown manifest action '{action}' for: {path}")


# --- Phase 2: reference scrub and scaffolder trim ---------------------------

def _clean_ref(ref):
    """Normalize a backtick path reference for comparison against removed paths."""
    r = _norm(ref).rstrip("/")
    while r.startswith("./") or r.startswith("../"):
        r = r[r.index("/") + 1:]
    return r


def _ref_is_removed(ref, removed_files, removed_dirs):
    clean = _clean_ref(ref)
    if clean in removed_files:
        return True
    return any(clean == d or clean.startswith(d + "/") for d in removed_dirs)


def scrub_content(content, removed_files, removed_dirs):
    """
    Drop every line whose backtick path reference points at a removed path
    (or under a removed directory). Returns (new_content, dropped_count).
    Mirrors the validator's check-5 reference filter so only checkable refs
    trigger a drop.
    """
    kept, dropped = [], 0
    for line in content.splitlines(keepends=True):
        broken = False
        for ref in re.findall(r"`([^`]+/[^`]+)`", line):
            ref = ref.strip()
            if any(c in ref for c in "*{|( ") or not 3 <= len(ref) <= 100:
                continue
            if _ref_is_removed(ref, removed_files, removed_dirs):
                broken = True
                break
        if broken:
            dropped += 1
        else:
            kept.append(line)
    return "".join(kept), dropped


def _readme_files():
    """Every README.md in the tree, skipping .git."""
    found = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d != ".git"]
        if "README.md" in files:
            found.append(os.path.normpath(os.path.join(root, "README.md")))
    return found


def scrub_references(removed_files, removed_dirs, dry_run):
    """Scrub the gated files and every README. Returns report lines."""
    reports = []
    targets = list(GATED_REFERENCE_FILES) + _readme_files()
    seen = set()
    for path in targets:
        key = os.path.normpath(path)
        if key in seen or not os.path.isfile(path):
            continue
        seen.add(key)
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        new_content, dropped = scrub_content(content, removed_files, removed_dirs)
        if dropped == 0:
            continue
        if not dry_run:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new_content)
        prefix = "[dry-run] would drop" if dry_run else "dropped"
        reports.append(f"  {prefix} {dropped} line(s)  {_norm(path)}")
    return reports


def trim_scaffolder_references(dry_run):
    """
    When Category B is removed: cut the Step 0 section from the project-setup
    skill and drop remaining scaffolder lines there and in the skills README.
    Returns report lines.
    """
    reports = []
    tokens = ("scaffold.py", "ah-ide", "Step 0", "scaffold-matrix")
    if os.path.isfile(PROJECT_SETUP_SKILL):
        with open(PROJECT_SETUP_SKILL, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        out, dropped, in_step0 = [], 0, False
        for line in lines:
            if line.startswith("### Step 0"):
                in_step0 = True
                dropped += 1
                continue
            if in_step0:
                if line.startswith("### "):
                    in_step0 = False
                else:
                    dropped += 1
                    continue
            if any(t in line for t in tokens):
                dropped += 1
                continue
            out.append(line)
        if dropped:
            if not dry_run:
                with open(PROJECT_SETUP_SKILL, "w", encoding="utf-8", newline="\n") as fh:
                    fh.writelines(out)
            prefix = "[dry-run] would trim" if dry_run else "trimmed"
            reports.append(f"  {prefix} {dropped} line(s)  {_norm(PROJECT_SETUP_SKILL)}")
    if os.path.isfile(SKILLS_README):
        with open(SKILLS_README, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        out = [ln for ln in lines if "scaffold.py" not in ln and "ah-ide" not in ln]
        dropped = len(lines) - len(out)
        if dropped:
            if not dry_run:
                with open(SKILLS_README, "w", encoding="utf-8", newline="\n") as fh:
                    fh.writelines(out)
            prefix = "[dry-run] would trim" if dry_run else "trimmed"
            reports.append(f"  {prefix} {dropped} line(s)  {_norm(SKILLS_README)}")
    return reports


def _closing_gate(dry_run):
    """Run sync then validate. Raises EjectError on a non-zero result."""
    for script in (SYNC_SCRIPT, VALIDATE_SCRIPT):
        if not os.path.isfile(script):
            print(f"  WARNING: {script} not found; gate step skipped")
            continue
        if dry_run:
            print(f"  [dry-run] would run: {script}")
            continue
        print(f"  running {script} ...")
        res = subprocess.run([sys.executable, script],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            raise EjectError(f"closing gate failed: {script} exited {res.returncode}")


def _rollback():
    """Restore the pre-eject working tree. Nothing was committed, so reset suffices."""
    _git(["reset", "--hard"], check=False)


def cmd_execute(manifest, dry_run, keep_scaffolder):
    """
    The Phase 1 run. Dry-run previews everywhere; the live run enforces the
    guards and the clean-tree precondition, applies the manifest, runs the
    closing sync-and-validate gate, and lands the whole eject as one commit.
    """
    violations = validate_manifest(manifest)
    if violations:
        print("FAIL: manifest violates the keep-set guard; nothing will run:")
        for v in violations:
            print(f"  - {v}")
        return 1

    can, reasons = guard_state(manifest)
    print(f"Guard state: {'CAN eject' if can else 'will REFUSE'}")
    for r in reasons:
        print(f"  - {r}")
    print()

    if not dry_run:
        if not can:
            print("REFUSED: guards not satisfied. Run --dry-run to preview.")
            return 1
        if not working_tree_clean():
            print("REFUSED: working tree is dirty. Commit or stash first; "
                  "eject must land as a single revertable commit.")
            return 1

    mode = "DRY RUN (no changes)" if dry_run else "LIVE RUN"
    opt = " [--keep-scaffolder: Category B retained]" if keep_scaffolder else ""
    print(f"harness-eject {mode}{opt}\n")

    entries = removal_entries(manifest, keep_scaffolder=keep_scaffolder)
    roots = manifest.get("protected_roots", [])
    current_cat = None
    try:
        for entry in entries:
            if entry["category"] != current_cat:
                current_cat = entry["category"]
                label = manifest["categories"][current_cat].get("label", "")
                print(f"Category {current_cat}: {label}")
            print(apply_entry(entry, roots, dry_run))
        removed_files = {e["path"].rstrip("/") for e in entries
                         if e["action"] == "remove" and e["type"] != "dir"}
        removed_dirs = {e["path"].rstrip("/") for e in entries
                        if e["action"] == "remove" and e["type"] == "dir"}
        print("\nReference scrub (gated files + READMEs):")
        scrub_reports = scrub_references(removed_files, removed_dirs, dry_run)
        for r in scrub_reports or ["  nothing to scrub"]:
            print(r)
        if not keep_scaffolder:
            print("\nScaffolder trim (project-setup skill, skills README):")
            trim_reports = trim_scaffolder_references(dry_run)
            for r in trim_reports or ["  nothing to trim"]:
                print(r)
        print("\nClosing gate (sync, then validate):")
        _closing_gate(dry_run)
    except EjectError as exc:
        if not dry_run:
            print(f"\nERROR: {exc}\nRolling back (git reset --hard) ...")
            _rollback()
        else:
            print(f"\nERROR: {exc}")
        return 1

    if dry_run:
        print("\nDry run complete. No changes were made.")
        return 0

    _git(["add", "-A"])
    _git(["commit", "-m", EJECT_COMMIT_MESSAGE])
    sha = _git(["rev-parse", "--short", "HEAD"]).stdout.strip()
    print(f"\nEject complete: commit {sha}.")
    print(f"Reversal: git revert {sha} restores the pre-eject tree.")
    return 0


# --- Read-only commands (Phase 0) ------------------------------------------

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
    flags = set(argv)
    keep_scaffolder = "--keep-scaffolder" in flags
    flags.discard("--keep-scaffolder")
    if len(flags) != 1:
        print("Expected exactly one of: --list, --check, --dry-run, --run "
              "(plus optional --keep-scaffolder)", file=sys.stderr)
        return 1
    cmd = flags.pop()
    try:
        manifest = load_manifest()
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if cmd == "--list":
        cmd_list(manifest)
        return 0
    if cmd == "--check":
        return cmd_check(manifest)
    if cmd == "--dry-run":
        return cmd_execute(manifest, dry_run=True, keep_scaffolder=keep_scaffolder)
    if cmd == "--run":
        return cmd_execute(manifest, dry_run=False, keep_scaffolder=keep_scaffolder)
    print(f"Unknown argument: {cmd} (try --help)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
