#!/usr/bin/env bash
cd "$(dirname "$0")/../../.." || exit 1
if command -v python3 >/dev/null 2>&1; then
    python3 .github/scripts/sync-claude-rules.py
elif command -v python >/dev/null 2>&1; then
    python .github/scripts/sync-claude-rules.py
else
    echo "ERROR: python not found on PATH. Install Python 3 and retry." >&2
    exit 1
fi
