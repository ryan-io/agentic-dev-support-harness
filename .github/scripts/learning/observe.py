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
SESSION_DELTA_FILE = os.path.join(LEARNING_DIR, "session-delta.md")
LAST_MODIFIED_FILE = os.path.join(LEARNING_DIR, "last-modified.json")
INSTRUCTIONS_DIR = os.path.join(PROJECT_DIR, ".github", "instructions")

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

    # File-based tools: just the path (normalize separators)
    file_path = tool_input.get("file_path", "")
    if file_path:
        return file_path.replace("\\", "/")

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
        file_path = (tool_input or {}).get("file_path", "")
        if any(file_path.endswith(s) for s in (
            ".test.ts", ".test.js", ".spec.ts", ".spec.js", ".test.py",
            "_test.go", "_test.py",
        )):
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

        # Track rule/instruction file and guide consultations
        file_path = (tool_input or {}).get("file_path", "")
        if tool_name == "Read" and file_path:
            normalized = file_path.replace("\\", "/")
            if ".github/instructions/" in normalized or ".claude/rules/" in normalized:
                obs["rule_consulted"] = os.path.basename(file_path)
            elif ".github/docs/" in normalized and normalized.endswith("-guide.md"):
                obs["guide_consulted"] = os.path.basename(file_path)

        # Track file extension for edit/write operations
        if tool_name in ("Edit", "Write") and file_path:
            _, ext = os.path.splitext(file_path)
            if ext:
                obs["edit_ext"] = ext

    # PostToolUse includes outcome; failures carry a tool_error field
    if event_name == "PostToolUse":
        if event_data.get("tool_error"):
            obs["outcome"] = "failure"
        else:
            obs["outcome"] = "success"

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
    """On first PreToolUse of a session, notify about pending proposals and changes."""
    if session_already_notified(session_id):
        return

    messages = []

    delta = get_session_delta_summary()
    if delta:
        messages.append(f"Last session: {delta}")

    changed = get_instruction_changes()
    if changed:
        names = ", ".join(sorted(changed))
        messages.append(f"Instruction files updated since last session: {names}")

    pending = count_pending_proposals()
    if pending > 0:
        messages.append(
            f"{pending} pending proposal(s) waiting for review. "
            f"Run the continuous-learning skill to review."
        )

    for msg in messages:
        print(f"[learning] {msg}", file=sys.stderr)


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


# --- Session continuity ---


def get_session_observations(session_id):
    """Read observations for the given session from the JSONL file."""
    if not session_id or not os.path.isfile(OBS_FILE):
        return []
    prefix = session_id[:12]
    obs = []
    try:
        with open(OBS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("session_id") == prefix:
                        obs.append(rec)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return obs


def classify_complexity(observations):
    """Classify session as 'simple' or 'complex' based on tool usage."""
    edited_files = set()
    skill_invoked = False
    for obs in observations:
        tool = obs.get("tool", "")
        if tool in ("Edit", "Write"):
            summary = obs.get("input_summary", "")
            if summary:
                edited_files.add(summary)
        if tool == "Skill":
            skill_invoked = True
    if skill_invoked or len(edited_files) > 1:
        return "complex"
    return "simple"


def generate_session_delta(session_id):
    """Write session-delta.md summarizing the completed session."""
    observations = get_session_observations(session_id)
    if not observations:
        return

    edited_files = set()
    domains = set()
    rules_consulted = set()
    guides_consulted = set()
    for obs in observations:
        tool = obs.get("tool", "")
        if tool in ("Edit", "Write"):
            summary = obs.get("input_summary", "")
            if summary:
                edited_files.add(os.path.basename(summary))
        domain = obs.get("domain_hint", "")
        if domain:
            domains.add(domain)
        rule = obs.get("rule_consulted", "")
        if rule:
            rules_consulted.add(rule)
        guide = obs.get("guide_consulted", "")
        if guide:
            guides_consulted.add(guide)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    lines = [f"# Session Delta ({ts} UTC)", ""]
    if edited_files:
        lines.append(f"Files modified: {', '.join(sorted(edited_files))}")
    if domains:
        lines.append(f"Domains: {', '.join(sorted(domains))}")
    if rules_consulted:
        lines.append(f"Rules consulted: {', '.join(sorted(rules_consulted))}")
    if guides_consulted:
        lines.append(f"Guides consulted: {', '.join(sorted(guides_consulted))}")
    lines.append(f"Tool calls: {len(observations)}")
    lines.append("")

    try:
        with open(SESSION_DELTA_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError:
        pass


def update_last_modified():
    """Record current modification times of instruction files."""
    if not os.path.isdir(INSTRUCTIONS_DIR):
        return
    records = {}
    for fname in os.listdir(INSTRUCTIONS_DIR):
        if not fname.endswith(".instructions.md"):
            continue
        fpath = os.path.join(INSTRUCTIONS_DIR, fname)
        try:
            records[fname] = os.path.getmtime(fpath)
        except OSError:
            continue
    try:
        with open(LAST_MODIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except OSError:
        pass


def get_instruction_changes():
    """Compare current instruction file mtimes against last-modified.json."""
    if not os.path.isfile(LAST_MODIFIED_FILE) or not os.path.isdir(INSTRUCTIONS_DIR):
        return []
    try:
        with open(LAST_MODIFIED_FILE, "r", encoding="utf-8") as f:
            recorded = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    changed = []
    current_files = set()
    for fname in os.listdir(INSTRUCTIONS_DIR):
        if not fname.endswith(".instructions.md"):
            continue
        current_files.add(fname)
        fpath = os.path.join(INSTRUCTIONS_DIR, fname)
        try:
            current_mtime = os.path.getmtime(fpath)
        except OSError:
            continue
        if fname not in recorded or current_mtime > recorded[fname]:
            changed.append(fname)
    for fname in recorded:
        if fname not in current_files:
            changed.append(f"{fname} (removed)")
    return changed


def get_session_delta_summary():
    """Read session-delta.md and return a one-line summary."""
    if not os.path.isfile(SESSION_DELTA_FILE):
        return ""
    try:
        with open(SESSION_DELTA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Files modified:"):
                    return line
        return ""
    except OSError:
        return ""


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

    # On Stop events: generate delta, update last-modified, check thresholds
    if obs.get("event") == "Stop":
        generate_session_delta(session_id)
        update_last_modified()

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

        # Nudge only for complex sessions (multi-file or skill-invoking)
        session_obs = get_session_observations(session_id)
        if classify_complexity(session_obs) == "complex":
            handle_stop_nudge(config, unanalyzed)

    # Always exit 0: observation only, never block
    sys.exit(0)


if __name__ == "__main__":
    main()
