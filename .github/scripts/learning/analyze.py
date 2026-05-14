#!/usr/bin/env python3
"""
analyze.py
Pattern detection engine for continuous learning.
Reads .claude/learning/observations.jsonl, detects patterns, creates/updates
instinct YAML files in .claude/learning/instincts/.

Detectors:
  1. Correction patterns — user rejects then redoes differently
  2. Repeated sequences — same tool call sequences across sessions
  3. Error recovery — failure followed by resolution pattern
  4. File conventions — consistent file placement and naming

Run from repo root: python .github/scripts/analyze.py
Called automatically by observe.py on Stop when threshold met.
"""

import json
import os
import re
import subprocess
import sys
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

# --- Paths ---

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
LEARNING_DIR = os.path.join(PROJECT_DIR, ".claude", "learning")
OBS_FILE = os.path.join(LEARNING_DIR, "observations.jsonl")
INSTINCTS_DIR = os.path.join(LEARNING_DIR, "instincts")
CONFIG_FILE = os.path.join(LEARNING_DIR, "config.json")

# --- Config ---

def load_config():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"thresholds": {}, "staleness": {}}


# --- Observation loading ---

def load_observations():
    """Load all observations from JSONL."""
    obs = []
    if not os.path.isfile(OBS_FILE):
        return obs
    with open(OBS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("event") != "_analysis_marker":
                    obs.append(rec)
            except json.JSONDecodeError:
                continue
    return obs


# --- Instinct I/O ---

def instinct_id(text):
    """Generate a stable ID from a description string."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > 50:
        slug = slug[:50]
    return slug


def load_instinct(instinct_file):
    """Load an existing instinct YAML (simplified key:value format)."""
    data = {}
    if not os.path.isfile(instinct_file):
        return data
    with open(instinct_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Parse frontmatter
    parts = content.split("---", 2)
    if len(parts) >= 3:
        for line in parts[1].strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"')
                if key == "confidence":
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                elif key == "evidence_count":
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                data[key] = val
        data["body"] = parts[2].strip()
    return data


def save_instinct(iid, trigger, action, confidence, domain, evidence,
                  file_scope="**", evidence_count=1):
    """Save an instinct YAML file."""
    os.makedirs(INSTINCTS_DIR, exist_ok=True)
    path = os.path.join(INSTINCTS_DIR, f"{iid}.yaml")

    # If exists, merge — increase confidence, append evidence
    existing = load_instinct(path)
    if existing:
        old_conf = existing.get("confidence", 0.3)
        old_count = existing.get("evidence_count", 1)
        # Reinforcement: +0.1 per new observation, capped at 0.9
        new_count = old_count + evidence_count
        new_conf = min(0.9, old_conf + (evidence_count * 0.1))
        confidence = new_conf
        evidence_count = new_count

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = f"""---
id: {iid}
trigger: "{trigger}"
confidence: {confidence:.2f}
domain: {domain}
file_scope: "{file_scope}"
evidence_count: {evidence_count}
last_seen: "{now}"
---

# {action}

## Evidence
{evidence}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# --- Detector 1: Correction Patterns ---

def detect_corrections(observations):
    """
    Find sequences where a PreToolUse is followed by the same tool
    targeting the same file within 60 seconds — suggests user corrected.
    """
    instincts = []
    pre_events = [o for o in observations if o.get("event") == "PreToolUse"]

    # Group by session + tool + target file
    groups = defaultdict(list)
    for o in pre_events:
        key = (o.get("session_id", ""), o.get("tool", ""), o.get("file_ext", ""))
        groups[key].append(o)

    for key, events in groups.items():
        if len(events) < 2:
            continue
        session_id, tool, file_ext = key
        # Multiple PreToolUse for same tool+ext in same session = potential correction
        summaries = [e.get("input_summary", "") for e in events]
        unique_summaries = set(summaries)
        if len(unique_summaries) > 1 and len(events) >= 3:
            instincts.append({
                "trigger": f"when using {tool} on {file_ext or 'files'}",
                "action": f"Consistent {tool} pattern on {file_ext or 'files'} — "
                          f"user corrected approach {len(events)} times",
                "confidence": 0.3,
                "domain": events[0].get("domain_hint", "workflow"),
                "file_scope": f"**/*{file_ext}" if file_ext else "**",
                "evidence": f"- {len(events)} corrections in session {session_id[:8]}",
                "evidence_count": len(events) - 1,
            })

    return instincts


# --- Detector 2: Repeated Sequences ---

def detect_repeated_sequences(observations):
    """
    Find tool call sequences (3+ tools) that appear in multiple sessions.
    """
    instincts = []

    # Build per-session tool sequences
    sessions = defaultdict(list)
    for o in observations:
        if o.get("tool"):
            sessions[o.get("session_id", "unknown")].append(o.get("tool"))

    # Extract 3-grams from each session
    ngram_sessions = defaultdict(set)
    for sid, tools in sessions.items():
        if len(tools) < 3:
            continue
        for i in range(len(tools) - 2):
            trigram = tuple(tools[i:i+3])
            ngram_sessions[trigram].add(sid)

    # Sequences appearing in 2+ sessions
    for trigram, sids in ngram_sessions.items():
        if len(sids) >= 2:
            seq_str = " -> ".join(trigram)
            instincts.append({
                "trigger": f"when starting a {trigram[0]} workflow",
                "action": f"Follow sequence: {seq_str}",
                "confidence": min(0.3 + (len(sids) * 0.1), 0.7),
                "domain": "workflow",
                "file_scope": "**",
                "evidence": f"- Sequence seen in {len(sids)} sessions",
                "evidence_count": len(sids),
            })

    return instincts


# --- Detector 3: Error Recovery ---

def detect_error_recovery(observations):
    """
    Find PostToolUse failures followed by a successful resolution pattern.
    """
    instincts = []

    # Group by session
    sessions = defaultdict(list)
    for o in observations:
        sessions[o.get("session_id", "unknown")].append(o)

    for sid, events in sessions.items():
        for i, o in enumerate(events):
            if o.get("outcome") != "failure":
                continue
            failed_tool = o.get("tool", "")
            # Look ahead for the resolution (next 5 events)
            resolution = None
            for j in range(i+1, min(i+6, len(events))):
                next_ev = events[j]
                if next_ev.get("outcome") == "success" and next_ev.get("tool"):
                    resolution = next_ev
                    break

            if resolution:
                instincts.append({
                    "trigger": f"when {failed_tool} fails",
                    "action": f"Recover with {resolution.get('tool', 'unknown')}: "
                              f"{resolution.get('input_summary', '')[:80]}",
                    "confidence": 0.3,
                    "domain": "error-handling",
                    "file_scope": "**",
                    "evidence": f"- Recovery pattern in session {sid[:8]}: "
                                f"{failed_tool} failure -> {resolution.get('tool')} success",
                    "evidence_count": 1,
                })

    return instincts


# --- Detector 4: File Conventions ---

def detect_file_conventions(observations):
    """
    Detect consistent file placement patterns from tool inputs.
    """
    instincts = []

    # Collect file paths from all observations
    dir_counts = Counter()
    ext_dir = defaultdict(Counter)

    for o in observations:
        summary = o.get("input_summary", "")
        if not summary or "/" not in summary:
            continue
        # Extract directory from path-like summaries
        if "." in summary.split("/")[-1]:  # Looks like a file path
            directory = "/".join(summary.split("/")[:-1])
            ext = o.get("file_ext", "")
            if directory and ext:
                ext_dir[ext][directory] += 1
                dir_counts[directory] += 1

    # Patterns where 80%+ of an extension goes to one directory
    for ext, dirs in ext_dir.items():
        total = sum(dirs.values())
        if total < 3:
            continue
        top_dir, top_count = dirs.most_common(1)[0]
        ratio = top_count / total
        if ratio >= 0.8:
            instincts.append({
                "trigger": f"when creating {ext} files",
                "action": f"Place {ext} files in {top_dir}/",
                "confidence": min(0.3 + (ratio * 0.4), 0.7),
                "domain": "code-style",
                "file_scope": f"**/*{ext}",
                "evidence": f"- {top_count}/{total} ({ratio:.0%}) of {ext} files "
                            f"placed in {top_dir}/",
                "evidence_count": top_count,
            })

    return instincts


# --- Main ---

def main():
    observations = load_observations()
    if not observations:
        print("[analyze] No observations to analyze.", file=sys.stderr)
        sys.exit(0)

    print(f"[analyze] Analyzing {len(observations)} observations...", file=sys.stderr)

    # Run all detectors
    all_instincts = []
    all_instincts.extend(detect_corrections(observations))
    all_instincts.extend(detect_repeated_sequences(observations))
    all_instincts.extend(detect_error_recovery(observations))
    all_instincts.extend(detect_file_conventions(observations))

    if not all_instincts:
        print("[analyze] No patterns detected yet.", file=sys.stderr)
    else:
        # Deduplicate by generating IDs
        seen_ids = set()
        saved = 0
        for inst in all_instincts:
            iid = instinct_id(inst["action"])
            if iid in seen_ids:
                continue
            seen_ids.add(iid)
            save_instinct(
                iid=iid,
                trigger=inst["trigger"],
                action=inst["action"],
                confidence=inst["confidence"],
                domain=inst["domain"],
                file_scope=inst.get("file_scope", "**"),
                evidence=inst["evidence"],
                evidence_count=inst.get("evidence_count", 1),
            )
            saved += 1
        print(f"[analyze] Created/updated {saved} instincts.", file=sys.stderr)

    # Write analysis marker so observe.py can reset its count
    os.makedirs(LEARNING_DIR, exist_ok=True)
    with open(OBS_FILE, "a", encoding="utf-8") as f:
        marker = json.dumps({
            "event": "_analysis_marker",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }, separators=(",", ":"))
        f.write(marker + "\n")

    # Invoke propose.py to check for promotion-ready instincts
    propose_script = os.path.join(
        PROJECT_DIR, ".github", "scripts", "learning", "propose.py"
    )
    if os.path.isfile(propose_script):
        try:
            subprocess.Popen(
                [sys.executable, propose_script],
                cwd=PROJECT_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass  # Never block on proposal failures

    sys.exit(0)


if __name__ == "__main__":
    main()
