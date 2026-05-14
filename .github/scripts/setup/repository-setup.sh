#!/usr/bin/env bash
# repository-setup.sh
# Initializes a new git repository and copies all template files into it.
# Run this first, then use the project-setup skill to tailor the markdown files.

set -euo pipefail

echo "============================================"
echo " Repository Setup - Project Template Init"
echo "============================================"
echo

# --- Step 1: Get target directory (default: current directory) ---

TARGET_DIR="${1:-$(pwd)}"
if [ "$#" -eq 0 ]; then
    echo "No path provided - using current directory."
fi

# --- Step 2: Validate target ---

echo "Target: $TARGET_DIR"
echo

if [ -d "$TARGET_DIR/.git" ]; then
    echo "ERROR: $TARGET_DIR is already a git repository."
    echo "       Use an empty or non-git directory."
    exit 1
fi

# --- Step 3: Create target directory if needed ---

if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR" || { echo "ERROR: Could not create directory: $TARGET_DIR"; exit 1; }
    echo "Created: $TARGET_DIR"
else
    echo "Using existing directory: $TARGET_DIR"
fi

# --- Step 4: Initialize git repository ---

echo
echo "Initializing git repository..."
git init "$TARGET_DIR" || { echo "ERROR: git init failed."; exit 1; }

# --- Step 5: Copy template files ---

SRC="$(cd "$(dirname "$0")/../../.." && pwd)"
echo
echo "Copying template files from: $SRC"
echo "                          to: $TARGET_DIR"
echo

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

# --- Step 6: Install git hooks ---

echo
echo "Installing git hooks..."
if [ ! -d "$TARGET_DIR/.git" ]; then
    echo "ERROR: $TARGET_DIR is not a git repository. Hook installation skipped."
    exit 1
fi
git -C "$TARGET_DIR" config core.hooksPath .github/hooks || {
    echo "ERROR: Failed to configure git hooks."
    exit 1
}
echo "Git hooks installed. Pre-commit sync is now active."

# --- Step 7: Run initial sync ---

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
echo "  1. Open the repository in your editor."
echo "  2. Run the project-setup skill to tailor"
echo "     template files to your stack."
echo "  3. Make your initial commit."
