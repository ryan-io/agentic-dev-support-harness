#!/usr/bin/env python3
"""
session_clock.py
Shared session-clock primitives for the evidence-based staleness model
(ADR: adr-learn-replace-wall-clock-decay-with-evidence-based-staleness).

Provides:
  - the monotonic session counter (.claude/learning/session-counter.json),
    incremented once per SessionEnd by observe.py;
  - config migration from date-based staleness keys to session-based keys;
  - the `confirmed` permanence check every staleness pass must apply first;
  - backfill stamping for instincts/proposals created before the session clock.

Imported as a sibling module by observe.py, analyze.py, and propose.py.
All functions fail closed: errors degrade to safe defaults, never raise
out of the public functions.
"""

import json
import os
import re
from datetime import datetime, timezone

SESSION_COUNTER_FILENAME = "session-counter.json"

# Old date-based key -> (new session-based key, default value).
# proposal_decay_sessions default 15 per the ADR decision; archive at 30
# mirrors the old 30/60 day ratio. instinct decay drops a fixed amount per
# full window of sessions stale, with one window of grace (the session
# analog of the old "0.05 per month after one month stale").
CONFIG_MIGRATION = {
    "proposal_decay_days": ("proposal_decay_sessions", 15),
    "proposal_archive_days": ("proposal_archive_sessions", 30),
    "instinct_decay_per_month": ("instinct_decay_per_sessions", 0.05),
}

DEFAULT_STALENESS = {
    "proposal_decay_sessions": 15,
    "proposal_archive_sessions": 30,
    "instinct_decay_per_sessions": 0.05,
    "instinct_decay_session_window": 15,
    "contradiction_penalty": 0.1,
}

DEFAULT_THRESHOLD_EXTRAS = {
    # Soft cap before the session-start notice nudges oldest-first review.
    "pending_proposal_soft_cap": 10,
    # Correction instincts seed above the 0.30 frequency proxy
    # (corrections ADR: real corrections are strong evidence).
    "correction_seed_confidence": 0.45,
    # Session-delta blocks accumulated before the session-start notice
    # nudges a memory curation pass (project-memory ADR debt).
    "memory_curation_nudge_blocks": 5,
}


# --- Session counter ---

def _counter_path(learning_dir):
    return os.path.join(learning_dir, SESSION_COUNTER_FILENAME)


def read_session_count(learning_dir):
    """Return the current session count, 0 if absent or unreadable."""
    path = _counter_path(learning_dir)
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = data.get("session_count", 0)
        return count if isinstance(count, int) and count >= 0 else 0
    except (json.JSONDecodeError, OSError, AttributeError):
        return 0


def increment_session_count(learning_dir):
    """Increment the counter by one and return the new count. Fail closed:
    on any error the previous (or zero) count is returned unchanged."""
    count = read_session_count(learning_dir)
    new_count = count + 1
    try:
        os.makedirs(learning_dir, exist_ok=True)
        with open(_counter_path(learning_dir), "w", encoding="utf-8") as f:
            json.dump({
                "session_count": new_count,
                "updated": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }, f, indent=2)
        return new_count
    except OSError:
        return count


# --- Config migration ---

def migrate_config_dict(config):
    """Migrate a config dict from date-based to session-based staleness keys.

    Idempotent: an already-migrated dict passes through unchanged. Returns
    (config, changed). Unknown keys are preserved; old date keys are dropped,
    not flagged off, per the ADR enforcement clause.
    """
    if not isinstance(config, dict):
        return config, False
    changed = False
    staleness = config.setdefault("staleness", {})
    for old_key, (new_key, default) in CONFIG_MIGRATION.items():
        if old_key in staleness:
            del staleness[old_key]
            changed = True
        if new_key not in staleness:
            staleness[new_key] = default
            changed = True
    for extra_key in ("instinct_decay_session_window",
                      "contradiction_penalty"):
        if extra_key not in staleness:
            staleness[extra_key] = DEFAULT_STALENESS[extra_key]
            changed = True
    thresholds = config.setdefault("thresholds", {})
    for key, default in DEFAULT_THRESHOLD_EXTRAS.items():
        if key not in thresholds:
            thresholds[key] = default
            changed = True
    return config, changed


def migrate_config_file(config_path):
    """Migrate config.json in place if it carries date-based keys.

    Returns the (possibly migrated) config dict. Never raises: an unreadable
    file yields the migrated defaults without writing."""
    config = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = {}
    config, changed = migrate_config_dict(config)
    if changed and os.path.isfile(config_path):
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                f.write("\n")
        except OSError:
            pass
    return config


# --- Permanence guarantee ---

def is_confirmed(record):
    """True if a parsed instinct/proposal dict carries the confirmed marker.

    Confirmed knowledge (applied proposals, confirmed instincts, curated
    memory entries) is structurally exempt from every staleness mechanism."""
    if not isinstance(record, dict):
        return False
    val = record.get("confirmed", False)
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() == "true"


def content_is_confirmed(content):
    """True if raw frontmatter text carries `confirmed: true`."""
    if not isinstance(content, str):
        return False
    return bool(re.search(r"^confirmed:\s*true\s*$",
                          content, re.MULTILINE | re.IGNORECASE))


# --- Backfill ---

def _insert_frontmatter_key(content, line):
    """Insert a key line at the end of the first frontmatter block."""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return f"---{parts[1].rstrip()}\n{line}\n---{parts[2]}"


def backfill_session_fields(learning_dir, current_session):
    """Stamp pre-session-clock artifacts so nothing decays retroactively.

    Instincts missing `last_seen_session` and proposals missing
    `created_session` get the current count. Idempotent; returns the number
    of files stamped."""
    stamped = 0
    instincts_dir = os.path.join(learning_dir, "instincts")
    proposals_dir = os.path.join(learning_dir, "proposals")
    targets = (
        (instincts_dir, ".yaml", "last_seen_session"),
        (proposals_dir, ".md", "created_session"),
    )
    for directory, suffix, key in targets:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if not fname.endswith(suffix):
                continue
            path = os.path.join(directory, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if re.search(rf"^{key}:", content, re.MULTILINE):
                    continue
                updated = _insert_frontmatter_key(
                    content, f"{key}: {current_session}"
                )
                if updated != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(updated)
                    stamped += 1
            except OSError:
                continue
    return stamped
