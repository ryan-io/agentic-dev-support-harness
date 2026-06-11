#!/usr/bin/env python3
"""
sync-claude-rules.py
1. Syncs .github/copilot-instructions.md -> CLAUDE.md (identical copy).
2. Syncs .github/instructions/*.instructions.md -> .claude/rules/ (frontmatter transform).
Validates output: correct frontmatter, non-empty body, ≤4000 chars.

Run from repo root: python .github/scripts/sync-claude-rules.py
"""

import os
import re
import glob
import sys
from datetime import datetime

SRC_DIR = os.path.join(".github", "instructions")
DEST_DIR = os.path.join(".claude", "rules")
LOG_FILE = os.path.join(".claude", "sync_log.txt")
HUB_SRC = os.path.join(".github", "copilot-instructions.md")
HUB_DEST = "CLAUDE.md"
MAX_CHARS = 4000

if not os.path.isdir(SRC_DIR):
    print(f"ERROR: {SRC_DIR} not found. Run from repo root.", file=sys.stderr)
    sys.exit(1)

os.makedirs(DEST_DIR, exist_ok=True)

log_lines = []
errors = 0

def log(msg):
    print(msg)
    log_lines.append(msg)

# --- Step 1: Sync hub file (copilot-instructions.md -> CLAUDE.md) ---

# All reads use utf-8-sig: it strips a leading BOM (common from Windows
# editors), which a strict utf-8 read leaves in the text where it breaks
# the DEPRECATED marker check and frontmatter parsing.

if os.path.isfile(HUB_SRC):
    with open(HUB_SRC, "r", encoding="utf-8-sig") as f:
        hub_content = f.read().replace("\r", "").replace("\x00", "")

    if len(hub_content) > MAX_CHARS:
        log(f"FAIL: {HUB_SRC} exceeds {MAX_CHARS} chars ({len(hub_content)})")
        errors += 1
    else:
        with open(HUB_DEST, "w", encoding="utf-8", newline="\n") as f:
            f.write(hub_content)
        log(f"SYNC: {HUB_SRC} -> {HUB_DEST} ({len(hub_content)} chars)")
else:
    log(f"WARN: {HUB_SRC} not found, skipping hub sync")

# --- Step 2: Sync instruction files -> .claude/rules/ ---

synced = 0

for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
    filename = os.path.basename(src)

    with open(src, "r", encoding="utf-8-sig") as f:
        content = f.read()

    content = content.replace("\r", "").replace("\x00", "")

    # Skip deprecated/empty files
    if content.strip().startswith("<!-- DEPRECATED"):
        log(f"SKIP: {filename} (deprecated)")
        continue

    # Validate source size
    if len(content) > MAX_CHARS:
        log(f"FAIL: {filename} exceeds {MAX_CHARS} chars ({len(content)})")
        errors += 1
        continue

    # Parse frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        log(f"FAIL: {filename} has no valid frontmatter")
        errors += 1
        continue

    # Anything before the opening --- would be silently dropped from the
    # mirror. Fail loudly instead of losing content.
    if parts[0].strip():
        log(f"FAIL: {filename} has content before frontmatter")
        errors += 1
        continue

    frontmatter = parts[1].strip()
    body = parts[2]

    # Validate body is not empty
    if not body.strip():
        log(f"FAIL: {filename} has empty body")
        errors += 1
        continue

    # Extract applyTo value
    match = re.search(r'applyTo:\s*["\']?([^"\'\n]+)["\']?', frontmatter)
    if not match:
        log(f"FAIL: {filename} has no applyTo in frontmatter")
        errors += 1
        continue

    apply_to_raw = match.group(1).strip()
    if not apply_to_raw:
        log(f"FAIL: {filename} has empty applyTo value")
        errors += 1
        continue

    # Split comma-separated applyTo values into a proper array
    apply_to_parts = [p.strip() for p in apply_to_raw.split(",") if p.strip()]
    if not apply_to_parts:
        log(f"FAIL: {filename} has empty applyTo value after parsing")
        errors += 1
        continue

    # Derive destination filename
    dest_name = filename.replace(".instructions", "")
    dest_path = os.path.join(DEST_DIR, dest_name)

    # Build output content and validate size. The body already starts with
    # the newline that followed the source's closing ---, so the template
    # adds none (B8): mirror bodies are byte-identical to their sources.
    paths_value = ", ".join(f'"{p}"' for p in apply_to_parts)
    if not body.startswith("\n"):
        body = "\n" + body
    output = f'---\npaths: [{paths_value}]\n---{body}'
    if len(output) > MAX_CHARS:
        log(f"FAIL: {dest_name} output exceeds {MAX_CHARS} chars ({len(output)})")
        errors += 1
        continue

    with open(dest_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(output)

    log(f"SYNC: {filename} -> {dest_name} ({len(output)} chars)")
    synced += 1

# --- Step 3: Clean orphaned files ---

expected = set()
for src in glob.glob(os.path.join(SRC_DIR, "*.instructions.md")):
    with open(src, "r", encoding="utf-8-sig") as f:
        content_check = f.read()
    content_check = content_check.replace("\r", "").replace("\x00", "")
    if content_check.strip().startswith("<!-- DEPRECATED"):
        continue
    expected.add(os.path.basename(src).replace(".instructions", ""))

for existing in os.listdir(DEST_DIR):
    if existing.endswith(".md") and existing not in expected:
        orphan_path = os.path.join(DEST_DIR, existing)
        try:
            os.remove(orphan_path)
            log(f"CLEAN: removed orphaned file {DEST_DIR}/{existing}")
        except OSError:
            log(f"WARN: orphaned file in {DEST_DIR}: {existing} (delete manually)")

log(f"\nDone. Hub synced. Rules synced: {synced}, Errors: {errors}")
if errors > 0:
    log("Fix errors above and re-run.")

# Append to sync log
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(LOG_FILE, "a", encoding="utf-8", newline="\n") as f:
    f.write(f"[{timestamp}]\n")
    for line in log_lines:
        f.write(f"{line}\n")
    f.write("\n")

sys.exit(1 if errors > 0 else 0)
