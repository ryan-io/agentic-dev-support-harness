#!/usr/bin/env bash
# repository-setup.sh
# Sets up a project from this harness template. Two modes, auto-detected:
#   - Activate in place: run from inside a repo already created from the
#     template (e.g. GitHub's "Use this template"). Configures the hook
#     path, makes the hook executable, runs an initial sync. No files copied.
#   - Scaffold: run pointing at an empty / non-git directory. Initializes
#     git, copies the template files, then activates as above.

set -euo pipefail

echo "============================================"
echo " Repository Setup - Project Template Init"
echo "============================================"
echo

# --- Resolve paths ---

# SRC is the harness repo this script lives in (3 levels up from .github/scripts/setup/).
SRC="$(cd "$(dirname "$0")/../../.." && pwd)"
TARGET_DIR="${1:-$(pwd)}"
# Normalize to an absolute path when the directory already exists.
TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd || echo "$TARGET_DIR")"

# --- Shared: configure hook path, make hook executable, run sync ---

activate() {
    local dir="$1"
    echo
    echo "Configuring git hooks..."
    git -C "$dir" config core.hooksPath .github/hooks
    if [ -f "$dir/.github/hooks/pre-commit" ]; then
        chmod +x "$dir/.github/hooks/pre-commit"
    fi
    echo "Git hooks installed. Pre-commit sync + validation is now active."

    echo
    if command -v python3 &>/dev/null; then
        echo "Running initial sync..."
        (cd "$dir" && python3 .github/scripts/sync-claude-rules.py) || \
            echo "WARN: Sync had errors. Run sync manually after fixing."
    else
        echo "WARN: python3 not found. Run sync manually after installing Python."
    fi
}

# --- Mode detection ---

if [ "$SRC" = "$TARGET_DIR" ]; then
    # Running from inside the repo itself -- the "Use this template" workflow.
    echo "Mode: activate in place"
    echo "Target: $TARGET_DIR"
    echo "(repository already populated -- no files copied)"
    activate "$TARGET_DIR"

    echo
    echo "============================================"
    echo " Activation complete: $TARGET_DIR"
    echo "============================================"
    echo
    echo "Next steps:"
    echo "  1. Run the project-setup skill to tailor"
    echo "     template files to your stack."
    echo "  2. Commit -- the pre-commit hook will run."
    exit 0
fi

# --- Scaffold mode ---

echo "Mode: scaffold"
echo "Target: $TARGET_DIR"
echo

if [ -d "$TARGET_DIR/.git" ]; then
    echo "ERROR: $TARGET_DIR is already a git repository."
    echo "       To set up a repo created from the GitHub template, run this"
    echo "       script from INSIDE that repo with no arguments."
    echo "       Otherwise, point it at an empty or non-git directory."
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR" || { echo "ERROR: Could not create directory: $TARGET_DIR"; exit 1; }
    echo "Created: $TARGET_DIR"
else
    echo "Using existing directory: $TARGET_DIR"
fi

echo
echo "Initializing git repository..."
git init "$TARGET_DIR" || { echo "ERROR: git init failed."; exit 1; }

echo
echo "Copying template files from: $SRC"
echo "                          to: $TARGET_DIR"
echo

# rsync only creates the final path component; create parents explicitly.
mkdir -p "$TARGET_DIR/.github" "$TARGET_DIR/.claude/rules" \
         "$TARGET_DIR/.claude/learning" "$TARGET_DIR/docs"

rsync -a --exclude='.git' --exclude='sync_log.txt' \
    "$SRC/.github/" "$TARGET_DIR/.github/"
rsync -a "$SRC/.claude/rules/" "$TARGET_DIR/.claude/rules/"
if [ -f "$SRC/.claude/learning/config.json" ]; then
    cp "$SRC/.claude/learning/config.json" "$TARGET_DIR/.claude/learning/config.json"
    echo "  .claude/learning/config.json"
fi
rsync -a "$SRC/docs/" "$TARGET_DIR/docs/"

for f in CLAUDE.md .gitignore setup.bat setup.sh sync.bat; do
    if [ -f "$SRC/$f" ]; then
        cp "$SRC/$f" "$TARGET_DIR/$f"
        echo "  $f"
    fi
done

activate "$TARGET_DIR"

echo
echo "============================================"
echo " Setup complete: $TARGET_DIR"
echo "============================================"
echo
echo "Next steps:"
echo "  1. Open the repository in your editor."
echo "  2. Run the project-setup skill to tailor"
echo "     template files to your stack."
echo "  3. Make your initial commit."
