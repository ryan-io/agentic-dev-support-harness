#!/usr/bin/env python3
"""
propose.py
Promotion engine for continuous learning.
Reads instincts from .claude/learning/instincts/, promotes high-confidence
instincts to proposals, applies staleness decay, and archives expired proposals.

Proposals are markdown files in .claude/learning/proposals/ that suggest
concrete changes to instruction files.

Run from repo root: python .github/scripts/propose.py
Called automatically by analyze.py after instinct creation/update.
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta

# --- Paths ---

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
LEARNING_DIR = os.path.join(PROJECT_DIR, ".claude", "learning")
INSTINCTS_DIR = os.path.join(LEARNING_DIR, "instincts")
PROPOSALS_DIR = os.path.join(LEARNING_DIR, "proposals")
ARCHIVE_DIR = os.path.join(LEARNING_DIR, "proposals.archive")
CONFIG_FILE = os.path.join(LEARNING_DIR, "config.json")
INSTRUCTIONS_DIR = os.path.join(PROJECT_DIR, ".github", "instructions")

# --- Config ---

DEFAULT_CONFIG = {
    "thresholds": {"proposal_confidence_threshold": 0.7},
    "staleness": {
        "proposal_decay_days": 30,
        "proposal_archive_days": 60,
        "instinct_decay_per_month": 0.05
    }
}


def load_config():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG


# --- Instinct I/O ---

def parse_instinct(path):
    """Parse an instinct YAML file into a dict."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    data = {"_path": path, "_filename": os.path.basename(path)}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"')
            if key == "confidence":
                try:
                    val = float(val)
                except ValueError:
                    val = 0.0
            elif key == "evidence_count":
                try:
                    val = int(val)
                except ValueError:
                    val = 0
            data[key] = val
    data["body"] = parts[2].strip()
    return data


def save_instinct_confidence(path, new_confidence):
    """Update just the confidence value in an instinct file."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    updated = re.sub(
        r'(confidence:\s*)[\d.]+',
        f'\\g<1>{new_confidence:.2f}',
        content
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)


# --- Staleness decay ---

def apply_instinct_decay(instincts, decay_per_month):
    """Reduce confidence of instincts not seen recently."""
    now = datetime.now(timezone.utc)
    for inst in instincts:
        last_seen = inst.get("last_seen", "")
        if not last_seen:
            continue
        try:
            seen_date = datetime.strptime(last_seen, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        months_stale = (now - seen_date).days / 30.0
        if months_stale > 1.0:
            decay = decay_per_month * months_stale
            old_conf = inst.get("confidence", 0.0)
            new_conf = max(0.1, round(old_conf - decay, 2))
            if new_conf != old_conf:
                inst["confidence"] = new_conf
                save_instinct_confidence(inst["_path"], new_conf)
                print(
                    f"  [decay] {inst.get('id', '?')}: "
                    f"{old_conf:.2f} -> {new_conf:.2f} "
                    f"({months_stale:.1f} months stale)",
                    file=sys.stderr
                )


# --- Target mapping ---

def map_target_file(instinct):
    """Map an instinct's domain/file_scope to a target instruction file."""
    domain = instinct.get("domain", "")
    file_scope = instinct.get("file_scope", "**")

    # Meta instincts (rule/guide consultation patterns)
    if domain == "meta":
        return "agent-guardrails.instructions.md"

    # Testing-related instincts
    if domain == "testing":
        return "testing.instructions.md"

    # Code style with specific extension
    if domain == "code-style":
        # Check if there's a language-specific file
        if file_scope and file_scope != "**":
            # Try to find a matching language-specific file
            ext = ""
            match = re.search(r'\*\.(\w+)', file_scope)
            if match:
                ext = match.group(1)
            if ext and os.path.isdir(INSTRUCTIONS_DIR):
                for f in os.listdir(INSTRUCTIONS_DIR):
                    if ext.lower() in f.lower() and f.endswith(".instructions.md"):
                        return f
        return "code-standards.instructions.md"

    # Error handling
    if domain == "error-handling":
        return "code-standards.instructions.md"

    # Git and shell instincts (commit workflow, agent behavior)
    if domain in ("git", "shell", "navigation"):
        return "agent-guardrails.instructions.md"

    # Workflow patterns
    if domain == "workflow":
        return "patterns.instructions.md"

    # Default
    return "code-standards.instructions.md"


# --- Priority scoring ---

def compute_priority(instinct):
    """Return an integer 1-5 based on evidence count and confidence."""
    evidence_count = instinct.get("evidence_count", 0)
    confidence = instinct.get("confidence", 0.0)
    if evidence_count >= 10 and confidence >= 0.8:
        return 5
    if evidence_count >= 5 and confidence >= 0.7:
        return 4
    if evidence_count >= 3:
        return 3
    if evidence_count >= 2:
        return 2
    return 1


# --- Proposal generation ---

def generate_proposal(instinct, target_file):
    """Generate a proposal markdown file from a high-confidence instinct."""
    iid = instinct.get("id", "unknown")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    priority = compute_priority(instinct)

    content = f"""---
id: {iid}
status: pending
target: {target_file}
instinct_confidence: {instinct.get('confidence', 0.0):.2f}
evidence_count: {instinct.get('evidence_count', 0)}
priority: {priority}
created: "{now}"
last_reviewed: "{now}"
---

# Proposal: {instinct.get('body', '').split(chr(10))[0].lstrip('# ')}

## Trigger
{instinct.get('trigger', 'Unknown trigger')}

## Suggested Change
Add to `{target_file}`:

> {instinct.get('body', '').split(chr(10))[0].lstrip('# ')}

## Evidence
Confidence: {instinct.get('confidence', 0.0):.2f} from {instinct.get('evidence_count', 0)} observations.
Domain: {instinct.get('domain', 'unknown')} | Scope: `{instinct.get('file_scope', '**')}`

{instinct.get('body', '').split('## Evidence')[-1].strip() if '## Evidence' in instinct.get('body', '') else ''}

## Review
- [ ] Reviewed by developer
- [ ] Change applied to instruction file
"""
    return content


def proposal_exists(iid):
    """Check if a proposal already exists for this instinct."""
    if not os.path.isdir(PROPOSALS_DIR):
        return False
    for f in os.listdir(PROPOSALS_DIR):
        if f == f"{iid}.md":
            return True
    return False


# --- Proposal decay and archive ---

def process_existing_proposals(config):
    """Apply decay and archive logic to existing proposals."""
    if not os.path.isdir(PROPOSALS_DIR):
        return

    now = datetime.now(timezone.utc)
    decay_days = config.get("staleness", {}).get("proposal_decay_days", 30)
    archive_days = config.get("staleness", {}).get("proposal_archive_days", 60)

    for fname in os.listdir(PROPOSALS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(PROPOSALS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse created date
        created_match = re.search(r'created:\s*"?(\d{4}-\d{2}-\d{2})"?', content)
        if not created_match:
            continue
        try:
            created = datetime.strptime(
                created_match.group(1), "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        age_days = (now - created).days

        # Archive if past archive threshold
        if age_days >= archive_days:
            status_match = re.search(r'status:\s*(\w+)', content)
            status = status_match.group(1) if status_match else "pending"
            if status == "pending":
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
                archive_path = os.path.join(ARCHIVE_DIR, fname)
                shutil.move(path, archive_path)
                print(
                    f"  [archive] {fname}, {age_days}d old, moved to archive",
                    file=sys.stderr
                )
                continue

        # Mark as stale if past decay threshold
        if age_days >= decay_days:
            if "status: pending" in content:
                updated = content.replace("status: pending", "status: stale")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(updated)
                print(
                    f"  [stale] {fname}, {age_days}d old, marked stale",
                    file=sys.stderr
                )


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Promote high-confidence instincts to proposals."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview promotion decisions without writing files."
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    config = load_config()
    threshold = config.get("thresholds", {}).get(
        "proposal_confidence_threshold", 0.7
    )
    decay_per_month = config.get("staleness", {}).get(
        "instinct_decay_per_month", 0.05
    )

    # Load all instincts
    instincts = []
    if os.path.isdir(INSTINCTS_DIR):
        for fname in os.listdir(INSTINCTS_DIR):
            if not fname.endswith(".yaml"):
                continue
            inst = parse_instinct(os.path.join(INSTINCTS_DIR, fname))
            if inst:
                instincts.append(inst)

    if not instincts:
        print("[propose] No instincts to evaluate.", file=sys.stderr)
        sys.exit(0)

    if dry_run:
        print(
            f"[propose] DRY RUN: Evaluating {len(instincts)} instincts...",
            file=sys.stderr
        )
    else:
        print(
            f"[propose] Evaluating {len(instincts)} instincts...",
            file=sys.stderr
        )

    # Step 1: Apply staleness decay to instincts
    if dry_run:
        now = datetime.now(timezone.utc)
        for inst in instincts:
            last_seen = inst.get("last_seen", "")
            if not last_seen:
                continue
            try:
                seen_date = datetime.strptime(last_seen, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            months_stale = (now - seen_date).days / 30.0
            if months_stale > 1.0:
                decay = decay_per_month * months_stale
                old_conf = inst.get("confidence", 0.0)
                new_conf = max(0.1, round(old_conf - decay, 2))
                if new_conf != old_conf:
                    print(
                        f"  [dry-run][decay] {inst.get('id', '?')}: "
                        f"{old_conf:.2f} -> {new_conf:.2f} "
                        f"({months_stale:.1f} months stale)",
                        file=sys.stderr
                    )
                    inst["confidence"] = new_conf
    else:
        apply_instinct_decay(instincts, decay_per_month)

    # Step 2: Process existing proposals (decay + archive)
    if dry_run:
        if os.path.isdir(PROPOSALS_DIR):
            now = datetime.now(timezone.utc)
            decay_days = config.get("staleness", {}).get(
                "proposal_decay_days", 30
            )
            archive_days = config.get("staleness", {}).get(
                "proposal_archive_days", 60
            )
            for fname in os.listdir(PROPOSALS_DIR):
                if not fname.endswith(".md"):
                    continue
                path = os.path.join(PROPOSALS_DIR, fname)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                created_match = re.search(
                    r'created:\s*"?(\d{4}-\d{2}-\d{2})"?', content
                )
                if not created_match:
                    continue
                try:
                    created = datetime.strptime(
                        created_match.group(1), "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                age_days = (now - created).days
                if age_days >= archive_days:
                    status_match = re.search(r'status:\s*(\w+)', content)
                    status = (
                        status_match.group(1) if status_match else "pending"
                    )
                    if status == "pending":
                        print(
                            f"  [dry-run][archive] {fname}, "
                            f"{age_days}d old, would be archived",
                            file=sys.stderr
                        )
                        continue
                if age_days >= decay_days:
                    if "status: pending" in content:
                        print(
                            f"  [dry-run][stale] {fname}, "
                            f"{age_days}d old, would be marked stale",
                            file=sys.stderr
                        )
    else:
        process_existing_proposals(config)

    # Step 3: Promote high-confidence instincts to proposals
    if not dry_run:
        os.makedirs(PROPOSALS_DIR, exist_ok=True)
    promoted = 0
    for inst in instincts:
        conf = inst.get("confidence", 0.0)
        iid = inst.get("id", "")
        if conf < threshold:
            continue
        if proposal_exists(iid):
            continue

        target = map_target_file(inst)
        priority = compute_priority(inst)

        if dry_run:
            print(
                f"  [dry-run][promote] {iid} (conf={conf:.2f}, "
                f"priority={priority}) -> {target}",
                file=sys.stderr
            )
            promoted += 1
        else:
            content = generate_proposal(inst, target)
            proposal_path = os.path.join(PROPOSALS_DIR, f"{iid}.md")
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(content)
            promoted += 1
            print(
                f"  [promote] {iid} (conf={conf:.2f}, "
                f"priority={priority}) -> {target}",
                file=sys.stderr
            )

    prefix = "[propose] DRY RUN:" if dry_run else "[propose]"
    print(
        f"{prefix} {promoted} new proposals from {len(instincts)} instincts.",
        file=sys.stderr
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
