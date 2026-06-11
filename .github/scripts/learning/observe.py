#!/usr/bin/env python3
"""
observe.py
Hook handler for continuous learning observation layer.
Reads hook event JSON from stdin, extracts relevant fields,
appends a single JSONL line to .claude/learning/observations.jsonl.

Registered as a Claude Code hook in .claude/settings.json; runs on
PostToolUse, SessionStart, SessionEnd, and UserPromptSubmit events.
Tool calls are recorded on PostToolUse only: one observation per call,
carrying the outcome. (PreToolUse recording was removed because it doubled
every count; see the 2026-06-10 system review, B1.)
Never blocks, always exits 0.

On SessionEnd it also ticks the session clock (session-counter.json), the
timer behind the evidence-based staleness model.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

try:
    import session_clock
except ImportError:
    session_clock = None  # Hook must never fail on a missing sibling module

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
        "commit_nudge_proposal_count": 3,
        "pending_proposal_soft_cap": 10,
        "correction_seed_confidence": 0.45,
        "memory_curation_nudge_blocks": 5
    },
    "staleness": {
        "proposal_decay_sessions": 15,
        "proposal_archive_sessions": 30,
        "instinct_decay_per_sessions": 0.05,
        "instinct_decay_session_window": 15,
        "contradiction_penalty": 0.1
    }
}


MAX_OBSERVATIONS = 1000  # Rotate after this many entries


def _acquire_lock(f):
    """Take an advisory exclusive lock on an open file. Returns True if held.

    msvcrt on Windows, fcntl elsewhere. Failure to lock is tolerated: losing
    serialization is better than dropping a write or blocking the hook."""
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        return True
    except (OSError, ImportError):
        return False


def _release_lock(f):
    """Release the advisory lock taken by _acquire_lock. Never raises."""
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (OSError, ImportError):
        pass


def locked_append(path, text):
    """Append text under an OS-level exclusive lock.

    Concurrent hook invocations (parallel tool calls, overlapping sessions)
    can interleave bytes mid-record in a plain append. An advisory lock
    serializes writers. If the lock cannot be taken, the write proceeds
    unlocked; losing serialization is better than dropping the observation
    or blocking the hook.
    """
    with open(path, "a", encoding="utf-8") as f:
        locked = _acquire_lock(f)
        try:
            f.write(text)
            f.flush()
        finally:
            if locked:
                _release_lock(f)


def rotate_observations_if_needed():
    """Archive the observations file when it exceeds MAX_OBSERVATIONS entries.

    Called only at session boundaries (SessionStart), never mid-session:
    rotating under active writers orphans their open handles (silent data
    loss), can hit Windows sharing violations, and truncates the session
    delta, which reads only the current file. Observations recorded after
    the last analysis marker have not been consumed by analyze.py yet, so
    they are carried into the fresh file instead of being archived away.
    """
    if not os.path.isfile(OBS_FILE):
        return
    try:
        # The whole read-archive-truncate sequence runs under the same lock
        # locked_append takes (B5). With the old os.replace approach, a
        # detached analyze.py could append its analysis marker between the
        # rotation's read and the swap; the swap discarded the marker and
        # the carried-forward tail was analyzed twice. Rewriting in place
        # under the lock closes that window: a concurrent append lands
        # either before the read (and is rotated correctly) or after the
        # truncate (and survives in the fresh tail).
        with open(OBS_FILE, "r+", encoding="utf-8") as f:
            locked = _acquire_lock(f)
            try:
                f.seek(0)
                lines = [line for line in f if line.strip()]
                if len(lines) < MAX_OBSERVATIONS:
                    return

                # Find the last analysis marker; everything after it is
                # unanalyzed and carried forward.
                last_marker = -1
                for i, line in enumerate(lines):
                    try:
                        if (json.loads(line).get("event")
                                == "_analysis_marker"):
                            last_marker = i
                    except json.JSONDecodeError:
                        continue
                # No marker means analysis never ran; archive everything
                # rather than letting the file grow without bound.
                keep = lines[last_marker + 1:] if last_marker >= 0 else []

                # Archive copy first, then truncate in place. A crash
                # between the two leaves duplicates in the archive, never
                # data loss in the live file.
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                archive_dir = os.path.join(
                    LEARNING_DIR, "observations.archive"
                )
                os.makedirs(archive_dir, exist_ok=True)
                archive_path = os.path.join(
                    archive_dir, f"observations-{ts}.jsonl"
                )
                with open(archive_path, "w", encoding="utf-8") as af:
                    af.writelines(lines)

                f.seek(0)
                f.truncate()
                f.writelines(keep)
                f.flush()
            finally:
                if locked:
                    _release_lock(f)
    except OSError:
        pass  # Never block on rotation errors


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


# Editing or reading files under these paths is the learning system observing
# its own machinery (instinct YAML, proposal markdown, the observation log),
# not real project work. Recording it would teach detectors from their own
# churn -- e.g. promoting "place .yaml files in .claude/learning/instincts/".
# Such observations are dropped before they reach the log. Instruction files
# (.github/instructions/, .claude/rules/) are intentionally NOT excluded here:
# the rule- and guide-consultation detectors depend on seeing them.
SELF_OBSERVATION_FRAGMENTS = (".claude/learning/",)


# Input fields that name a tool's target: file paths for file tools, the
# command line for Bash, pattern/query/path for search tools. Content
# fields (old_string, new_string, file content) are deliberately excluded:
# editing a document that mentions the learning directory is real work.
SELF_OBSERVATION_INPUT_KEYS = (
    "file_path", "notebook_path", "command", "pattern", "query", "path",
)


def is_self_observation(tool_input):
    """True if the tool targets the learning pipeline's own data directory.

    Checks every target-naming input field, not just file_path (B6):
    Bash, Grep, and Glob calls aimed at .claude/learning/ are the
    pipeline observing its own churn and must not reach the log."""
    if not tool_input or not isinstance(tool_input, dict):
        return False
    for key in SELF_OBSERVATION_INPUT_KEYS:
        val = tool_input.get(key, "")
        if isinstance(val, str) and val:
            normalized = val.replace("\\", "/")
            if any(frag in normalized
                   for frag in SELF_OBSERVATION_FRAGMENTS):
                return True
    return False


def build_observation(event_data):
    """Build a single observation record from hook event data."""
    event_name = event_data.get("hook_event_name", "")
    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input", {})
    session_id = event_data.get("session_id", "")

    # Drop the pipeline's observations of its own learning data.
    if is_self_observation(tool_input):
        return None

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

    # PostToolUse carries the result in tool_response (a dict or string,
    # depending on the tool). Derive failure conservatively: an explicit
    # success=False or a truthy error field means failure; anything
    # ambiguous counts as success. tool_error is kept as a fallback for
    # older or future payload shapes.
    if event_name == "PostToolUse":
        response = event_data.get("tool_response")
        failed = False
        if isinstance(response, dict):
            failed = (
                response.get("success") is False
                or bool(response.get("error"))
                or bool(response.get("is_error"))
            )
        if not failed and event_data.get("tool_error"):
            failed = True
        obs["outcome"] = "failure" if failed else "success"

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


def oldest_pending_proposal():
    """Return the filename of the oldest pending proposal, or "".

    Ordered by created_session frontmatter when present, falling back to
    file mtime. Drives the soft-cap oldest-first review nudge."""
    if not os.path.isdir(PROPOSALS_DIR):
        return ""
    oldest_name, oldest_key = "", None
    for fname in os.listdir(PROPOSALS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(PROPOSALS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                head = f.read(500)
            if "status: pending" not in head:
                continue
            import re as _re
            m = _re.search(r"created_session:\s*(\d+)", head)
            key = (0, int(m.group(1))) if m else (1, os.path.getmtime(path))
        except (OSError, ValueError):
            continue
        if oldest_key is None or key < oldest_key:
            oldest_key, oldest_name = key, fname
    return oldest_name


def count_session_delta_blocks():
    """Count accumulated session blocks in the local session log."""
    if not os.path.isfile(SESSION_DELTA_FILE):
        return 0
    try:
        with open(SESSION_DELTA_FILE, "r", encoding="utf-8") as f:
            return sum(1 for line in f
                       if line.startswith("# Session Delta"))
    except OSError:
        return 0


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
    """On SessionStart, notify about pending proposals and changes."""
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
        soft_cap = load_config().get("thresholds", {}).get(
            "pending_proposal_soft_cap", 10
        )
        if pending > soft_cap:
            oldest = oldest_pending_proposal()
            oldest_hint = f" Start with the oldest: {oldest}." if oldest else ""
            messages.append(
                f"{pending} pending proposals exceed the soft cap of "
                f"{soft_cap}. Review oldest-first via the "
                f"continuous-learning skill.{oldest_hint}"
            )
        else:
            messages.append(
                f"{pending} pending proposal(s) waiting for review. "
                f"Run the continuous-learning skill to review."
            )

    # Memory curation cadence (project-memory ADR debt): nudge when the
    # local session log has accumulated enough blocks to be worth curating.
    delta_blocks = count_session_delta_blocks()
    curation_nudge = load_config().get("thresholds", {}).get(
        "memory_curation_nudge_blocks", 5
    )
    if delta_blocks >= curation_nudge:
        messages.append(
            f"Session log holds {delta_blocks} uncurated session blocks. "
            f"Run the continuous-learning skill (memory curation step) to "
            f"promote durable facts into project memory."
        )

    # SessionStart stdout is added to the agent's context; stderr on a
    # zero exit is not. Print to stdout so the notice is actually seen.
    for msg in messages:
        print(f"[learning] {msg}")


# --- Correction capture (transcript parse) ---
# Per adr-learn-capture-corrections-via-transcript-parse: on the session
# boundary, walk user turns in the transcript Claude Code passes, classify
# each as corrective or not, and record derived fields only. Raw transcript
# text never reaches the observation log. Conservative by construction:
# an ambiguous turn is not a correction.

MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024  # degrade quietly on oversized files

# Only corrections of mutating actions are captured; you cannot meaningfully
# "reject" a read. Mirrors MUTATING_TOOLS in analyze.py.
CORRECTION_MUTATING_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

# Trigger-phrase categories. Anchored phrases hold precision high at the
# cost of recall, the trade the ADR chose. Matched lowercase against the
# head of the turn.
CORRECTION_PHRASES = (
    ("negation", ("no,", "no.", "nope", "don't do", "do not do",
                  "that's not what i", "that is not what i",
                  "not what i asked", "not what i meant",
                  "undo that", "undo this", "revert that", "revert this")),
    ("rejection", ("that's wrong", "that is wrong", "this is wrong",
                   "wrong file", "wrong place", "wrong approach",
                   "incorrect", "that's not right", "that is not right",
                   "you broke", "that broke", "this broke")),
    ("redirect", ("instead", "rather than", "i meant", "actually,",
                  "change it to", "change that to", "should have been",
                  "redo that", "redo this", "try again but")),
)

CLASSIFY_HEAD_CHARS = 240  # a correction announces itself early in the turn


def classify_correction(text):
    """Return the trigger-phrase category for a user turn, or None.

    Conservative: only anchored phrases in the head of the turn count.
    Ambiguous is not a correction."""
    if not isinstance(text, str) or not text.strip():
        return None
    head = text[:CLASSIFY_HEAD_CHARS].lower()
    for category, phrases in CORRECTION_PHRASES:
        for phrase in phrases:
            if phrase in head:
                return category
    return None


def _relative_target(path):
    """Normalize a tool target to a repo-relative path (or basename)."""
    if not path:
        return ""
    norm = path.replace("\\", "/")
    root = PROJECT_DIR.replace("\\", "/").rstrip("/")
    if norm.startswith(root + "/"):
        return norm[len(root) + 1:]
    return os.path.basename(norm)


def _extract_user_text(message):
    """Extract human text from a user message; "" for tool_result turns."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    texts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        if btype == "tool_result":
            return ""  # machine turn, not the human speaking
        if btype == "text":
            texts.append(block.get("text", ""))
    return "\n".join(texts)


def parse_transcript_for_corrections(transcript_path, session_id):
    """Parse a session transcript into `correction` observations.

    Pinned to the Claude Code JSONL transcript format: one JSON record per
    line, records carrying type user/assistant and an Anthropic-style
    message. Anything else degrades quietly to no observations. The whole
    path fails closed; it never raises.

    Every returned observation carries derived fields only: target file or
    topic, a templated change description built from tool metadata, and the
    trigger-phrase category. No transcript text is ever copied through."""
    corrections = []
    try:
        if not transcript_path or not os.path.isfile(transcript_path):
            return []
        if os.path.getsize(transcript_path) > MAX_TRANSCRIPT_BYTES:
            return []

        last_tool, last_target = "", ""
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                rtype = rec.get("type", "")
                message = rec.get("message", {})
                if not isinstance(message, dict):
                    continue

                if rtype == "assistant":
                    content = message.get("content", [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != "tool_use":
                            continue
                        name = block.get("name", "")
                        if name not in CORRECTION_MUTATING_TOOLS:
                            continue
                        tool_input = block.get("input", {})
                        if isinstance(tool_input, dict):
                            last_tool = name
                            last_target = _relative_target(
                                tool_input.get("file_path", "")
                            )
                    continue

                if rtype != "user":
                    continue
                category = classify_correction(_extract_user_text(message))
                if not category:
                    continue
                if not last_tool:
                    continue  # nothing to pair the correction with
                target = last_target or "general"
                _, ext = os.path.splitext(target)
                corrections.append({
                    "ts": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"),
                    "event": "correction",
                    "session_id": session_id[:12] if session_id else "",
                    "provenance": "user-correction",
                    "category": category,
                    "tool": last_tool,
                    "target": target,
                    "file_ext": ext,
                    "change": (
                        f"user {category} after {last_tool} on {target}"
                    ),
                })
    except (OSError, ValueError, TypeError, AttributeError):
        return []  # fail closed: the hook must never block
    return corrections


def capture_corrections(event_data, session_id):
    """SessionEnd entry point: parse the transcript, append observations."""
    try:
        transcript_path = event_data.get("transcript_path", "")
        for obs in parse_transcript_for_corrections(
                transcript_path, session_id):
            locked_append(
                OBS_FILE, json.dumps(obs, separators=(",", ":")) + "\n"
            )
    except (OSError, TypeError):
        pass


# Explicit developer signal (corrections ADR, secondary source): a prompt
# beginning with this marker is a developer-flagged correction, the
# highest-precision signal. Recall supplement for corrections the
# transcript classifier would phrase-miss.
CORRECTION_MARKER = "#correction"


def handle_prompt_submit(event_data, session_id):
    """UserPromptSubmit entry point: record a developer-flagged correction.

    Only the marker is recognized; the prompt text itself is never written
    to the observation log (same derived-fields boundary as the transcript
    parse). The correction pairs with the session's most recent mutating
    tool action, falling back to `general`."""
    try:
        prompt = event_data.get("prompt", "")
        if not isinstance(prompt, str):
            return
        if not prompt.lstrip().lower().startswith(CORRECTION_MARKER):
            return

        tool, target = "", "general"
        for obs in reversed(get_session_observations(session_id)):
            if (obs.get("tool") in CORRECTION_MUTATING_TOOLS
                    and obs.get("input_summary")):
                tool = obs["tool"]
                target = _relative_target(obs["input_summary"]) or "general"
                break
        _, ext = os.path.splitext(target)
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event": "correction",
            "session_id": session_id[:12] if session_id else "",
            "provenance": "developer-flagged",
            "category": "explicit",
            "tool": tool,
            "target": target,
            "file_ext": ext,
            "change": (
                f"developer flagged correction after "
                f"{tool or 'recent work'} on {target}"
            ),
        }
        os.makedirs(LEARNING_DIR, exist_ok=True)
        locked_append(
            OBS_FILE, json.dumps(record, separators=(",", ":")) + "\n"
        )
    except (OSError, TypeError, ValueError):
        pass  # fail closed: never block the prompt


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


def generate_session_delta(session_id):
    """Append a summary block for the completed session to the local session log (accumulates across sessions)."""
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
        with open(SESSION_DELTA_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
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
    """Return the most recent 'Files modified' line from the session log."""
    if not os.path.isfile(SESSION_DELTA_FILE):
        return ""
    try:
        latest = ""
        with open(SESSION_DELTA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Files modified:"):
                    latest = line
        return latest
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

    # SessionStart: surface a one-time notice. Stdout from a SessionStart
    # hook is added to the agent's context, so this is where pending
    # proposals and last-session changes become visible. Rotation also
    # happens here, at a session boundary, where no writer from this
    # session holds the file open and the previous session's delta has
    # already been generated.
    if event_name == "SessionStart":
        handle_session_start_notice(session_id)
        rotate_observations_if_needed()
        sys.exit(0)

    # UserPromptSubmit: recognize the explicit correction marker. No output
    # (stdout would be injected into context); record and move on.
    if event_name == "UserPromptSubmit":
        handle_prompt_submit(event_data, session_id)
        sys.exit(0)

    # SessionEnd: the session is over. Generate exactly one delta, refresh
    # instruction mtimes, and trigger analysis if enough has accumulated.
    # Stop fires after every assistant turn, so it must not drive these.
    if event_name == "SessionEnd":
        os.makedirs(LEARNING_DIR, exist_ok=True)
        # Session clock: one tick per session worked. SessionEnd is the
        # boundary (Stop fires every assistant turn). A killed session
        # never ticks; undercounting delays decay, never accelerates loss.
        if session_clock is not None:
            session_clock.increment_session_count(LEARNING_DIR)
        # Correction capture: batch-parse the session transcript for user
        # corrections before the delta and analysis trigger consume the log.
        capture_corrections(event_data, session_id)
        generate_session_delta(session_id)
        update_last_modified()

        config = load_config()
        threshold = config.get("thresholds", {}).get(
            "min_observations_before_analysis", 20
        )
        if count_unanalyzed() >= threshold:
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
        sys.exit(0)

    # Tool events (PostToolUse only): record one observation per tool call.
    obs = build_observation(event_data)
    if obs is None:
        sys.exit(0)

    os.makedirs(LEARNING_DIR, exist_ok=True)
    try:
        locked_append(OBS_FILE, json.dumps(obs, separators=(",", ":")) + "\n")
    except OSError:
        sys.exit(0)  # Never block on write errors

    # Always exit 0: observation only, never block
    sys.exit(0)


if __name__ == "__main__":
    main()
