#!/usr/bin/env python3
"""
propose.py
Promotion engine for continuous learning.
Reads instincts from .claude/learning/instincts/, promotes high-confidence
instincts to proposals, applies staleness decay, and archives expired proposals.

Proposals are markdown files in .claude/learning/proposals/ that suggest
concrete changes to instruction files.

Run from repo root: python .github/scripts/learning/propose.py
Called automatically by analyze.py after instinct creation/update.
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timezone

import session_clock

# --- Paths ---

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
LEARNING_DIR = os.path.join(PROJECT_DIR, ".claude", "learning")
INSTINCTS_DIR = os.path.join(LEARNING_DIR, "instincts")
PROPOSALS_DIR = os.path.join(LEARNING_DIR, "proposals")
ARCHIVE_DIR = os.path.join(LEARNING_DIR, "proposals.archive")
CONFIG_FILE = os.path.join(LEARNING_DIR, "config.json")
INSTRUCTIONS_DIR = os.path.join(PROJECT_DIR, ".github", "instructions")

# --- Config ---

def load_config():
    """Load config.json, migrating date-based staleness keys in place."""
    return session_clock.migrate_config_file(CONFIG_FILE)


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
            elif key in ("evidence_count", "last_seen_session"):
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


# --- Staleness decay (session-clock, per the evidence-based staleness ADR) ---

def apply_instinct_decay(instincts, config, current_session, dry_run=False):
    """Reduce confidence of instincts not reinforced for whole session windows.

    The clock counts sessions worked, not days elapsed: a dormant repository
    is frozen, only continued work without reinforcement decays an instinct.
    Confirmed instincts are structurally exempt and skipped first."""
    staleness = config.get("staleness", {})
    rate = staleness.get("instinct_decay_per_sessions", 0.05)
    window = staleness.get("instinct_decay_session_window", 15)
    if window <= 0:
        return
    for inst in instincts:
        if session_clock.is_confirmed(inst):
            continue
        last_seen_session = inst.get("last_seen_session", None)
        if not isinstance(last_seen_session, int):
            continue  # pre-clock instinct awaiting backfill: never decay
        sessions_stale = current_session - last_seen_session
        windows_stale = sessions_stale / float(window)
        if windows_stale > 1.0:
            decay = rate * windows_stale
            old_conf = inst.get("confidence", 0.0)
            new_conf = max(0.1, round(old_conf - decay, 2))
            if new_conf != old_conf:
                inst["confidence"] = new_conf
                if not dry_run:
                    save_instinct_confidence(inst["_path"], new_conf)
                tag = "[dry-run][decay]" if dry_run else "[decay]"
                print(
                    f"  {tag} {inst.get('id', '?')}: "
                    f"{old_conf:.2f} -> {new_conf:.2f} "
                    f"({sessions_stale} sessions stale)",
                    file=sys.stderr
                )


# --- Target mapping ---

# Extension (without the dot) -> language-standards filename prefixes. Routes a
# code-style instinct to a language-specific standards file when one exists
# (e.g. ".cs" -> "csharp-code-standards.instructions.md"). Extensions with no
# language standards file (e.g. ".md") fall back to the universal file.
EXT_TO_LANG_PREFIXES = {
    "py": ["python"],
    "js": ["javascript"],
    "ts": ["typescript"],
    "cs": ["csharp"],
    "cpp": ["cpp"],
    "c": ["c"],
    "java": ["java"],
    "rb": ["ruby"],
    "go": ["go"],
    "rs": ["rust"],
    "lua": ["lua"],
    "swift": ["swift"],
    "kt": ["kotlin"],
}


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

    # Code style with a specific extension: prefer a language-specific
    # standards file when one exists. Match by the file's language prefix, not
    # a bare substring -- ".md" is a substring of every "*.instructions.md"
    # name, which previously routed markdown instincts to an arbitrary file.
    if domain == "code-style":
        if file_scope and file_scope != "**":
            match = re.search(r'\*\.(\w+)', file_scope)
            ext = match.group(1).lower() if match else ""
            langs = EXT_TO_LANG_PREFIXES.get(ext, [])
            if langs and os.path.isdir(INSTRUCTIONS_DIR):
                for f in sorted(os.listdir(INSTRUCTIONS_DIR)):
                    base = f.lower()
                    if f.endswith(".instructions.md") and any(
                        base.startswith(prefix + "-") for prefix in langs
                    ):
                        return f
        return "code-standards.instructions.md"

    # Error handling
    if domain == "error-handling":
        return "code-standards.instructions.md"

    # Git and shell instincts (commit workflow, agent behavior)
    if domain in ("git", "shell", "navigation"):
        return "agent-guardrails.instructions.md"

    # Workflow patterns. patterns.instructions.md is deprecated and not synced
    # into .claude/rules/, so an accepted workflow proposal there would never
    # load. Route to agent-guardrails (universal, synced, already home to the
    # "Detected Workflows" section) until a populated patterns file exists.
    if domain == "workflow":
        return "agent-guardrails.instructions.md"

    # Default
    return "code-standards.instructions.md"


# --- Quality gate ---

# A proposal's Suggested Change must be a rule a developer can apply, not a
# pattern description (fidelity plan Phase 2). Frequency and self-correction
# instincts pass only when their action line reads as an imperative rule.
ACTIONABLE_LEADS = (
    "place", "use", "follow", "add", "prefer", "avoid", "run", "read",
    "also read", "name", "keep", "document", "recover", "write", "route",
    "wrap", "validate", "never", "always",
)


def has_actionable_rule(instinct):
    """True if the instinct can yield an actionable Suggested Change.

    User-correction and developer-flagged instincts pass with their derived
    change descriptions attached: the developer codifies the rule at review,
    which is exactly what the review surface shows them. Everything else
    must lead with an imperative; a description like "X rarely consulted" is
    held as an instinct rather than promoted."""
    if instinct.get("provenance") in ("user-correction", "developer-flagged"):
        return bool(instinct.get("body", "").strip())
    headline = instinct.get("body", "").split("\n")[0].lstrip("# ").lower()
    return headline.startswith(ACTIONABLE_LEADS)


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

def generate_proposal(instinct, target_file, current_session=0):
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
provenance: {instinct.get('provenance', 'frequency')}
created: "{now}"
created_session: {current_session}
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


# --- Proposal decay and archive (session-clock) ---

def record_archive_reason(content, reason, current_session):
    """Append archive metadata to a proposal's frontmatter.

    Every archived file must carry a reason a developer can read; a proposal
    never disappears without one (ADR enforcement clause). Valid reasons:
    decayed, irrelevant, rejected."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content + (
            f"\n<!-- archived_reason: {reason}, "
            f"session: {current_session}, date: {today} -->\n"
        )
    meta = (
        f"archived_reason: {reason}\n"
        f"archived_session: {current_session}\n"
        f'archived: "{today}"'
    )
    return f"---{parts[1].rstrip()}\n{meta}\n---{parts[2]}"


def process_existing_proposals(config, current_session, dry_run=False):
    """Apply session-clock staleness to pending proposals.

    A pending proposal goes stale after proposal_decay_sessions without
    reinforcement and archives (reason: decayed) at proposal_archive_sessions.
    Confirmed proposals and any non-pending status are untouched."""
    if not os.path.isdir(PROPOSALS_DIR):
        return

    staleness = config.get("staleness", {})
    decay_sessions = staleness.get("proposal_decay_sessions", 15)
    archive_sessions = staleness.get("proposal_archive_sessions", 30)

    for fname in os.listdir(PROPOSALS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(PROPOSALS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Permanence guarantee: confirmed knowledge never decays.
        if session_clock.content_is_confirmed(content):
            continue

        status_match = re.search(r'status:\s*(\w+)', content)
        status = status_match.group(1) if status_match else "pending"
        if status not in ("pending", "stale"):
            continue

        created_match = re.search(r'created_session:\s*(\d+)', content)
        if not created_match:
            continue  # pre-clock proposal awaiting backfill: never decay
        sessions_old = current_session - int(created_match.group(1))

        # Archive past the archive threshold, with a recorded reason.
        if sessions_old >= archive_sessions:
            tag = "[dry-run][archive]" if dry_run else "[archive]"
            if not dry_run:
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
                updated = record_archive_reason(
                    content, "decayed", current_session
                )
                with open(path, "w", encoding="utf-8") as f:
                    f.write(updated)
                shutil.move(path, os.path.join(ARCHIVE_DIR, fname))
            print(
                f"  {tag} {fname}, {sessions_old} sessions old, "
                f"archived (reason: decayed)",
                file=sys.stderr
            )
            continue

        # Mark stale past the decay threshold.
        if sessions_old >= decay_sessions and status == "pending":
            tag = "[dry-run][stale]" if dry_run else "[stale]"
            if not dry_run:
                updated = content.replace("status: pending", "status: stale")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(updated)
            print(
                f"  {tag} {fname}, {sessions_old} sessions old, marked stale",
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
    current_session = session_clock.read_session_count(LEARNING_DIR)

    # Stamp pre-clock artifacts so nothing decays retroactively.
    if not dry_run:
        session_clock.backfill_session_fields(LEARNING_DIR, current_session)

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

    # Step 1: Apply session-clock staleness decay to instincts
    apply_instinct_decay(instincts, config, current_session, dry_run=dry_run)

    # Step 2: Process existing proposals (stale marking + archive)
    process_existing_proposals(config, current_session, dry_run=dry_run)

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

        # Quality gate: hold instincts whose Suggested Change would be a
        # pattern description rather than an applicable rule.
        if not has_actionable_rule(inst):
            print(
                f"  [hold] {iid} (conf={conf:.2f}): no actionable rule "
                f"text; held as instinct",
                file=sys.stderr
            )
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
            content = generate_proposal(inst, target, current_session)
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
