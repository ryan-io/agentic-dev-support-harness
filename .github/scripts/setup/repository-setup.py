#!/usr/bin/env python3
"""
repository-setup.py
The repository-setup engine. Sets up a project from this harness template,
cross-platform, replacing the former repository-setup.sh / .bat pair.

Two modes, auto-detected:
  - Activate in place: run from inside a repo already created from the template
    (GitHub's "Use this template"). Configures the hook path, makes the hook
    executable, installs a .git/hooks compatibility symlink, then runs sync,
    validation, and the ah-ide smoke check. No files copied.
  - Scaffold: run pointing at an empty / non-git directory. Initializes git,
    copies the template files, then activates as above.

Setup never edits a shell rc file or the system environment (ADR-SCAFFOLD
Amendment 2026-06-08). The scaffolder is invoked through Python as
python .github/scripts/scaffold.py. --remove-path strips PATH entries an
earlier setup wrote, for clones that ran the superseded version.

Stdlib only. Run from the repo root (no shell or batch wrappers ship; the git
hook is the only shell script in the template):
  python .github/scripts/setup/repository-setup.py            # activate / scaffold
  python .github/scripts/setup/repository-setup.py --dry-run  # preview, no changes
  python .github/scripts/setup/repository-setup.py /path/to/new/dir
  python .github/scripts/setup/repository-setup.py --remove-path

Decision record: docs/adr/adr-scaffold-introduce-ah-ide-cli.md (Amendment 2026-06-08)
Plan: docs/process/2026-06-08-setup-python-engine-plan.md
"""

import os
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
    "CLAUDE.md", ".gitignore",
]

# Directory trees copied in scaffold mode. .github carries everything under it
# (instructions, scripts, skills, docs, hooks); exclude .git and the sync log.
# Banner art is template-repo branding; no copy path ships it (eject removes
# it on the template-clone path).
TREE_COPIES = [
    (".github", {".git", "sync_log.txt"}),
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
    ignore_fn = shutil.ignore_patterns(*ignore) if ignore else None
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

def run_setup(target, dry_run=False):
    print("============================================")
    print(" Repository Setup - Project Template Init")
    print("============================================\n")
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
    flags = {"--dry-run", "--remove-path"}
    positionals = [a for a in argv if a not in flags]

    try:
        if "--remove-path" in argv:
            remove_path(dry_run)
            return 0
        check_prerequisites()
        target = os.path.abspath(positionals[0]) if positionals else os.getcwd()
        run_setup(target, dry_run)
        return 0
    except SetupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
