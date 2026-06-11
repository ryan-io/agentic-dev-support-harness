#!/usr/bin/env python3
"""
repository-setup.py
The repository-setup engine. Sets up a project from this harness template,
cross-platform, replacing the former repository-setup.sh / .bat pair.

Three modes:
  - Activate in place (auto-detected): run from inside a repo already created
    from the template (GitHub's "Use this template"). Configures the hook path,
    makes the hook executable, installs a .git/hooks compatibility symlink, then
    runs sync, validation, and the ah-ide smoke check. No files copied.
  - Scaffold (auto-detected): run pointing at an empty / non-git directory.
    Initializes git, copies the template files, then activates as above.
  - Adopt (--adopt, explicit): overlay the template into an existing, populated
    project (e.g. a Unity Hub-created root). Collision policy: never overwrite
    an existing file, merge .gitignore (with case-insensitive collision
    negations for tracked directories), tolerate an existing .git (init only
    when absent), report every skipped collision. The template README.md is
    never copied on any path. Adopt ends by handing off to the project-setup
    skill, which chains into harness-eject.
    Decision record: docs/adr/adr-setup-add-adopt-mode-three-paths.md

Setup never edits a shell rc file or the system environment (ADR-SCAFFOLD
Amendment 2026-06-08). The scaffolder is invoked through Python as
python .github/scripts/scaffold.py. --remove-path strips PATH entries an
earlier setup wrote, for clones that ran the superseded version.

Stdlib only. Run from the repo root (no shell or batch wrappers ship; the git
hook is the only shell script in the template):
  python .github/scripts/setup/repository-setup.py            # activate / scaffold
  python .github/scripts/setup/repository-setup.py --dry-run  # preview, no changes
  python .github/scripts/setup/repository-setup.py /path/to/new/dir
  python .github/scripts/setup/repository-setup.py --adopt /path/to/existing/project
  python .github/scripts/setup/repository-setup.py --remove-path

Decision record: docs/adr/adr-scaffold-introduce-ah-ide-cli.md (Amendment 2026-06-08)
Plan: docs/process/2026-06-08-setup-python-engine-plan.md
"""

import os
import re
import shutil
import subprocess
import sys

# Repo root is three levels up from this file (.github/scripts/setup/).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

# Marker the superseded setup wrote into shell rc files. --remove-path strips
# lines carrying it so an older clone can clean up.
RC_MARKER = "# ah-ide (agentic-dev-support-harness)"

# Root files copied verbatim in scaffold mode; the rest of the tree is copied
# by directory. Setup, sync, and scaffolder are invoked through Python, so no
# root shims are shipped (ADR-SCAFFOLD Amendment 2026-06-08).
ROOT_FILES = [
    "CLAUDE.md", ".gitignore", ".gitattributes",
]

# Directory trees copied in scaffold mode. .github carries everything under it
# (instructions, scripts, skills, docs, hooks); exclude .git and the sync log.
# TEMPLATE_SOURCE is the upstream-protection sentinel; shipping it downstream
# locks eject and update behind an agent-executed deletion (audit G2), so no
# copy path carries it. Only template clones (GitHub template, activate mode)
# still hold it. Banner art is template-repo branding; no copy path ships it
# (eject removes it on the template-clone path).
TREE_COPIES = [
    (".github", {".git", "sync_log.txt", "TEMPLATE_SOURCE"}),
    (os.path.join(".claude", "rules"), None),
    ("docs", {"banner.*"}),
    ("templates", None),
]

# Single files copied in scaffold mode: learning config, hook registration, and
# the tracked proposals placeholder, but not the local learning data.
FILE_COPIES = [
    os.path.join(".claude", "learning", "config.json"),
    os.path.join(".claude", "learning", "proposals", ".gitkeep"),
    os.path.join(".claude", "settings.json"),
]


# Never ship Python bytecode from the source clone, on any copy path.
ALWAYS_IGNORE = {"__pycache__", "*.pyc"}


class SetupError(Exception):
    """A setup step failed in a way that should stop the run."""


def warn(msg):
    print(f"WARN: {msg}")


def check_prerequisites():
    """Fail early if git or a recent enough Python is missing."""
    if shutil.which("git") is None:
        raise SetupError("git not found on PATH. Install git and re-run.")
    if sys.version_info < (3, 10):
        found = ".".join(str(p) for p in sys.version_info[:3])
        raise SetupError(f"Python 3.10+ required ({found} found).")


# --- Uninstall: strip PATH entries a superseded setup wrote ---

def remove_path(dry_run=False):
    """Remove PATH entries an earlier (superseded) setup registered.

    POSIX: drop marked lines from ~/.bashrc and ~/.zshrc. Windows: drop the
    repo root from the user-scope PATH. Current setup writes none of these;
    this is a migration for clones that ran the old version.
    """
    if os.name == "nt":
        removed = _remove_path_windows(dry_run)
    else:
        removed = _remove_path_posix(dry_run)
    if not removed:
        print("No ah-ide PATH entry found.")


def _remove_path_posix(dry_run):
    removed = False
    for rc in (os.path.expanduser("~/.bashrc"), os.path.expanduser("~/.zshrc")):
        if not os.path.isfile(rc):
            continue
        with open(rc, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        kept = [ln for ln in lines if RC_MARKER not in ln]
        if len(kept) == len(lines):
            continue
        if dry_run:
            print(f"[dry-run] would remove ah-ide PATH entry from {rc}")
        else:
            with open(rc, "w", encoding="utf-8") as fh:
                fh.writelines(kept)
            print(f"Removed ah-ide PATH entry from {rc}")
        removed = True
    return removed


def _remove_path_windows(dry_run):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_READ) as key:
            current, kind = winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:
        return False
    root = SRC.rstrip("\\")
    kept = [p for p in current.split(";") if p and p.rstrip("\\") != root]
    new_value = ";".join(kept)
    if new_value == current:
        return False
    if dry_run:
        print(f"[dry-run] would remove {root} from the Windows user PATH")
        return True
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                        winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, kind, new_value)
    print(f"Removed {root} from the Windows user PATH.")
    return True


# --- Activate: configure hooks, run sync / validate / smoke check ---

def activate(target, dry_run=False):
    # Under dry-run a preceding git init is skipped, so .git may be absent;
    # a real run would have just created it. Only enforce on a live run.
    if not dry_run and not os.path.isdir(os.path.join(target, ".git")):
        raise SetupError(f"{target} is not a git repository. Hook installation skipped.")

    print("\nConfiguring git hooks...")
    _run(["git", "-C", target, "config", "core.hooksPath", ".github/hooks"], dry_run)

    hook = os.path.join(target, ".github", "hooks", "pre-commit")
    if os.path.isfile(hook) and os.name != "nt":
        if dry_run:
            print(f"[dry-run] would chmod +x {hook}")
        else:
            os.chmod(hook, os.stat(hook).st_mode | 0o111)

    _install_hook_symlink(target, dry_run)
    print("Git hooks installed. Pre-commit sync + validation is now active.")

    if dry_run:
        print("\n[dry-run] would run sync, validation, and the ah-ide smoke check")
        return

    print("\nRunning initial sync...")
    if _run_py(target, ["sync-claude-rules.py"]) != 0:
        warn("Sync had errors. Run sync manually after fixing.")

    print("\nRunning system validation...")
    if _run_py(target, ["validate-system.py"], quiet=True) == 0:
        print("Validation passed.")
    else:
        warn("Validation reported failures. Run "
             "'python .github/scripts/validate-system.py' for detail.")

    if _run_py(target, ["scaffold.py", "help"], quiet=True) == 0:
        print("Scaffolder ready (try: python .github/scripts/scaffold.py help).")
    else:
        warn("ah-ide smoke check failed. Run "
             "'python .github/scripts/scaffold.py help' for detail.")


def _install_hook_symlink(target, dry_run):
    """Symlink .git/hooks/pre-commit so clients that ignore core.hooksPath
    (e.g. GitKraken Desktop) still run the hook."""
    git_hooks = os.path.join(target, ".git", "hooks")
    link = os.path.join(git_hooks, "pre-commit")
    rel_target = os.path.join("..", "..", ".github", "hooks", "pre-commit")
    if dry_run:
        print(f"[dry-run] would symlink {link} -> {rel_target}")
        return
    try:
        os.makedirs(git_hooks, exist_ok=True)
        if os.path.islink(link) or os.path.exists(link):
            os.remove(link)
        os.symlink(rel_target, link)
    except OSError:
        warn("Could not create symlink in .git/hooks. GitKraken may not run "
             "hooks. On Windows, run as Administrator or enable Developer Mode.")


# --- Scaffold: git init + copy the template tree ---

def scaffold(target, dry_run=False):
    print("Mode: scaffold")
    print(f"Target: {target}\n")

    if os.path.isdir(os.path.join(target, ".git")):
        raise SetupError(
            f"{target} is already a git repository.\n"
            "       To set up a repo created from the GitHub template, run setup\n"
            "       from INSIDE that repo with no arguments. Otherwise, point it\n"
            "       at an empty or non-git directory.")

    if not os.path.isdir(target):
        if dry_run:
            print(f"[dry-run] would create directory: {target}")
        else:
            os.makedirs(target, exist_ok=True)
            print(f"Created: {target}")
    else:
        print(f"Using existing directory: {target}")

    print("\nInitializing git repository...")
    _run(["git", "init", target], dry_run)

    print(f"\nCopying template files from: {SRC}")
    print(f"                          to: {target}\n")
    copy_template(target, dry_run)

    activate(target, dry_run)


def copy_template(target, dry_run=False):
    for rel, ignore in TREE_COPIES:
        _copytree(os.path.join(SRC, rel), os.path.join(target, rel), dry_run, ignore)
    for rel in FILE_COPIES + ROOT_FILES:
        _copyfile(os.path.join(SRC, rel), os.path.join(target, rel), dry_run)


def _copytree(src, dst, dry_run, ignore=None):
    if not os.path.isdir(src):
        return
    if dry_run:
        print(f"[dry-run] would copy tree {os.path.relpath(src, SRC)}/")
        return
    ignore_fn = shutil.ignore_patterns(*(set(ignore or set()) | ALWAYS_IGNORE))
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_fn)
    print(f"  {os.path.relpath(src, SRC)}/")


def _copyfile(src, dst, dry_run):
    if not os.path.isfile(src):
        return
    rel = os.path.relpath(src, SRC)
    if dry_run:
        print(f"[dry-run] would copy {rel}")
        return
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {rel}")


# --- Adopt: overlay the template into an existing, populated project ---

GITIGNORE_MERGE_HEADER = "# === agentic-dev-support-harness (adopt merge) ==="


def adopt(target, dry_run=False):
    """Overlay the template into a non-empty target with the collision policy
    from adr-setup-add-adopt-mode-three-paths: never overwrite, merge
    .gitignore, tolerate an existing .git, report every skipped collision."""
    print("Mode: adopt (overlay into an existing project)")
    print(f"Target: {target}\n")

    if os.path.abspath(target) == SRC:
        raise SetupError("adopt target is the template source itself.")
    if os.path.isfile(os.path.join(target, ".github", "TEMPLATE_SOURCE")):
        raise SetupError(
            f"{target} carries .github/TEMPLATE_SOURCE: it is a template clone.\n"
            "       Run setup from inside it with no flags (activate mode) instead.")
    if not os.path.isdir(target) or not os.listdir(target):
        raise SetupError(
            "adopt requires an existing, non-empty directory.\n"
            "       For an empty or new directory, run setup without --adopt "
            "(scaffold mode).")

    # Snapshot the target's own top-level directories before the overlay, so
    # gitignore negations consider only pre-existing (project) content.
    pre_dirs = [d for d in os.listdir(target)
                if os.path.isdir(os.path.join(target, d)) and d != ".git"]

    if not os.path.isdir(os.path.join(target, ".git")):
        print("Initializing git repository (none present)...")
        _run(["git", "init", target], dry_run)

    print(f"\nOverlaying template files from: {SRC}")
    print(f"                            to: {target}\n")
    collisions = overlay_template(target, dry_run)

    for line in merge_gitignore(target, pre_dirs, dry_run):
        print(line)

    if is_unity_project(target):
        print("\nUnity project detected (ProjectSettings/ProjectVersion.txt); "
              "Git LFS is required:")
        for line in merge_unity_gitattributes(target, dry_run):
            print(line)
        if _git_lfs_available():
            _run(["git", "-C", target, "lfs", "install", "--local"], dry_run)
            if not dry_run:
                print("  git lfs install --local: done")
        else:
            warn("git-lfs not found on PATH. Install it, then run "
                 "'git lfs install' in the project before committing binary "
                 "assets (required for Unity).")

    if collisions:
        print(f"\nSkipped {len(collisions)} existing file(s) (never overwritten):")
        for c in collisions:
            print(f"  collision: {c}")
    else:
        print("\nNo collisions: no overlay file already existed in the target.")

    activate(target, dry_run)
    return collisions


def overlay_template(target, dry_run=False):
    """Copy the template trees and files, skipping anything that already
    exists. .gitignore is merged separately; the template README.md is not in
    any copy list, so it is skipped by construction. Returns the collision list."""
    collisions = []
    for rel, ignore in TREE_COPIES:
        src_root = os.path.join(SRC, rel)
        if not os.path.isdir(src_root):
            continue
        ignore_fn = shutil.ignore_patterns(*(set(ignore or set()) | ALWAYS_IGNORE))
        for dirpath, dirnames, filenames in os.walk(src_root):
            ignored = ignore_fn(dirpath, dirnames + filenames)
            dirnames[:] = [d for d in dirnames if d not in ignored]
            filenames = [f for f in filenames if f not in ignored]
            for fname in filenames:
                src = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(src, SRC)
                _overlay_file(src, os.path.join(target, rel_path),
                              rel_path, collisions, dry_run)
    for rel in FILE_COPIES + ROOT_FILES:
        if rel == ".gitignore":
            continue
        src = os.path.join(SRC, rel)
        if os.path.isfile(src):
            _overlay_file(src, os.path.join(target, rel), rel, collisions, dry_run)
    return collisions


def _overlay_file(src, dst, rel, collisions, dry_run):
    if os.path.exists(dst):
        collisions.append(rel.replace(os.sep, "/"))
        return
    if dry_run:
        print(f"[dry-run] would copy {rel}")
        return
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copy2(src, dst)


def _expand_char_classes(pattern):
    """Collapse single-char classes: '[Bb]in' -> 'bin'."""
    return re.sub(r"\[(.)(.)?\]", lambda m: m.group(1).lower(), pattern)


def _collision_negations(src_lines, pre_dirs):
    """
    Case-insensitive filesystems (Windows, macOS) match gitignore patterns
    case-insensitively, so a harness pattern like 'packages/' would swallow a
    tracked 'Packages/' directory. For each pre-existing top-level directory
    whose name matches a simple harness directory pattern case-insensitively
    but not exactly, emit a '!/Dir/' negation.
    """
    negations = []
    patterns = []
    for line in src_lines:
        p = line.strip()
        if not p or p.startswith("#") or p.startswith("!"):
            continue
        p = _expand_char_classes(p).lstrip("/").rstrip("/")
        if p and not any(ch in p for ch in "*?/"):
            patterns.append(p)
    for d in pre_dirs:
        for p in patterns:
            if p.lower() == d.lower() and p != d:
                neg = f"!/{d}/"
                if neg not in negations:
                    negations.append(neg)
    return negations


def merge_gitignore(target, pre_dirs, dry_run=False):
    """Merge the template .gitignore into the target's. Never removes a target
    line; appends missing harness lines under a marker header, then collision
    negations. Returns report lines."""
    src_path = os.path.join(SRC, ".gitignore")
    dst_path = os.path.join(target, ".gitignore")
    if not os.path.isfile(src_path):
        return ["  WARN: template .gitignore missing; nothing to merge"]
    with open(src_path, "r", encoding="utf-8") as fh:
        src_lines = fh.read().splitlines()

    if not os.path.isfile(dst_path):
        # Copying is still a merge with the (empty) target: the negation pass
        # must run, or 'packages/' would swallow a tracked 'Packages/' on
        # case-insensitive filesystems.
        negations = _collision_negations(src_lines, pre_dirs)
        if dry_run:
            report = ["[dry-run] would copy .gitignore (target has none)"]
            report += [f"[dry-run] would negate: {n}" for n in negations]
            return report
        out = list(src_lines)
        if negations:
            out.append("")
            out.append(GITIGNORE_MERGE_HEADER)
            out.append("# Adopt: on case-insensitive filesystems the harness patterns")
            out.append("# above would swallow these tracked directories; negate them.")
            out.extend(negations)
        with open(dst_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out) + "\n")
        return (["  copied .gitignore (target had none)"]
                + [f"  negated: {n}" for n in negations])

    with open(dst_path, "r", encoding="utf-8") as fh:
        dst_lines = fh.read().splitlines()
    if GITIGNORE_MERGE_HEADER in dst_lines:
        return ["  .gitignore already merged (marker present); left untouched"]

    existing = {ln.strip() for ln in dst_lines if ln.strip() and not ln.strip().startswith("#")}
    additions = [ln for ln in src_lines
                 if not ln.strip() or ln.strip().startswith("#")
                 or ln.strip() not in existing]
    negations = _collision_negations(src_lines, pre_dirs)

    if dry_run:
        report = [f"[dry-run] would merge .gitignore ({len(additions)} line(s) appended)"]
        report += [f"[dry-run] would negate: {n}" for n in negations]
        return report

    out = list(dst_lines)
    if out and out[-1].strip():
        out.append("")
    out.append(GITIGNORE_MERGE_HEADER)
    out.extend(additions)
    if negations:
        out.append("")
        out.append("# Adopt merge: on case-insensitive filesystems the harness patterns")
        out.append("# above would swallow these tracked directories; negate them.")
        out.extend(negations)
    with open(dst_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    report = [f"  merged .gitignore ({len(additions)} line(s) appended)"]
    report += [f"  negated: {n}" for n in negations]
    return report


# --- Unity LFS (adopt path) ---

UNITY_GITATTRIBUTES_REF = os.path.join(".github", "docs", "unity.gitattributes")
GITATTRIBUTES_MERGE_HEADER = "# === Unity LFS (agentic-dev-support-harness adopt merge) ==="


def is_unity_project(target):
    return os.path.isfile(os.path.join(target, "ProjectSettings", "ProjectVersion.txt"))


def _git_lfs_available():
    try:
        return subprocess.run(["git", "lfs", "version"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def merge_unity_gitattributes(target, dry_run=False):
    """Git LFS is required for Unity projects under git (adopt ADR, Amendment
    2026-06-10). Merge the reference LFS set into the target root
    .gitattributes, append-only under a marker header. Returns report lines."""
    ref_path = os.path.join(SRC, UNITY_GITATTRIBUTES_REF)
    if not os.path.isfile(ref_path):
        return [f"  WARN: {UNITY_GITATTRIBUTES_REF} missing; LFS merge skipped"]
    with open(ref_path, "r", encoding="utf-8") as fh:
        ref_lines = fh.read().splitlines()
    dst_path = os.path.join(target, ".gitattributes")
    dst_lines = []
    if os.path.isfile(dst_path):
        with open(dst_path, "r", encoding="utf-8") as fh:
            dst_lines = fh.read().splitlines()
    if GITATTRIBUTES_MERGE_HEADER in dst_lines:
        return ["  .gitattributes already carries the Unity LFS block; left untouched"]
    have = {ln.strip() for ln in dst_lines if ln.strip()}
    additions = [ln for ln in ref_lines
                 if ln.strip() and not ln.strip().startswith("#")
                 and ln.strip() not in have]
    if dry_run:
        return [f"[dry-run] would merge {len(additions)} Unity LFS line(s) "
                "into .gitattributes"]
    out = list(dst_lines)
    if out and out[-1].strip():
        out.append("")
    out.append(GITATTRIBUTES_MERGE_HEADER)
    out.append("# Required for Unity. Never route Unity text assets (.unity,")
    out.append("# .prefab, .asset, .meta) through LFS.")
    out.extend(additions)
    with open(dst_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return [f"  merged {len(additions)} Unity LFS line(s) into .gitattributes"]


# --- Subprocess helpers ---

def _run(cmd, dry_run):
    if dry_run:
        print(f"[dry-run] would run: {' '.join(cmd)}")
        return
    if subprocess.run(cmd).returncode != 0:
        raise SetupError(f"command failed: {' '.join(cmd)}")


def _run_py(target, script_args, quiet=False):
    """Run a repo script with the current interpreter, from the target root."""
    script = os.path.join(".github", "scripts", script_args[0])
    cmd = [sys.executable, script] + script_args[1:]
    stdout = subprocess.DEVNULL if quiet else None
    return subprocess.run(cmd, cwd=target, stdout=stdout).returncode


# --- Entry point ---

def run_setup(target, dry_run=False, mode=None):
    print("============================================")
    print(" Repository Setup - Project Template Init")
    print("============================================\n")
    if mode == "adopt":
        adopt(target, dry_run)
        banner, steps = "Adoption overlay complete", [
            "Open the project in your editor.",
            "Run the project-setup skill (adopt path) to tailor instruction "
            "files and merge stack-specific ignores and attributes.",
            "project-setup's final step writes .claude/setup-complete "
            "(the overlay does not copy .github/TEMPLATE_SOURCE, so there "
            "is nothing to remove).",
            "Run the harness-eject skill to remove template-only machinery "
            "(adopt chains into eject).",
        ]
        print("\n============================================")
        print(f" {banner}: {target}")
        print("============================================\n")
        print("Next steps:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
        return
    if target == SRC:
        print("Mode: activate in place")
        print(f"Target: {target}")
        print("(repository already populated -- no files copied)")
        activate(target, dry_run)
        banner, steps = "Activation complete", [
            "Run the project-setup skill to tailor template files to your stack.",
            "Commit -- the pre-commit hook will run.",
        ]
    else:
        scaffold(target, dry_run)
        banner, steps = "Setup complete", [
            "Open the repository in your editor.",
            "Run the project-setup skill to tailor template files to your stack.",
            "Make your initial commit.",
        ]
    print("\n============================================")
    print(f" {banner}: {target}")
    print("============================================\n")
    print("Next steps:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print("\nScaffold a solution with: python .github/scripts/scaffold.py "
          "<stack> --name <Name>")


def main(argv):
    if any(a in ("-h", "--help", "help") for a in argv):
        print(__doc__)
        return 0

    dry_run = "--dry-run" in argv
    adopt_mode = "--adopt" in argv
    flags = {"--dry-run", "--remove-path", "--adopt"}
    positionals = [a for a in argv if a not in flags]

    try:
        if "--remove-path" in argv:
            remove_path(dry_run)
            return 0
        check_prerequisites()
        target = os.path.abspath(positionals[0]) if positionals else os.getcwd()
        run_setup(target, dry_run, mode="adopt" if adopt_mode else None)
        return 0
    except SetupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
