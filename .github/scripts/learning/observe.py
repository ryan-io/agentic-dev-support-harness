#!/usr/bin/env python3
"""
observe.py
Hook handler for continuous learning observation layer.
Reads hook event JSON from stdin, extracts relevant fields,
appends a single JSONL line to .claude/learning/observations.jsonl.

Called by .github/hooks/observe.json on PreToolUse, PostToolUse, and Stop events.
Never blocks, always exits 0.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# --- Paths ---

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
LEARNING_DIR = os.path.join(PROJECT_DIR, ".claude", "learning")
OBS_FILE = os.path.join(LEARNING_DIR, "observations.jsonl")
CONFIG_FILE = os.path.join(LEARNING_DIR, "config.json")
PROPOSALS_DIR = os.path.join(LEARNING_DIR, "proposals")
SESSION_NOTICE_DIR = os.path.join(LEARNING_DIR, ".session-notices")

# --- Defaults ---

DEFAULT_CONFIG = {
    "thresholds": {
        "min_observations_before_analysis": 20,
        "proposal_confidence_threshold": 0.7,
        "commit_nudge_observation_count": 50,
        "commit_nudge_proposal_count": 3
    },
    "staleness": {
        "proposal_decay_days": 30,
        "proposal_archive_days": 60,
        "instinct_decay_per_month": 0.05
    }
}


def load_config():
    """Load config, returning defaults if missing."""
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG


def summarize_tool_input(tool_input):
    """Extract a short summary from tool_input without capturing code or secrets."""
    if not tool_input or not isinstance(tool_input, dict):
        return ""

    # File-based tools: just the path
    file_path = tool_input.get("file_path", "")
    if file_path:
        return file_path

    # Bash: first 120 chars of command, no arguments after first pipe/redirect
    command = tool_input.get("command", "")
    if command:
        for sep in ["|", ">", ";", "&&", "||"]:
            idx = command.find(sep)
            if idx > 0:
                command = command[:idx].strip()
                break
        return command[:120]

    # Search/grep: the pattern
    pattern = tool_input.get("pattern", tool_input.get("query", ""))
    if pattern:
        return str(pattern)[:120]

    return ""


def extract_file_ext(tool_input):
    """Extract file extension from tool input if present."""
    if not tool_input or not isinstance(tool_input, dict):
        return ""
    file_path = tool_input.get("file_path", "")
    if file_path:
        _, ext = os.path.splitext(file_path)
        return ext
    return ""


def classify_domain(tool_name, tool_input):
    """Rough domain hint based on tool and target."""
    if not tool_name:
        return ""
    name = tool_name.lower()

    if name == "bash":
        cmd = (tool_input or {}).get("command", "").lower()
        if any(t in cmd for t in ["test", "jest", "pytest", "nunit", "xunit"]):
            return "testing"
        if any(g in cmd for g in ["git ", "git\t"]):
            return "git"
        return "shell"

    if name in ("edit", "write"):
        ext = extract_file_ext(tool_input)
        if ext in (".test.ts", ".test.js", ".spec.ts", ".spec.js", ".test.py"):
            return "testing"
        return "code-style"

    if name in ("read", "grep", "glob"):
        return "navigation"

    return "workflow"


def build_observation(event_data):
    """Build a single observation record from hook event data."""
    event_name = event_data.get("hook_event_name", "")
    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input", {})
    session_id = event_data.get("session_id", "")

    obs = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event_name,
        "session_id": session_id[:12] if session_id else "",
    }

    if tool_name:
        obs["tool"] = tool_name
        obs["input_summary"] = summarize_tool_input(tool_input)
        obs["file_ext"] = extract_file_ext(tool_input)
        obs["domain_hint"] = classify_domain(tool_name, tool_input)

    # PostToolUse includes outcome
    if event_name == "PostToolUse":
        obs["outcome"] = "success"
    elif event_name == "PostToolUseFailure":
        obs["outcome"] = "failure"

    # Stop event: check stop_hook_active to avoid loops
    if event_name == "Stop":
        if event_data.get("stop_hook_active", False):
            return None  # Skip, this is a recursive stop
        obs["event"] = "Stop"

    return obs


def count_unanalyzed():
    """Count observations since last analysis marker."""
    if not os.path.isfile(OBS_FILE):
        return 0
    count = 0
    try:
        with open(OBS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("event") == "_analysis_marker":
                        count = 0
                    else:
                        count += 1
                except json.JSONDecodeError:
                    continue
    except OSError:
        return 0
    return count


def count_pending_proposals():
    """Count proposal files with status: pending."""
    if not os.path.isdir(PROPOSALS_DIR):
        return 0
    count = 0
    for fname in os.listdir(PROPOSALS_DIR):
        if not fname.endswith(".md"):
            continue
        try:
            with open(os.path.join(PROPOSALS_DIR, fname), "r", encoding="utf-8") as f:
                head = f.read(500)
            if "status: pending" in head:
                count += 1
        except OSError:
            continue
    return count


def session_already_notified(session_id):
    """Check if we already showed the session-start notice for this session."""
    if not session_id:
        return True
    os.makedirs(SESSION_NOTICE_DIR, exist_ok=True)
    marker = os.path.join(SESSION_NOTICE_DIR, session_id[:12])
    if os.path.isfile(marker):
        return True
    # Create marker
    try:
        with open(marker, "w") as f:
            f.write("")
    except OSError:
        pass
    # Clean old markers (keep last 20)
    try:
        markers = sorted(
            [os.path.join(SESSION_NOTICE_DIR, f)
             for f in os.listdir(SESSION_NOTICE_DIR)],
            key=os.path.getmtime,
        )
        for old in markers[:-20]:
            os.remove(old)
    except OSError:
        pass
    return False


def handle_session_start_notice(session_id):
    """On first PreToolUse of a session, notify about pending proposals."""
    if session_already_notified(session_id):
        return
    pending = count_pending_proposals()
    if pending > 0:
        print(
            f"[learning] {pending} pending proposal(s) waiting for review. "
            f"Run the continuous-learning skill to review.",
            file=sys.stderr,
        )


def handle_stop_nudge(config, unanalyzed):
    """On Stop, nudge if observation/proposal counts are high."""
    thresholds = config.get("thresholds", {})
    nudge_obs = thresholds.get("commit_nudge_observation_count", 50)
    nudge_proposals = thresholds.get("commit_nudge_proposal_count", 3)

    messages = []
    if unanalyzed >= nudge_obs:
        messages.append(f"{unanalyzed} unanalyzed observations")
    pending = count_pending_proposals()
    if pending >= nudge_proposals:
        messages.append(f"{pending} pending proposals")

    if messages:
        summary = " and ".join(messages)
        print(
            f"[learning] {summary}, consider running the continuous-learning skill.",
            file=sys.stderr,
        )


def main():
    # Read event JSON from stdin
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        event_data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        sys.exit(0)  # Never block on parse errors

    event_name = event_data.get("hook_event_name", "")
    session_id = event_data.get("session_id", "")

    # Session-start notice on first PreToolUse
    if event_name == "PreToolUse":
        handle_session_start_notice(session_id)

    # Build observation
    obs = build_observation(event_data)
    if obs is None:
        sys.exit(0)

    # Ensure learning directory exists
    os.makedirs(LEARNING_DIR, exist_ok=True)

    # Append to JSONL
    try:
        with open(OBS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(obs, separators=(",", ":")) + "\n")
    except OSError:
        sys.exit(0)  # Never block on write errors

    # On Stop events: check thresholds
    if obs.get("event") == "Stop":
        config = load_config()
        threshold = config.get("thresholds", {}).get(
            "min_observations_before_analysis", 20
        )
        unanalyzed = count_unanalyzed()

        # Auto-invoke analysis if threshold met
        if unanalyzed >= threshold:
            analyze_script = os.path.join(
                PROJECT_DIR, ".github", "scripts", "learning", "analyze.py"
            )
            if os.path.isfile(analyze_script):
                try:
                    subprocess.Popen(
                        [sys.executable, analyze_script],
                        cwd=PROJECT_DIR,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except OSError:
                    pass

        # Nudge if counts are high
        handle_stop_nudge(config, unanalyzed)

    # Always exit 0: observation only, never block
    sys.exit(0)


if __name__ == "__main__":
    main()
