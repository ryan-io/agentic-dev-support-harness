#!/usr/bin/env bash
# llm-sw-setup.sh
# Drop into any directory and run to initialize it as a new project
# from the template repo. Sets up git, copies files, installs hooks, runs sync.

set -euo pipefail

SRC="$HOME/source/projects/claude-workflows/agentic-dev-support-harness"
TARGET_DIR="$(pwd)"

echo "============================================"
echo " Quick Setup - Project Template Init"
echo "============================================"
echo
echo "Source:  $SRC"
echo "Target:  $TARGET_DIR"
echo

# --- Validate ---

if [ ! -d "$SRC/.github" ]; then
    echo "ERROR: Template source not found at $SRC"
    echo "       Update the SRC variable in this script to match your template location."
    exit 1
fi

if [ -d "$TARGET_DIR/.git" ]; then
    echo "ERROR: $TARGET_DIR is already a git repository."
    exit 1
fi

# --- Initialize git ---

echo "Initializing git repository..."
git init "$TARGET_DIR"

# --- Copy template files ---

echo
echo "Copying template files..."

rsync -a --exclude='.git' --exclude='sync_log.txt' \
    "$SRC/.github/" "$TARGET_DIR/.github/"
rsync -a "$SRC/.claude/rules/" "$TARGET_DIR/.claude/rules/"

# Create learning directory and copy config
mkdir -p "$TARGET_DIR/.claude/learning"
if [ -f "$SRC/.claude/learning/config.json" ]; then
    cp "$SRC/.claude/learning/config.json" "$TARGET_DIR/.claude/learning/config.json"
    echo "  .claude/learning/config.json"
fi

rsync -a "$SRC/docs/" "$TARGET_DIR/docs/"

# Copy root files (setup shims, gitignore, hub file)
for f in CLAUDE.md .gitignore setup.bat setup.sh sync.bat; do
    if [ -f "$SRC/$f" ]; then
        cp "$SRC/$f" "$TARGET_DIR/$f"
        echo "  $f"
    fi
done

# --- Install hooks ---

echo
echo "Installing git hooks..."
git -C "$TARGET_DIR" config core.hooksPath .github/hooks
echo "Git hooks installed."

# --- Initial sync ---

echo
if command -v python3 &>/dev/null; then
    echo "Running initial sync..."
    (cd "$TARGET_DIR" && python3 .github/scripts/sync-claude-rules.py) || \
        echo "WARN: Sync had errors. Run sync manually after fixing."
else
    echo "WARN: python3 not found. Run sync manually after installing Python."
fi

# --- Done ---

echo
echo "============================================"
echo " Setup complete: $TARGET_DIR"
echo "============================================"
echo
echo "Next steps:"
echo "  1. Open this directory in your editor."
echo "  2. Run the project-setup skill to tailor"
echo "     template files to your stack."
echo "  3. Make your initial commit."
