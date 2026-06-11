#!/usr/bin/env python3
"""
analyze.py
Pattern detection engine for continuous learning.
Reads .claude/learning/observations.jsonl, detects patterns, creates/updates
instinct YAML files in .claude/learning/instincts/.

Detectors:
  1. Correction patterns: user rejects then redoes differently
  2. Repeated sequences: same tool call sequences across sessions
  3. Error recovery: failure followed by resolution pattern
  4. File conventions: consistent file placement and naming
  5. Rule consultation: instruction files never consulted for in-scope edits
  6. Guide consultation: companion guides not read when rules are consulted

A relevance pass archives instincts whose file_scope matches no real file
(reason: irrelevant), per the evidence-based staleness ADR.

Run from repo root: python .github/scripts/learning/analyze.py
Called automatically by observe.py on Stop when threshold met.

Flags:
  --dry-run   Run detectors and print results without writing files or
              invoking propose.py.
"""

import argparse
import glob as glob_module
import json
import os
import re
import shutil
import subprocess
import sys
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

import session_clock

# --- Paths ---

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
LEARNING_DIR = os.path.join(PROJECT_DIR, ".claude", "learning")
OBS_FILE = os.path.join(LEARNING_DIR, "observations.jsonl")
INSTINCTS_DIR = os.path.join(LEARNING_DIR, "instincts")
INSTINCTS_ARCHIVE_DIR = os.path.join(LEARNING_DIR, "instincts.archive")
PROPOSALS_DIR = os.path.join(LEARNING_DIR, "proposals")
CONFIG_FILE = os.path.join(LEARNING_DIR, "config.json")
INSTRUCTIONS_DIR = os.path.join(PROJECT_DIR, ".github", "instructions")
RULES_DIR = os.path.join(PROJECT_DIR, ".claude", "rules")

# --- Config ---

def load_config():
    """Load config.json, migrating date-based staleness keys in place."""
    return session_clock.migrate_config_file(CONFIG_FILE)


# --- Observation loading ---

def load_observations(incremental=True):
    """Load observations from JSONL.

    When incremental=True (default), only returns observations recorded after
    the most recent analysis marker. This avoids re-processing the entire
    history on every run. Pass incremental=False for a full scan.
    """
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
                if rec.get("event") == "_analysis_marker":
                    if incremental:
                        obs.clear()  # reset: only keep post-marker entries
                    continue
                obs.append(rec)
            except json.JSONDecodeError:
                continue
    return obs


def tool_events(observations):
    """Tool observations every detector must count from.

    Recording is PostToolUse-only (one observation per tool call, outcome
    included). The filter stays as a structural guard: if a PreToolUse hook
    is ever re-registered, detectors keep counting one event per call
    instead of silently doubling their evidence (the B1 failure mode --
    two detectors filtered, two did not, and counts inflated 2x)."""
    return [
        o for o in observations
        if o.get("event") == "PostToolUse" and o.get("tool")
    ]


# --- Instinct I/O ---

def instinct_id(text):
    """Generate a stable ID from a description string."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > 50:
        short_hash = hashlib.sha1(text.encode()).hexdigest()[:8]
        slug = f"{slug[:50]}-{short_hash}"
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
                elif key in ("evidence_count", "last_seen_session"):
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                data[key] = val
        data["body"] = parts[2].strip()
    return data


def _evidence_lines(body):
    """Evidence bullet lines from an instinct body, oldest first."""
    if "## Evidence" not in body:
        return []
    tail = body.split("## Evidence", 1)[1]
    return [ln for ln in tail.split("\n") if ln.strip().startswith("-")]


def reinforce_proposal(iid, current_session):
    """Stamp reinforced_session on a live proposal whose instinct was just
    reinforced, reviving a stale one to pending.

    propose.py measures proposal staleness from this stamp (falling back to
    created_session), so a proposal whose instinct keeps gathering evidence
    neither goes stale nor archives (B4/F4). Fails closed: any error leaves
    the proposal untouched."""
    path = os.path.join(PROPOSALS_DIR, f"{iid}.md")
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        status = re.search(r'status:\s*(\w+)', content)
        if not status or status.group(1) not in ("pending", "stale"):
            return
        if re.search(r"^reinforced_session:", content, re.MULTILINE):
            content = re.sub(
                r"^(reinforced_session:\s*)\d+",
                rf"\g<1>{current_session}",
                content, flags=re.MULTILINE
            )
        else:
            parts = content.split("---", 2)
            if len(parts) < 3:
                return
            content = (
                f"---{parts[1].rstrip()}\n"
                f"reinforced_session: {current_session}\n---{parts[2]}"
            )
        if status.group(1) == "stale":
            content = content.replace("status: stale", "status: pending", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError:
        pass


# Most recent evidence entries kept per instinct. Merging is additive (B2):
# prior entries survive reinforcement instead of being rebuilt from the new
# batch alone, capped so instinct files stay bounded.
EVIDENCE_CAP = 10

# Flat confidence bump applied each time an instinct is reinforced by a new
# analysis run. It is intentionally NOT scaled by the batch's evidence_count:
# a detector that emits one instinct backed by eight events would otherwise add
# 0.8 in a single merge, vaulting noise straight past the promotion threshold
# on first sight. One reinforcement, one increment.
MERGE_CONFIDENCE_INCREMENT = 0.1


def save_instinct(iid, trigger, action, confidence, domain, evidence,
                  file_scope="**", evidence_count=1, provenance="frequency"):
    """Save an instinct YAML file.

    Every instinct carries provenance: `user-correction` (transcript parse),
    `developer-flagged` (explicit marker), `self-correction` (failed-retry
    burst), or `frequency` (repetition proxies). The corrections ADR
    requires these never be conflated; an existing instinct's provenance
    survives merges."""
    os.makedirs(INSTINCTS_DIR, exist_ok=True)
    path = os.path.join(INSTINCTS_DIR, f"{iid}.yaml")

    # If exists, merge: increase confidence, append evidence
    existing = load_instinct(path)
    confirmed = session_clock.is_confirmed(existing)
    if existing and existing.get("provenance"):
        provenance = existing["provenance"]
    if existing:
        old_conf = existing.get("confidence", 0.3)
        old_count = existing.get("evidence_count", 1)
        # evidence_count still accumulates the supporting-observation total,
        # but confidence rises by a flat increment per merge (see constant).
        new_count = old_count + evidence_count
        new_conf = min(0.9, old_conf + MERGE_CONFIDENCE_INCREMENT)
        confidence = new_conf
        evidence_count = new_count
        # Append, do not replace (B2): prior evidence survives the merge so
        # a long-lived instinct shows its history at review time, capped to
        # the most recent EVIDENCE_CAP entries. Duplicates of lines already
        # present are dropped.
        old_lines = _evidence_lines(existing.get("body", ""))
        new_lines = [ln for ln in evidence.split("\n") if ln.strip()]
        combined = old_lines + [ln for ln in new_lines
                                if ln not in old_lines]
        evidence = "\n".join(combined[-EVIDENCE_CAP:])
        # The instinct was reinforced: keep its pending proposal alive (B4).
        reinforce_proposal(
            iid, session_clock.read_session_count(LEARNING_DIR)
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Reinforcement resets the session clock: last_seen_session is the
    # session count at the most recent save or merge.
    current_session = session_clock.read_session_count(LEARNING_DIR)
    safe_trigger = trigger.replace('"', '\\"')
    safe_scope = file_scope.replace('"', '\\"')
    safe_evidence = evidence.replace("---", "- - -")
    # The confirmed marker survives merges: a developer's decision is never
    # dropped by a pipeline rewrite (permanence guarantee).
    # decay_charged_windows is deliberately NOT carried through: the rewrite
    # resets last_seen_session, so the decay charge (propose.py, B3) starts
    # over with the fresh clock.
    confirmed_line = "confirmed: true\n" if confirmed else ""
    content = f"""---
id: {iid}
trigger: "{safe_trigger}"
confidence: {confidence:.2f}
domain: {domain}
file_scope: "{safe_scope}"
evidence_count: {evidence_count}
provenance: {provenance}
last_seen: "{now}"
last_seen_session: {current_session}
{confirmed_line}---

# {action}

## Evidence
{safe_evidence}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# --- Relevance check (evidence-based staleness ADR) ---

def scope_matches_anything(file_scope):
    """True if an instinct's file_scope glob matches at least one real file.

    Matches under .git/ and .claude/learning/ do not count: the pipeline's
    own data must not keep its instincts alive (self-observation rule)."""
    if not file_scope or file_scope == "**":
        return True  # universal scope is trivially relevant
    pattern = os.path.join(PROJECT_DIR, file_scope)
    try:
        for match in glob_module.iglob(pattern, recursive=True):
            norm = match.replace("\\", "/")
            if "/.git/" in norm or "/.claude/learning/" in norm:
                continue
            if os.path.isfile(match):
                return True
    except (OSError, ValueError):
        return True  # fail open: never archive on a glob error
    return False


def relevance_pass(dry_run=False):
    """Archive instincts whose target scope no longer matches any file.

    Reason recorded as `irrelevant`, distinct from `decayed` and `rejected`,
    so the archive stays auditable. Confirmed instincts are exempt."""
    if not os.path.isdir(INSTINCTS_DIR):
        return 0
    archived = 0
    current_session = session_clock.read_session_count(LEARNING_DIR)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fname in sorted(os.listdir(INSTINCTS_DIR)):
        if not fname.endswith(".yaml"):
            continue
        path = os.path.join(INSTINCTS_DIR, fname)
        inst = load_instinct(path)
        if not inst or session_clock.is_confirmed(inst):
            continue
        scope = inst.get("file_scope", "**")
        if scope_matches_anything(scope):
            continue
        tag = "[dry-run][irrelevant]" if dry_run else "[irrelevant]"
        if not dry_run:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = (
                        f"archived_reason: irrelevant\n"
                        f"archived_session: {current_session}\n"
                        f'archived: "{today}"'
                    )
                    content = f"---{parts[1].rstrip()}\n{meta}\n---{parts[2]}"
                os.makedirs(INSTINCTS_ARCHIVE_DIR, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                shutil.move(
                    path, os.path.join(INSTINCTS_ARCHIVE_DIR, fname)
                )
            except OSError:
                continue
        archived += 1
        print(
            f"  {tag} {fname}: scope '{scope}' matches no files, archived",
            file=sys.stderr
        )
    return archived


# --- Contradiction reducer (evidence-based staleness ADR) ---

# Provenance weighting: a real user correction is stronger evidence against
# an instinct than the agent's own failed-and-retried edit. The explicit
# developer marker is the highest-precision signal and weighs the same as
# a parsed user correction.
CONTRADICTION_WEIGHTS = {
    "user-correction": 1.0,
    "developer-flagged": 1.0,
    "self-correction": 0.5,
}


def update_instinct_confidence(path, new_confidence):
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


def correction_contradicts_scope(target, file_scope):
    """Match rule: a correction whose target falls inside an instinct's
    scope is evidence against that instinct."""
    if not target or not file_scope or file_scope == "**":
        return False
    from fnmatch import fnmatch
    norm = target.replace("\\", "/")
    if fnmatch(norm, file_scope):
        return True
    # A root-level target misses "**/*.ext" patterns; match the basename
    # against the scope's final segment as a fallback.
    return fnmatch(os.path.basename(norm), file_scope.split("/")[-1])


def contradiction_pass(observations, config, dry_run=False):
    """Reduce confidence of instincts contradicted by correction evidence.

    Confidence falls only on evidence (the ADR's second rule): each
    `correction` observation whose target matches an instinct's scope
    reduces that instinct's confidence by the configured penalty, weighted
    by provenance. Confirmed instincts are exempt; a contradicted confirmed
    instinct surfaces as a review nudge instead, because unconfirming is
    the developer's call. Returns the number of instincts reduced."""
    corrections = [
        o for o in observations if o.get("event") == "correction"
    ]
    if not corrections or not os.path.isdir(INSTINCTS_DIR):
        return 0
    penalty = config.get("staleness", {}).get("contradiction_penalty", 0.1)
    reduced = 0
    for fname in sorted(os.listdir(INSTINCTS_DIR)):
        if not fname.endswith(".yaml"):
            continue
        path = os.path.join(INSTINCTS_DIR, fname)
        inst = load_instinct(path)
        if not inst:
            continue
        # A correction corroborates correction-derived instincts; it only
        # contradicts patterns inferred from other signals. Without this,
        # a correction instinct would be reduced by its own evidence.
        if inst.get("provenance") in ("user-correction", "developer-flagged"):
            continue
        scope = inst.get("file_scope", "**")
        weight_sum = sum(
            CONTRADICTION_WEIGHTS.get(c.get("provenance", ""), 0.5)
            for c in corrections
            if correction_contradicts_scope(c.get("target", ""), scope)
        )
        if weight_sum <= 0:
            continue
        if session_clock.is_confirmed(inst):
            print(
                f"  [contradicted-confirmed] {fname}: correction evidence "
                f"against a confirmed instinct; review via the "
                f"continuous-learning skill",
                file=sys.stderr
            )
            continue
        old_conf = inst.get("confidence", 0.0)
        new_conf = max(0.1, round(old_conf - penalty * weight_sum, 2))
        if new_conf == old_conf:
            continue
        tag = "[dry-run][contradiction]" if dry_run else "[contradiction]"
        if not dry_run:
            update_instinct_confidence(path, new_conf)
        print(
            f"  {tag} {fname}: {old_conf:.2f} -> {new_conf:.2f} "
            f"({len(corrections)} correction(s), weight {weight_sum:.1f})",
            file=sys.stderr
        )
        reduced += 1
    return reduced


# --- Detector 0: User Corrections (transcript-parse signal) ---

def detect_user_corrections(observations, seed_confidence=0.45):
    """Aggregate `correction` observations into instincts.

    A real user correction is strong evidence, so these seed above the 0.30
    proxy (corrections ADR). Grouped by target and trigger-phrase category
    so the instinct ID is stable across runs; the evidence lists the derived
    change descriptions for the developer to review."""
    instincts = []
    groups = defaultdict(list)
    for o in observations:
        if o.get("event") != "correction":
            continue
        if o.get("provenance") not in ("user-correction",
                                       "developer-flagged"):
            continue
        groups[(o.get("target", "general"),
                o.get("category", "unknown"))].append(o)

    for (target, category), events in groups.items():
        ext = events[0].get("file_ext", "")
        tool = events[0].get("tool", "")
        changes = sorted({e.get("change", "") for e in events if e.get("change")})
        evidence = "\n".join(f"- {c}" for c in changes) or "- (no description)"
        instincts.append({
            "trigger": f"when running {tool} on {target}" if tool
                       else f"when working on {target}",
            "action": f"User {category} corrections on {target}: "
                      f"codify the corrected convention",
            "confidence": seed_confidence,
            "domain": events[0].get("domain_hint", "code-style") or "code-style",
            "file_scope": f"**/*{ext}" if ext else "**",
            "evidence": evidence,
            "evidence_count": len(events),
            "provenance": events[0].get("provenance", "user-correction"),
        })

    return instincts


# --- Detector 1: Correction Patterns (agent self-correction proxy) ---

# Only mutating tools can represent a correction: you cannot "correct" by
# reading or searching. Restricting to these removes the false positives that
# came from repeated Read/Glob/Bash calls in a single session.
MUTATING_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


def _parse_ts(ts):
    """Parse an observation timestamp, returning None if absent or malformed.

    Accepts the canonical "%Y-%m-%dT%H:%M:%SZ" form observe.py writes, plus
    any ISO-8601 variant with an explicit UTC offset, so a line written with
    "+00:00" does not silently drop from correction grouping. Naive values
    are assumed UTC; everything is normalized to UTC for window comparison.
    """
    if not isinstance(ts, str) or not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def detect_corrections(observations, window_seconds=60, min_attempts=3):
    """
    Detect self-correction bursts: the same file edited min_attempts+ times in
    rapid succession (consecutive touches no more than window_seconds apart)
    where at least one attempt FAILED. The failure is the discriminator that
    separates a genuine correction from ordinary iterative editing -- normal
    editing has no failed attempts, so it no longer registers. Restricted to
    mutating tools and grouped by the actual file, honoring the detector's
    contract (same file, tight time window).

    This is still a proxy. A user rejecting a *successful* edit leaves no
    failure in the stream, so that case is not captured here; capturing real
    user-rejection signals is the P3 redesign (see the redesign plan).
    Confidence is seeded low and the action label carries no volatile count, so
    a single burst cannot self-promote and a changing count cannot spawn
    duplicate instincts.
    """
    instincts = []
    # Tool events carry both the file path and the success/failure outcome.
    post_events = [
        o for o in tool_events(observations)
        if o.get("tool") in MUTATING_TOOLS
        and o.get("file_ext")
        and o.get("input_summary")
    ]

    # Group by session + tool + actual file path (not just the extension).
    groups = defaultdict(list)
    for o in post_events:
        key = (o.get("session_id", ""), o.get("tool", ""), o.get("input_summary", ""))
        groups[key].append(o)

    for (session_id, tool, _file_path), events in groups.items():
        if len(events) < min_attempts:
            continue
        events = sorted(
            events,
            key=lambda e: _parse_ts(e.get("ts", ""))
            or datetime.max.replace(tzinfo=timezone.utc),
        )
        # Find the longest burst of consecutive edits within the time window.
        best, current = [], [events[0]]
        for prev, cur in zip(events, events[1:]):
            tp, tc = _parse_ts(prev.get("ts", "")), _parse_ts(cur.get("ts", ""))
            if tp and tc and (tc - tp).total_seconds() <= window_seconds:
                current.append(cur)
            else:
                if len(current) > len(best):
                    best = current
                current = [cur]
        if len(current) > len(best):
            best = current

        failures = sum(1 for e in best if e.get("outcome") == "failure")
        if len(best) < min_attempts or failures < 1:
            continue

        file_ext = events[0].get("file_ext", "")
        instincts.append({
            "trigger": f"when edits to the same {file_ext} file keep failing",
            "action": f"Repeated failed {tool} edits to the same {file_ext} file in "
                      f"one session may signal a missing convention or unclear guidance",
            "confidence": 0.3,
            "domain": events[0].get("domain_hint", "code-style"),
            "file_scope": f"**/*{file_ext}" if file_ext else "**",
            "evidence": f"- burst of {len(best)} {tool} edits to one {file_ext} file "
                        f"({failures} failed) within {window_seconds}s in "
                        f"session {session_id[:8]}",
            "evidence_count": 1,
            "provenance": "self-correction",
        })

    return instincts


# --- Detector 2: Repeated Sequences ---

def detect_repeated_sequences(observations):
    """
    Find tool call sequences (3+ tools) that appear in multiple sessions.

    Homogeneous trigrams (the same tool three times, e.g. Edit -> Edit -> Edit
    or PowerShell x3) are not workflows -- they are ordinary iterative work --
    so they are dropped. A sequence must also recur across at least
    MIN_SESSIONS distinct sessions to register, raising the bar above the noise
    a single session's repetition produced.
    """
    instincts = []
    MIN_SESSIONS = 3

    # Build per-session tool sequences from tool events (one per call).
    sessions = defaultdict(list)
    for o in tool_events(observations):
        sessions[o.get("session_id", "unknown")].append(o.get("tool"))

    # Extract 3-grams from each session, skipping homogeneous ones
    ngram_sessions = defaultdict(set)
    for sid, tools in sessions.items():
        if len(tools) < 3:
            continue
        for i in range(len(tools) - 2):
            trigram = tuple(tools[i:i+3])
            if len(set(trigram)) < 2:
                continue  # all the same tool: iteration, not a workflow
            ngram_sessions[trigram].add(sid)

    # Sequences appearing in MIN_SESSIONS+ sessions
    for trigram, sids in ngram_sessions.items():
        if len(sids) >= MIN_SESSIONS:
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

    # Group by session, tool events only: a lookahead window over a stream
    # with non-tool records in it would measure the wrong distance.
    sessions = defaultdict(list)
    for o in tool_events(observations):
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

def repo_relative_dir(path):
    """Return the repo-relative POSIX directory of a file-path summary.

    input_summary holds an absolute path with forward slashes (observe.py
    normalizes separators). A placement convention is only useful if it is
    portable, so this:
      - drops paths outside the project root (e.g. an Obsidian vault on the
        same machine), which are not conventions of this repo,
      - strips the project-root prefix to a relative path,
      - drops files that sit at the repo root (no directory convention).
    Returns None in those cases, otherwise the relative directory.
    """
    if not path or "/" not in path:
        return None
    norm = path.replace("\\", "/")
    root = PROJECT_DIR.replace("\\", "/").rstrip("/")
    if not norm.startswith(root + "/"):
        return None  # outside the project root -- not a portable convention
    rel = norm[len(root) + 1:]
    if "/" not in rel:
        return None  # file at repo root, no meaningful directory
    return "/".join(rel.split("/")[:-1])


def detect_file_conventions(observations):
    """
    Detect consistent file placement patterns from tool inputs.

    Paths are normalized to repo-relative form so the resulting rules are
    portable; non-portable (out-of-repo, absolute) paths and pipeline-internal
    directories are dropped rather than promoted as conventions.
    """
    instincts = []

    # Collect file paths from tool events (one per call; B1 fix)
    dir_counts = Counter()
    ext_dir = defaultdict(Counter)

    for o in tool_events(observations):
        ext = o.get("file_ext", "")
        if not ext:
            continue
        directory = repo_relative_dir(o.get("input_summary", ""))
        if directory is None:
            continue
        if directory.startswith(".claude/learning"):
            continue  # pipeline-internal churn, not a real convention
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


# --- Detector 5: Rule Consultation Patterns ---

def detect_rule_consultation(observations):
    """
    Find instruction files that are in scope for edited file types but were
    never consulted during those sessions. A rule file that no one reads
    despite active edits in its scope may be poorly discoverable or irrelevant.
    """
    instincts = []

    # Count consultations and edits from tool events (one per call; B1 fix)
    events = tool_events(observations)
    rule_consult_counts = Counter()
    for o in events:
        rule = o.get("rule_consulted")
        if rule:
            rule_consult_counts[rule] += 1

    # Count edits per file extension
    ext_edit_counts = Counter()
    for o in events:
        if o.get("tool") in ("Edit", "Write") and o.get("file_ext"):
            ext_edit_counts[o["file_ext"]] += 1

    # Build a mapping of instruction files to their extension scopes.
    # Convention: files named {language}-code-standards.instructions.md scope
    # to that language extension. Generic instruction files (no language prefix)
    # are scoped to all files and are excluded from this detector.
    rule_ext_scope = {}
    ext_map = {
        "python": ".py", "py": ".py",
        "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts",
        "csharp": ".cs", "cs": ".cs",
        "cpp": ".cpp", "c++": ".cpp",
        "c": ".c",
        "java": ".java",
        "ruby": ".rb", "rb": ".rb",
        "go": ".go",
        "rust": ".rs", "rs": ".rs",
        "lua": ".lua",
        "swift": ".swift",
        "kotlin": ".kt", "kt": ".kt",
    }

    for rule_file in rule_consult_counts:
        basename = os.path.basename(rule_file).lower()
        for lang, ext in ext_map.items():
            if basename.startswith(f"{lang}-"):
                rule_ext_scope[rule_file] = ext
                break

    # Discover rule files from the filesystem (both source and mirror)
    all_rule_files = set(rule_consult_counts.keys())
    for search_dir in (INSTRUCTIONS_DIR, RULES_DIR):
        if os.path.isdir(search_dir):
            for fname in os.listdir(search_dir):
                if fname.endswith((".instructions.md", ".md")):
                    all_rule_files.add(fname)
                    basename = fname.lower()
                    for lang, ext in ext_map.items():
                        if basename.startswith(f"{lang}-"):
                            rule_ext_scope[fname] = ext
                            break

    for rule_file in all_rule_files:
        ext = rule_ext_scope.get(rule_file)
        if not ext:
            continue
        edit_count = ext_edit_counts.get(ext, 0)
        if edit_count == 0:
            continue
        consult_count = rule_consult_counts.get(rule_file, 0)
        if consult_count == 0:
            instincts.append({
                "trigger": f"when editing {ext} files",
                "action": f"{rule_file} rarely consulted despite "
                          f"{edit_count} edits in scope",
                "confidence": 0.3,
                "domain": "meta",
                "file_scope": "**",
                "evidence": f"- {edit_count} edits on {ext} files, "
                            f"0 consultations of {rule_file}",
                "evidence_count": edit_count,
            })

    return instincts


# --- Detector 6: Guide Consultation Patterns ---

RULE_GUIDE_PAIRS = {
    "writing-voice.instructions.md": "writing-voice-guide.md",
    "writing-voice.md": "writing-voice-guide.md",
    "agent-guardrails.instructions.md": "agent-guardrails-guide.md",
    "agent-guardrails.md": "agent-guardrails-guide.md",
    "testing.instructions.md": "testing-guide.md",
    "testing.md": "testing-guide.md",
    "pr-review.instructions.md": "pr-review-guide.md",
    "pr-review.md": "pr-review-guide.md",
}


def detect_guide_consultation(observations):
    """
    Find sessions where a rule with a companion guide was consulted but the
    guide itself was never read. Agents should read the deep-doc guide when
    actively applying rules that have one.
    """
    instincts = []

    sessions = defaultdict(lambda: {"rules": set(), "guides": set()})
    for o in tool_events(observations):
        sid = o.get("session_id", "")
        if not sid:
            continue
        rule = o.get("rule_consulted")
        if rule:
            sessions[sid]["rules"].add(rule)
        guide = o.get("guide_consulted")
        if guide:
            sessions[sid]["guides"].add(guide)

    guide_miss_counts = Counter()
    guide_total_counts = Counter()

    for sid, data in sessions.items():
        for rule_file in data["rules"]:
            expected_guide = RULE_GUIDE_PAIRS.get(rule_file)
            if not expected_guide:
                continue
            guide_total_counts[rule_file] += 1
            if expected_guide not in data["guides"]:
                guide_miss_counts[rule_file] += 1

    for rule_file, total in guide_total_counts.items():
        if total < 2:
            continue
        miss = guide_miss_counts.get(rule_file, 0)
        miss_ratio = miss / total
        if miss_ratio > 0.7:
            expected_guide = RULE_GUIDE_PAIRS[rule_file]
            instincts.append({
                "trigger": f"when consulting {rule_file}",
                "action": f"Also read companion guide {expected_guide}",
                "confidence": min(0.3 + (miss_ratio * 0.3), 0.6),
                "domain": "meta",
                "file_scope": "**",
                "evidence": f"- {miss}/{total} sessions consulted rule "
                            f"without reading guide",
                "evidence_count": total,
            })

    return instincts


# --- Analysis marker ---

def write_analysis_marker():
    """Append the analysis marker under the observation-log lock.

    The marker is a log record like any other; a plain append could
    interleave bytes with a concurrent session's locked writer, and a
    SessionStart rotation could discard it mid-swap (B5). observe.py's
    locked_append and the in-place rotation share one lock, so the marker
    lands whole, before or after a rotation but never inside one. Falls
    back to a plain append if the sibling import fails; degraded
    serialization beats a lost marker."""
    os.makedirs(LEARNING_DIR, exist_ok=True)
    marker = json.dumps({
        "event": "_analysis_marker",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }, separators=(",", ":")) + "\n"
    try:
        import observe
        observe.locked_append(OBS_FILE, marker)
    except (ImportError, OSError):
        try:
            with open(OBS_FILE, "a", encoding="utf-8") as f:
                f.write(marker)
        except OSError:
            pass  # fail closed: never block analysis on the marker


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Pattern detection engine for continuous learning."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run detectors and print results without writing files or "
             "invoking propose.py.",
    )
    args = parser.parse_args()

    # Migrate config (date-based -> session-based keys) and stamp any
    # pre-clock artifacts before staleness logic touches them.
    config = load_config()
    if not args.dry_run:
        session_clock.backfill_session_fields(
            LEARNING_DIR, session_clock.read_session_count(LEARNING_DIR)
        )

    # Relevance pass: instincts whose scope matches nothing archive with
    # reason `irrelevant`. Runs independently of observation volume.
    relevance_pass(dry_run=args.dry_run)

    observations = load_observations()
    if not observations:
        print("[analyze] No observations to analyze.", file=sys.stderr)
        sys.exit(0)

    # Contradiction reducer: correction observations are evidence against
    # instincts whose scope they hit. Runs before detectors so a freshly
    # contradicted instinct is not re-reinforced in the same pass.
    contradiction_pass(observations, config, dry_run=args.dry_run)

    print(f"[analyze] Analyzing {len(observations)} observations...", file=sys.stderr)

    # Run all detectors. User corrections seed above the 0.30 proxy
    # (corrections ADR); the seed value lives in config, not code.
    correction_seed = config.get("thresholds", {}).get(
        "correction_seed_confidence", 0.45
    )
    all_instincts = []
    all_instincts.extend(
        detect_user_corrections(observations, correction_seed))
    all_instincts.extend(detect_corrections(observations))
    all_instincts.extend(detect_repeated_sequences(observations))
    all_instincts.extend(detect_error_recovery(observations))
    all_instincts.extend(detect_file_conventions(observations))
    all_instincts.extend(detect_rule_consultation(observations))
    all_instincts.extend(detect_guide_consultation(observations))

    saved = 0
    if not all_instincts:
        print("[analyze] No patterns detected yet.", file=sys.stderr)
    else:
        # Deduplicate by generating IDs
        seen_ids = set()
        for inst in all_instincts:
            iid = instinct_id(inst["action"])
            if iid in seen_ids:
                continue
            seen_ids.add(iid)
            if args.dry_run:
                print(
                    f"[dry-run] Would save instinct '{iid}': "
                    f"trigger=\"{inst['trigger']}\" "
                    f"action=\"{inst['action']}\" "
                    f"confidence={inst['confidence']:.2f} "
                    f"domain={inst['domain']}",
                    file=sys.stderr,
                )
            else:
                save_instinct(
                    iid=iid,
                    trigger=inst["trigger"],
                    action=inst["action"],
                    confidence=inst["confidence"],
                    domain=inst["domain"],
                    file_scope=inst.get("file_scope", "**"),
                    evidence=inst["evidence"],
                    evidence_count=inst.get("evidence_count", 1),
                    provenance=inst.get("provenance", "frequency"),
                )
            saved += 1
        if args.dry_run:
            print(f"[dry-run] {saved} instincts would be created/updated.",
                  file=sys.stderr)
        else:
            print(f"[analyze] Created/updated {saved} instincts.",
                  file=sys.stderr)

    if args.dry_run:
        sys.exit(0)

    # Write analysis marker so observe.py can reset its count
    write_analysis_marker()

    # Invoke propose.py only if instincts were created or updated.
    # Skipping when no new patterns were found avoids redundant scans.
    if saved > 0:
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
    else:
        print("[analyze] No new instincts; skipping propose.", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
