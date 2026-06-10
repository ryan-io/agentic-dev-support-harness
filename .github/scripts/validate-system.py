#!/usr/bin/env python3
"""
validate-system.py
Automated validation of the project setup template system.
Checks file existence, size limits, sync state, frontmatter, cross-references,
cross-platform parity, hook config, config schema, Python syntax, YAML validity,
pipeline chain integrity, gitignore coverage, learning pipeline consistency,
and workflow/sync/setup subsystem consistency.

Run from repo root: python .github/scripts/validate-system.py
              or:   python .github/scripts/validate-system.py --changed file1 file2 ...

The --changed flag enables incremental mode: only sections relevant to the
listed files are executed. Without --changed, all sections run (CI default).
Exit code: 0 = all pass, 1 = failures found.
"""

import json
import os
import re
import sys
import glob
import py_compile
import tempfile
from functools import lru_cache
from fnmatch import fnmatch


@lru_cache(maxsize=256)
def read_file(path):
    """Read and normalize a file, caching the result for repeated access.

    utf-8-sig strips a leading BOM (common from Windows editors); a strict
    utf-8 read leaves the BOM in the text, where it silently breaks
    startswith() checks like the DEPRECATED marker and frontmatter parsing.
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read().replace("\r", "").replace("\x00", "")


MAX_CHARS = 4000
SRC_DIR = os.path.join(".github", "instructions")
DEST_DIR = os.path.join(".claude", "rules")
HUB_SRC = os.path.join(".github", "copilot-instructions.md")
HUB_DEST = "CLAUDE.md"
SKILLS_DIR = os.path.join(".github", "skills")
SYSTEM_INDEX = os.path.join(".github", "docs", "system-index.md")
SCRIPTS_DIR = os.path.join(".github", "scripts")
WORKFLOWS_DIR = os.path.join(".github", "workflows")
HOOKS_DIR = os.path.join(".github", "hooks")
LEARNING_DIR = os.path.join(".claude", "learning")
CONFIG_FILE = os.path.join(LEARNING_DIR, "config.json")
SETTINGS_FILE = os.path.join(".claude", "settings.json")

# --- Incremental mode ---
SECTION_MAP = [
    (".github/instructions/*.md",           {1, 3, 4, 5, 14, 15, 17, 18, 19, 20}),
    (".github/copilot-instructions.md",     {1, 2, 5, 14}),
    ("CLAUDE.md",                           {1, 2, 14}),
    (".github/skills/*/SKILL.md",           {6, 14, 18}),
    (".github/skills/*",                    {6, 14, 18}),
    (".github/workflows/*.yml",             {11, 22}),
    (".github/scripts/*.py",                {10, 12, 22}),
    (".github/scripts/learning/*.py",       {10, 12, 21}),
    (".claude/settings.json",               {1, 8, 21}),
    (".claude/learning/config.json",        {9}),
    (".github/scripts/setup/*",             {7, 22}),
    (".github/scripts/setup/*.py",          {1, 7, 10, 22}),
    (".github/docs/*",                      {5, 18, 20}),
    (".gitignore",                          {13, 22}),
    (".claude/rules/*.md",                  {3, 4, 14}),
    ("templates/*",                         {23}),
    ("docs/adr/*.md",                       {23}),
    (".github/scripts/eject-manifest.json", {23}),
]
ALL_SECTIONS = set(range(1, 24))

def compute_active_sections(changed_files):
    active = set()
    for cf in changed_files:
        cf_norm = cf.replace("\\", "/")
        matched = False
        for pattern, sections in SECTION_MAP:
            if fnmatch(cf_norm, pattern):
                active.update(sections)
                matched = True
        if not matched:
            return ALL_SECTIONS
    return active if active else ALL_SECTIONS

_changed_files = []
_incremental = False
if "--changed" in sys.argv:
    _idx = sys.argv.index("--changed")
    _changed_files = sys.argv[_idx + 1:]
    _incremental = True

active_sections = compute_active_sections(_changed_files) if _incremental else ALL_SECTIONS

def should_run(n):
    return n in active_sections

if _incremental:
    print(f"[incremental] Running sections: {sorted(active_sections)}")
    print(f"[incremental] Changed files: {_changed_files}")

passes = 0
fails = 0
warns = 0
issues = []
current_check = ""


def result(status, msg):
    global passes, fails, warns
    if status == "PASS":
        passes += 1
    elif status == "FAIL":
        fails += 1
        issues.append(("FAIL", current_check, msg))
    else:
        warns += 1
        issues.append(("WARN", current_check, msg))
    print(f"  {status}: {msg}")


# Pre-define cross-section variables (needed when sections are skipped)
LEARNING_SCRIPTS_DIR = os.path.join(SCRIPTS_DIR, "learning")
SETUP_SCRIPTS_DIR = os.path.join(SCRIPTS_DIR, "setup")
hook_cfg = None
hooks_root = {}

# ============================================================
# 1. File existence
# ============================================================

current_check = "[1] File existence"
print("\n[1] File existence")

if should_run(1):

    # Post-setup, the init machinery is removable (harness-eject Category A),
    # so its presence is only required while setup has not completed.
    _setup_done = os.path.isfile(os.path.join(".claude", "setup-complete"))

    REQUIRED_FILES = [
        HUB_SRC, HUB_DEST, SYSTEM_INDEX,
        os.path.join(SCRIPTS_DIR, "sync-claude-rules.py"),
        os.path.join(HOOKS_DIR, "pre-commit"),
        os.path.join(".github", "docs", "adr-template.md"),
        os.path.join(".github", "docs", "br-template.md"),
        os.path.join(".github", "pull_request_template.md"), ".gitignore",
        os.path.join(SRC_DIR, "pattern-fidelity.instructions.md"),
        SETTINGS_FILE,
        os.path.join(LEARNING_SCRIPTS_DIR, "observe.py"),
        os.path.join(LEARNING_SCRIPTS_DIR, "analyze.py"),
        os.path.join(LEARNING_SCRIPTS_DIR, "propose.py"),
        CONFIG_FILE,
    ]
    if not _setup_done:
        REQUIRED_FILES.append(os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.py"))

    for f in REQUIRED_FILES:
        if os.path.isfile(f):
            result("PASS", f)
        else:
            result("FAIL", f + " -- missing")

# ============================================================
# 2. Hub file sync
# ============================================================

current_check = "[2] Hub file sync"
print("\n[2] Hub file sync")

if should_run(2):
    if os.path.isfile(HUB_SRC) and os.path.isfile(HUB_DEST):
        src_content = read_file(HUB_SRC)
        dest_content = read_file(HUB_DEST)
        if src_content == dest_content:
            result("PASS", "CLAUDE.md matches copilot-instructions.md")
        else:
            result("FAIL", "CLAUDE.md differs -- run sync")
    else:
        result("FAIL", "Hub files missing -- cannot compare")

# ============================================================
# 3. Size limits
# ============================================================

current_check = "[3] Size limits (instruction files <= 4000 chars)"
print("\n[3] Size limits (instruction files <= 4000 chars)")

if should_run(3):
    instruction_dirs = [
        os.path.join(".github", "instructions"),
        os.path.join(".claude", "rules"),
    ]
    md_files = set()
    for idir in instruction_dirs:
        md_files.update(glob.glob(os.path.join(idir, "*.md")))

    size_records = []
    for md in sorted(md_files):
        if ".git/" in md or "node_modules/" in md:
            continue
        if os.path.basename(md).lower() == "readme.md":
            continue
        file_content = read_file(md)
        if file_content.strip().startswith("<!-- DEPRECATED"):
            continue
        size = len(file_content)
        size_records.append((md, size))
        if size > MAX_CHARS:
            result("FAIL", f"{md} -- {size} chars (limit {MAX_CHARS})")
        else:
            result("PASS", f"{md} -- {size} chars")

    size_records.sort(key=lambda x: x[1], reverse=True)
    tightest = [(f, s) for f, s in size_records if s <= MAX_CHARS][:3]
    if tightest:
        parts = [f"{os.path.basename(f)} ({MAX_CHARS - s} free)" for f, s in tightest]
        print(f"  Tightest: {', '.join(parts)}")

# ============================================================
# 4. Instruction file sync state
# ============================================================

current_check = "[4] Instruction sync state"
print("\n[4] Instruction sync state")

if should_run(4):
    src_files = sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md")))
    expected_copies = set()

    for src in src_files:
        filename = os.path.basename(src)
        content = read_file(src)

        if content.strip().startswith("<!-- DEPRECATED"):
            result("PASS", f"{filename} -- deprecated, skipped")
            continue

        # Regenerate the expected mirror output exactly as
        # sync-claude-rules.py writes it (paths frontmatter from applyTo,
        # body carried verbatim) and compare full content. A frontmatter-only
        # check lets a hand-edited mirror body commit silently.
        parts = content.split("---", 2)
        if len(parts) < 3:
            result("FAIL", f"{filename} -- no valid frontmatter")
            continue
        if parts[0].strip():
            result("FAIL", f"{filename} -- content before frontmatter "
                           "(sync would silently drop it)")
            continue

        match = re.search(r'applyTo:\s*["\']?([^"\'\n]+)["\']?', parts[1])
        if not match:
            result("FAIL", f"{filename} -- missing applyTo frontmatter")
            continue
        apply_to = match.group(1).strip()
        result("PASS", f"{filename} -- applyTo: {apply_to}")

        apply_to_parts = [p.strip() for p in apply_to.split(",") if p.strip()]
        paths_value = ", ".join(f'"{p}"' for p in apply_to_parts)
        expected_output = f'---\npaths: [{paths_value}]\n---\n{parts[2]}'

        dest_name = filename.replace(".instructions", "")
        dest_path = os.path.join(DEST_DIR, dest_name)
        expected_copies.add(dest_name)

        if not os.path.isfile(dest_path):
            result("FAIL", f"{dest_name} -- missing in {DEST_DIR}")
            continue

        dest_content = read_file(dest_path)
        if dest_content == expected_output:
            result("PASS", f"{dest_name} -- synced, paths: {apply_to}")
            continue

        # Mismatch: report whether frontmatter or body drifted.
        paths_match = re.search(r'paths:\s*\[([^\]]+)\]', dest_content)
        if not paths_match:
            result("FAIL", f"{dest_name} -- missing paths frontmatter")
        else:
            path_values = [p.strip().strip('"').strip("'")
                           for p in paths_match.group(1).split(",")]
            if path_values != apply_to_parts:
                result("FAIL", f"{dest_name} -- paths mismatch (expected "
                               f"{apply_to}, got {','.join(path_values)})")
            else:
                result("FAIL", f"{dest_name} -- body drifted from source "
                               "(hand-edited mirror? run sync)")

    if os.path.isdir(DEST_DIR):
        for f in os.listdir(DEST_DIR):
            if f.endswith(".md") and f not in expected_copies:
                result("WARN", f"{DEST_DIR}/{f} -- orphaned")

# ============================================================
# 5. Cross-references (hub + index)
# ============================================================

current_check = "[5] Cross-references"
print("\n[5] Cross-references")

if should_run(5):
    def check_path_refs(content, label):
        refs = re.findall(r'`([^`]+/[^`]+)`', content)
        seen = set()
        for ref in refs:
            ref = ref.strip()
            if ref in seen or "*" in ref or "{" in ref:
                continue
            if "|" in ref or "(" in ref or len(ref) > 100 or len(ref) < 3 or " " in ref:
                continue
            seen.add(ref)
            clean = ref.rstrip("/")
            if os.path.isfile(clean) or os.path.isdir(clean):
                result("PASS", f"{label}: {ref}")
            else:
                result("FAIL", f"{label}: {ref} -- not found")

    if os.path.isfile(HUB_SRC):
        check_path_refs(read_file(HUB_SRC), "hub")

    if os.path.isfile(SYSTEM_INDEX):
        check_path_refs(read_file(SYSTEM_INDEX), "index")

# ============================================================
# 6. Skills validation
# ============================================================

current_check = "[6] Skills validation"
print("\n[6] Skills validation")

if should_run(6):
    if os.path.isdir(SKILLS_DIR):
        for skill_dir in sorted(os.listdir(SKILLS_DIR)):
            skill_full = os.path.join(SKILLS_DIR, skill_dir)
            if not os.path.isdir(skill_full):
                continue
            skill_path = os.path.join(skill_full, "SKILL.md")
            if not os.path.isfile(skill_path):
                result("FAIL", f"{skill_dir} -- no SKILL.md")
                continue
            skill_content = read_file(skill_path)
            if not skill_content.startswith("---"):
                result("FAIL", f"{skill_dir} -- missing frontmatter")
            elif "name:" not in skill_content.split("---")[1]:
                result("FAIL", f"{skill_dir} -- missing name")
            else:
                result("PASS", f"{skill_dir} -- valid ({len(skill_content)} chars)")

# ============================================================
# 7. Cross-platform script parity
# ============================================================

current_check = "[7] Setup engine integrity"
print("\n[7] Setup engine integrity")

if should_run(7):
    # Setup is one cross-platform Python engine, invoked through Python; no
    # shell or batch wrapper ships (ADR-SCAFFOLD Amendment 2026-06-08). This
    # confirms the engine carries every setup operation.
    ENGINE_FILE = os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.py")

    if os.path.isfile(ENGINE_FILE):
        engine = read_file(ENGINE_FILE)
        # Operations the engine must perform, by literal token. Tokens are
        # chosen to survive os.path.join (no embedded separators).
        ENGINE_MARKERS = [
            "def activate", "def scaffold", "def copy_template", "def remove_path",
            "core.hooksPath", "sync-claude-rules.py", "validate-system.py",
            "settings.json", "config.json", "init",
        ]
        for marker in ENGINE_MARKERS:
            if marker in engine:
                result("PASS", f"engine: {marker}")
            else:
                result("FAIL", f"engine: {marker} -- missing from repository-setup.py")
    elif os.path.isfile(os.path.join(".claude", "setup-complete")):
        result("PASS", "setup engine removed post-setup (harness-eject Category A)")
    else:
        result("FAIL", f"{ENGINE_FILE} -- missing (setup engine)")

# ============================================================
# 8. Hook config validation
# ============================================================

current_check = "[8] Hook config validation"
print("\n[8] Hook config validation")

if should_run(8):
    OBSERVE_REL = ".github/scripts/learning/observe.py"
    observe_path = os.path.join(LEARNING_SCRIPTS_DIR, "observe.py")
    if os.path.isfile(SETTINGS_FILE):
        try:
            hook_cfg = json.loads(read_file(SETTINGS_FILE))
            result("PASS", "settings.json -- valid JSON")
        except json.JSONDecodeError as e:
            hook_cfg = None
            result("FAIL", f"settings.json -- invalid JSON: {e}")

        if hook_cfg:
            hooks_root = hook_cfg.get("hooks", {})
            if not hooks_root:
                result("FAIL", "settings.json -- no 'hooks' block (learning pipeline would be inert)")
            expected_events = {"PreToolUse", "PostToolUse", "SessionStart", "SessionEnd"}
            found_events = set(hooks_root.keys())
            for expected in sorted(expected_events):
                if expected in found_events:
                    result("PASS", f"{expected} -- event registered in settings.json")
                else:
                    result("FAIL", f"{expected} -- event missing from settings.json")
            for event_name, event_list in hooks_root.items():
                for group in event_list:
                    for hook in group.get("hooks", []):
                        cmd = hook.get("command", "").replace("\\", "/")
                        if OBSERVE_REL in cmd:
                            if os.path.isfile(observe_path):
                                result("PASS", f"{event_name} -- runs observe.py")
                            else:
                                result("FAIL", f"{event_name} -- observe.py missing at {observe_path}")
                        else:
                            result("FAIL", f"{event_name} -- command does not invoke {OBSERVE_REL}")
    else:
        result("FAIL", "settings.json -- missing (.claude/settings.json registers the learning hooks)")

# ============================================================
# 9. Learning config schema validation
# ============================================================

current_check = "[9] Learning config schema"
print("\n[9] Learning config schema")

if should_run(9):
    REQUIRED_THRESHOLDS = [
        "min_observations_before_analysis",
        "proposal_confidence_threshold",
        "commit_nudge_observation_count",
        "commit_nudge_proposal_count",
        "pending_proposal_soft_cap",
        "correction_seed_confidence",
        "memory_curation_nudge_blocks",
    ]
    REQUIRED_STALENESS = [
        "proposal_decay_sessions",
        "proposal_archive_sessions",
        "instinct_decay_per_sessions",
        "instinct_decay_session_window",
        "contradiction_penalty",
    ]
    # Date-based keys removed by the evidence-based staleness ADR; their
    # presence means the config migration has not run or regressed.
    FORBIDDEN_STALENESS = [
        "proposal_decay_days",
        "proposal_archive_days",
        "instinct_decay_per_month",
    ]

    if os.path.isfile(CONFIG_FILE):
        try:
            cfg = json.loads(read_file(CONFIG_FILE))
            result("PASS", "config.json -- valid JSON")
        except json.JSONDecodeError as e:
            cfg = None
            result("FAIL", f"config.json -- invalid JSON: {e}")

        if cfg:
            thresholds = cfg.get("thresholds", {})
            staleness = cfg.get("staleness", {})
            if not thresholds:
                result("FAIL", "config.json -- missing 'thresholds' section")
            if not staleness:
                result("FAIL", "config.json -- missing 'staleness' section")
            for key in REQUIRED_THRESHOLDS:
                if key in thresholds:
                    result("PASS", f"thresholds.{key} = {thresholds[key]}")
                else:
                    result("FAIL", f"thresholds.{key} -- missing")
            for key in REQUIRED_STALENESS:
                if key in staleness:
                    result("PASS", f"staleness.{key} = {staleness[key]}")
                else:
                    result("FAIL", f"staleness.{key} -- missing")
            for key in FORBIDDEN_STALENESS:
                if key in staleness:
                    result("FAIL", f"staleness.{key} -- date-based key "
                                   "present (config migration not applied)")
                else:
                    result("PASS", f"staleness.{key} -- absent (migrated)")
    else:
        result("FAIL", "config.json -- missing")

# ============================================================
# 10. Python syntax check
# ============================================================

current_check = "[10] Python syntax check"
print("\n[10] Python syntax check")

if should_run(10):
    for search_dir in [SCRIPTS_DIR, LEARNING_SCRIPTS_DIR, SETUP_SCRIPTS_DIR]:
        if os.path.isdir(search_dir):
            for pyfile in sorted(glob.glob(os.path.join(search_dir, "*.py"))):
                try:
                    py_compile.compile(pyfile, doraise=True)
                    result("PASS", f"{pyfile} -- syntax OK")
                except py_compile.PyCompileError as e:
                    result("FAIL", f"{pyfile} -- {e}")

# ============================================================
# 11. Workflow YAML validation
# ============================================================

current_check = "[11] Workflow YAML validation"
print("\n[11] Workflow YAML validation")

if should_run(11):
    if os.path.isdir(WORKFLOWS_DIR):
        for ymlfile in sorted(glob.glob(os.path.join(WORKFLOWS_DIR, "*.yml"))):
            fname = os.path.basename(ymlfile)
            try:
                yml_content = read_file(ymlfile)
                errors = []
                if not yml_content.strip():
                    errors.append("empty file")
                if "name:" not in yml_content:
                    errors.append("missing 'name:' field")
                if "on:" not in yml_content and "on :" not in yml_content:
                    errors.append("missing 'on:' trigger")
                if "jobs:" not in yml_content:
                    errors.append("missing 'jobs:' section")
                for i, line in enumerate(yml_content.split("\n"), 1):
                    if line.startswith("\t"):
                        errors.append(f"line {i}: tab indentation (YAML requires spaces)")
                        break
                if errors:
                    result("FAIL", f"{fname} -- {'; '.join(errors)}")
                else:
                    result("PASS", f"{fname} -- structure OK")
            except OSError as e:
                result("FAIL", f"{fname} -- {e}")

# ============================================================
# 12. Pipeline chain validation
# ============================================================

current_check = "[12] Pipeline chain validation"
print("\n[12] Pipeline chain validation")

if should_run(12):
    PIPELINE = [
        (os.path.join(LEARNING_SCRIPTS_DIR, "observe.py"), "analyze.py"),
        (os.path.join(LEARNING_SCRIPTS_DIR, "analyze.py"), "propose.py"),
    ]
    for caller, expected_target in PIPELINE:
        caller_name = os.path.basename(caller)
        if not os.path.isfile(caller):
            result("FAIL", f"{caller_name} -- missing, cannot check chain")
            continue
        caller_content = read_file(caller)
        if expected_target in caller_content:
            target_path = os.path.join(LEARNING_SCRIPTS_DIR, expected_target)
            if os.path.isfile(target_path):
                result("PASS", f"{caller_name} -> {expected_target} -- chain valid")
            else:
                result("FAIL", f"{caller_name} -> {expected_target} -- target missing")
        else:
            result("FAIL", f"{caller_name} -- no reference to {expected_target}")

# ============================================================
# 13. Gitignore coverage
# ============================================================

current_check = "[13] Gitignore coverage"
print("\n[13] Gitignore coverage")

if should_run(13):
    REQUIRED_IGNORES = [
        "observations.jsonl", "proposals.archive/", "instincts/",
        "instincts.archive/", ".session-notices/", "session-delta.md",
        "last-modified.json", "session-counter.json",
    ]
    if os.path.isfile(".gitignore"):
        gitignore = read_file(".gitignore")
        for pattern in REQUIRED_IGNORES:
            if pattern in gitignore:
                result("PASS", f".gitignore covers {pattern}")
            else:
                result("FAIL", f".gitignore missing {pattern}")
    else:
        result("FAIL", ".gitignore -- missing")

# ============================================================
# 14. Agent discoverability (Copilot + Claude completeness)
# ============================================================

current_check = "[14] Agent discoverability"
print("\n[14] Agent discoverability")

if should_run(14):
    hub_content = ""
    if os.path.isfile(HUB_SRC):
        hub_content = read_file(HUB_SRC)

    for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
        fname = os.path.basename(src)
        first = read_file(src)[:50]
        if first.strip().startswith("<!-- DEPRECATED"):
            continue
        short_name = fname.replace(".instructions.md", "")
        if fname in hub_content or short_name in hub_content:
            result("PASS", f"hub refs instruction: {fname}")
        else:
            result("FAIL", f"hub missing instruction: {fname} -- not discoverable")

    if os.path.isdir(SKILLS_DIR):
        for skill_dir in sorted(os.listdir(SKILLS_DIR)):
            skill_path = os.path.join(SKILLS_DIR, skill_dir, "SKILL.md")
            if not os.path.isfile(skill_path):
                continue
            ref_unix = ".github/skills/" + skill_dir + "/SKILL.md"
            if ref_unix in hub_content or skill_dir in hub_content:
                result("PASS", f"hub refs skill: {skill_dir}")
            else:
                result("FAIL", f"hub missing skill: {skill_dir} -- not discoverable")

    if os.path.isdir(DEST_DIR):
        for rule_file in sorted(os.listdir(DEST_DIR)):
            if not rule_file.endswith(".md"):
                continue
            expected_src = rule_file.replace(".md", ".instructions.md")
            src_path = os.path.join(SRC_DIR, expected_src)
            if os.path.isfile(src_path):
                result("PASS", f"rule has source: {rule_file} <- {expected_src}")
            else:
                result("FAIL", f"rule orphaned: {rule_file} -- no source instruction")

    if os.path.isfile(HUB_DEST) and hub_content:
        claude_hub = read_file(HUB_DEST)
        clean_hub = read_file(HUB_SRC)
        if claude_hub == clean_hub:
            result("PASS", "Claude entry point (CLAUDE.md) matches Copilot hub")
        else:
            result("FAIL", "Claude entry point (CLAUDE.md) diverged -- agents see different content")
    else:
        if not os.path.isfile(HUB_DEST):
            result("FAIL", "Claude entry point (CLAUDE.md) missing")

# ============================================================
# 15. CUSTOMIZE marker audit
# ============================================================

current_check = "[15] CUSTOMIZE marker audit"
print("\n[15] CUSTOMIZE marker audit")

# Shared by sections 15-17; defined unconditionally so an incremental run
# of 16 or 17 without 15 does not hit a NameError.
SETUP_COMPLETE = os.path.join(".claude", "setup-complete")
setup_done = os.path.isfile(SETUP_COMPLETE)

if should_run(15):
    customize_count = 0
    customize_files = set()
    scan_dirs = [SRC_DIR, os.path.join(".github", "docs"), "."]
    scan_patterns = []
    for d in scan_dirs:
        scan_patterns.extend(glob.glob(os.path.join(d, "*.md")))
    scan_patterns.extend(glob.glob(os.path.join(SRC_DIR, "*.instructions.md")))
    seen_scan = set()
    for md in sorted(scan_patterns):
        if md in seen_scan or ".git/" in md or "node_modules/" in md:
            continue
        seen_scan.add(md)
        if not os.path.isfile(md):
            continue
        scan_content = read_file(md)
        matches = [m.start() for m in re.finditer(r"<!--\s*CUSTOMIZE", scan_content)]
        if matches:
            customize_count += len(matches)
            customize_files.add(md)
    if customize_count == 0:
        result("PASS", "no CUSTOMIZE markers remaining")
    elif setup_done:
        result("WARN", f"{customize_count} CUSTOMIZE marker(s) in {len(customize_files)} file(s) after setup")
        for cf in sorted(customize_files):
            result("WARN", f"  {cf}")
    else:
        result("PASS", f"{customize_count} CUSTOMIZE marker(s) in {len(customize_files)} file(s) (pre-setup, expected)")

# ============================================================
# 16. Stack-specific code standards check
# ============================================================

current_check = "[16] Stack-specific code standards"
print("\n[16] Stack-specific code standards")

if should_run(16):
    stack_files = glob.glob(os.path.join(SRC_DIR, "*-code-standards.instructions.md"))
    if stack_files:
        for sf in stack_files:
            result("PASS", f"stack standards: {os.path.basename(sf)}")
    elif setup_done:
        result("WARN", "no stack-specific code standards file found (expected after project-setup)")
    else:
        result("PASS", "no stack-specific code standards (pre-setup, expected)")

# ============================================================
# 17. Patterns registry content check
# ============================================================

current_check = "[17] Patterns registry content"
print("\n[17] Patterns registry content")

if should_run(17):
    PATTERNS_FILE = os.path.join(SRC_DIR, "patterns.instructions.md")
    if os.path.isfile(PATTERNS_FILE):
        patterns_content = read_file(PATTERNS_FILE)
        headings = re.findall(r"^## (.+)$", patterns_content, re.MULTILINE)
        real_headings = [h for h in headings if "[Pattern Name]" not in h]
        if real_headings:
            result("PASS", f"patterns registry has {len(real_headings)} pattern(s)")
        elif setup_done:
            result("WARN", "patterns registry is empty (consider running convention-discovery)")
        else:
            result("PASS", "patterns registry is placeholder (pre-setup, expected)")
    else:
        result("FAIL", "patterns.instructions.md -- missing")

# ============================================================
# 18. System-index completeness
# ============================================================

current_check = "[18] System-index completeness"
print("\n[18] System-index completeness")

if should_run(18):
    if os.path.isfile(SYSTEM_INDEX):
        index_content = read_file(SYSTEM_INDEX)

        for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
            fname = os.path.basename(src)
            src_content = read_file(src)
            if src_content.strip().startswith("<!-- DEPRECATED"):
                continue
            if fname in index_content:
                result("PASS", f"index lists instruction: {fname}")
            else:
                result("FAIL", f"index missing instruction: {fname}")
            apply_match = re.search(r'applyTo:\s*["\']?([^"\'\n]+)["\']?', src_content)
            if apply_match:
                actual_scope = apply_match.group(1).strip()
                if actual_scope in index_content:
                    result("PASS", f"index scope matches: {fname} ({actual_scope})")
                else:
                    result("WARN", f"index scope may be stale for {fname} (expected {actual_scope})")

        if os.path.isdir(SKILLS_DIR):
            for skill_dir in sorted(os.listdir(SKILLS_DIR)):
                skill_path = os.path.join(SKILLS_DIR, skill_dir, "SKILL.md")
                if not os.path.isfile(skill_path):
                    continue
                if skill_dir in index_content:
                    result("PASS", f"index lists skill: {skill_dir}")
                else:
                    result("FAIL", f"index missing skill: {skill_dir}")
    else:
        result("FAIL", "system-index.md -- missing, cannot check completeness")

    # 18b: Skills README catalog completeness
    skills_readme = os.path.join(SKILLS_DIR, "README.md")
    if os.path.isfile(skills_readme):
        readme_content = read_file(skills_readme)
        if os.path.isdir(SKILLS_DIR):
            for skill_dir in sorted(os.listdir(SKILLS_DIR)):
                skill_path = os.path.join(SKILLS_DIR, skill_dir, "SKILL.md")
                if not os.path.isfile(skill_path):
                    continue
                if skill_dir in readme_content:
                    result("PASS", f"skills README lists skill: {skill_dir}")
                else:
                    result("FAIL", f"skills README missing skill: {skill_dir}")
    else:
        result("FAIL", "skills/README.md -- missing, cannot check catalog")

    # 18c: Instructions README completeness
    instructions_readme = os.path.join(SRC_DIR, "README.md")
    if os.path.isfile(instructions_readme):
        inst_readme_content = read_file(instructions_readme)
        for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
            fname = os.path.basename(src)
            src_content = read_file(src)
            if src_content.strip().startswith("<!-- DEPRECATED"):
                continue
            short_name = fname.replace(".instructions.md", "")
            if short_name in inst_readme_content:
                result("PASS", f"instructions README lists: {short_name}")
            else:
                result("FAIL", f"instructions README missing: {short_name}")
    else:
        result("FAIL", "instructions/README.md -- missing, cannot check catalog")

    # 18d: Docs README completeness
    DOCS_DIR_README = os.path.join(".github", "docs")
    docs_readme = os.path.join(DOCS_DIR_README, "README.md")
    if os.path.isfile(docs_readme):
        docs_readme_content = read_file(docs_readme)
        for gf in sorted(os.listdir(DOCS_DIR_README)):
            if gf == "README.md":
                continue
            if not gf.endswith(".md"):
                continue
            if gf in docs_readme_content:
                result("PASS", f"docs README lists: {gf}")
            else:
                result("FAIL", f"docs README missing: {gf}")
    else:
        result("FAIL", "docs/README.md -- missing, cannot check catalog")

    # 18e: Scripts README completeness
    scripts_readme = os.path.join(SCRIPTS_DIR, "README.md")
    if os.path.isfile(scripts_readme):
        scripts_readme_content = read_file(scripts_readme)
        for pyfile in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))):
            pyname = os.path.basename(pyfile)
            if pyname in scripts_readme_content:
                result("PASS", f"scripts README lists: {pyname}")
            else:
                result("FAIL", f"scripts README missing: {pyname}")
        for subdir in sorted(os.listdir(SCRIPTS_DIR)):
            subdir_path = os.path.join(SCRIPTS_DIR, subdir)
            if os.path.isdir(subdir_path) and subdir != "__pycache__":
                if subdir in scripts_readme_content:
                    result("PASS", f"scripts README lists subdir: {subdir}/")
                else:
                    result("FAIL", f"scripts README missing subdir: {subdir}/")
    else:
        result("FAIL", "scripts/README.md -- missing, cannot check catalog")

# ============================================================
# 19. Content overlap detection
# ============================================================

current_check = "[19] Content overlap detection"
print("\n[19] Content overlap detection")

if should_run(19):
    def normalize_sentences(text):
        """Extract normalized sentences from markdown body (skip frontmatter)."""
        parts = text.split("---", 2)
        body = parts[2] if len(parts) >= 3 else text
        body = re.sub(r'```[\s\S]*?```', '', body)
        body = re.sub(r'<!--[\s\S]*?-->', '', body)
        body = re.sub(r'\|[^\n]+\|', '', body)
        body = re.sub(r'#+\s+', '', body)
        body = re.sub(r'[*_`\[\]()]', '', body)
        sentences = set()
        for line in body.split('\n'):
            line = line.strip().strip('-').strip()
            if len(line) > 20:
                sentences.add(line.lower())
        return sentences

    instruction_bodies = {}
    for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
        fname = os.path.basename(src)
        inst_content = read_file(src)
        if inst_content.strip().startswith("<!-- DEPRECATED"):
            continue
        instruction_bodies[fname] = normalize_sentences(inst_content)

    checked_pairs = set()
    for a, sents_a in instruction_bodies.items():
        for b, sents_b in instruction_bodies.items():
            if a >= b:
                continue
            pair = (a, b)
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            if not sents_a or not sents_b:
                continue
            overlap = sents_a & sents_b
            union = sents_a | sents_b
            jaccard = len(overlap) / len(union) if union else 0
            if jaccard > 0.30:
                result("WARN", f"{a} <-> {b}: {jaccard:.0%} overlap ({len(overlap)} shared sentences)")
            else:
                result("PASS", f"{a} <-> {b}: {jaccard:.0%} overlap")

# ============================================================
# 20. Thin-rules / deep-docs contract
# ============================================================

current_check = "[20] Thin-rules / deep-docs contract"
print("\n[20] Thin-rules / deep-docs contract")

if should_run(20):
    DOCS_DIR = os.path.join(".github", "docs")
    guide_directive_re = re.compile(
        r'^>\s*\*\*Full guidance:\*\*\s*`([^`]+)`', re.MULTILINE
    )
    directives_found = {}
    for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
        fname = os.path.basename(src)
        dir_content = read_file(src)
        match = guide_directive_re.search(dir_content)
        if match:
            guide_path = match.group(1)
            directives_found[fname] = guide_path
            if os.path.isfile(guide_path):
                result("PASS", f"{fname} -> {guide_path}")
            else:
                result("FAIL", f"{fname} -> {guide_path} -- guide file missing")

    if os.path.isdir(DOCS_DIR):
        # A guide's thin companion is usually an instruction file, but a
        # guide may instead be the deep half of a root README summary.
        root_readme = read_file("README.md") if os.path.isfile("README.md") else ""
        for gf in sorted(os.listdir(DOCS_DIR)):
            if not gf.endswith("-guide.md"):
                continue
            guide_rel = os.path.join(DOCS_DIR, gf).replace("\\", "/")
            found_directive = False
            for inst_fname, directive_path in directives_found.items():
                norm_directive = directive_path.replace("\\", "/")
                if norm_directive == guide_rel or os.path.basename(norm_directive) == gf:
                    found_directive = True
                    break
            if found_directive:
                result("PASS", f"{gf} has matching instruction directive")
            elif gf in root_readme:
                result("PASS", f"{gf} referenced from root README (README companion)")
            else:
                result("WARN", f"{gf} -- no instruction file references this guide")

    # Guide files carry the depth deliberately and are read on demand,
    # so they are exempt from the 4,000-char cap (see system-index.md).
    # Only .github/instructions/ and .claude/rules/ are size-capped.

# ============================================================
# 21. Learning pipeline consistency
# ============================================================

current_check = "[21] Learning pipeline consistency"
print("\n[21] Learning pipeline consistency")

if should_run(21):
    OBSERVE_PY = os.path.join(LEARNING_SCRIPTS_DIR, "observe.py")
    ANALYZE_PY = os.path.join(LEARNING_SCRIPTS_DIR, "analyze.py")
    PROPOSE_PY = os.path.join(LEARNING_SCRIPTS_DIR, "propose.py")

    if hook_cfg:
        for event_name, event_list in hooks_root.items():
            for i, group in enumerate(event_list):
                if "matcher" not in group:
                    result("FAIL", f"settings.json {event_name}[{i}] -- missing 'matcher' field")
                elif "hooks" not in group:
                    result("FAIL", f"settings.json {event_name}[{i}] -- missing 'hooks' field")
                else:
                    result("PASS", f"settings.json {event_name}[{i}] -- schema complete")

    if os.path.isfile(OBSERVE_PY) and os.path.isfile(PROPOSE_PY):
        obs_content = read_file(OBSERVE_PY)
        prop_content = read_file(PROPOSE_PY)
        cd_match = re.search(r'def classify_domain\b.*?(?=\ndef |\Z)', obs_content, re.DOTALL)
        if cd_match:
            cd_body = cd_match.group()
            domains = set(re.findall(r'return\s+"([^"]+)"', cd_body))
            mt_match = re.search(r'def map_target_file\b.*?(?=\ndef |\Z)', prop_content, re.DOTALL)
            if mt_match:
                mt_body = mt_match.group()
                eq_domains = set(re.findall(r'domain\s*==\s*"([^"]+)"', mt_body))
                for in_match in re.finditer(r'domain\s+in\s*\(([^)]+)\)', mt_body):
                    eq_domains.update(re.findall(r'"([^"]+)"', in_match.group(1)))
                for domain in sorted(domains):
                    if domain in eq_domains:
                        result("PASS", f"domain '{domain}' -- mapped in propose.py")
                    else:
                        result("FAIL", f"domain '{domain}' -- returned by observe.py but not mapped in propose.py")
            else:
                result("FAIL", "propose.py -- map_target_file() not found")
        else:
            result("FAIL", "observe.py -- classify_domain() not found")

    if os.path.isfile(PROPOSE_PY) and os.path.isfile(".gitignore"):
        prop_src = read_file(PROPOSE_PY)
        archive_match = re.search(r'ARCHIVE_DIR\s*=.*["\']([^"\'\n]+)["\']', prop_src)
        if archive_match:
            archive_name = archive_match.group(1)
            gitignore = read_file(".gitignore")
            if archive_name in gitignore:
                result("PASS", f"archive dir '{archive_name}' -- covered in .gitignore")
            else:
                result("FAIL", f"archive dir '{archive_name}' -- missing from .gitignore")
        else:
            result("FAIL", "propose.py -- ARCHIVE_DIR not found")

    if os.path.isfile(OBSERVE_PY) and hook_cfg:
        obs_src = read_file(OBSERVE_PY)
        checked_events = set(re.findall(r'event_name\s*==\s*"([^"]+)"', obs_src))
        registered = set(hooks_root.keys())
        internal_events = {"_analysis_marker"}
        for ev in sorted(checked_events):
            if ev in registered:
                result("PASS", f"event '{ev}' -- registered in settings.json")
            elif ev in internal_events:
                result("PASS", f"event '{ev}' -- internal marker (not a hook event)")
            else:
                result("FAIL", f"event '{ev}' -- checked in observe.py but not registered in settings.json")

    if os.path.isfile(OBSERVE_PY):
        obs_src = read_file(OBSERVE_PY)
        bo_match = re.search(r'def build_observation\b.*?(?=\ndef |\Z)', obs_src, re.DOTALL)
        if bo_match:
            bo_body = bo_match.group()
            has_path_check = '".github/instructions/"' in bo_body or '".claude/rules/"' in bo_body
            has_normalization = '.replace("\\\\", "/")' in bo_body or ".replace('\\\\', '/')" in bo_body
            if has_path_check and has_normalization:
                result("PASS", "build_observation() -- path normalization present")
            elif has_path_check and not has_normalization:
                result("FAIL", "build_observation() -- path checks without normalization (Windows compat)")
            else:
                result("PASS", "build_observation() -- no path checks to normalize")

    # Evidence-based staleness model (ADR): session-clock only, no date
    # arithmetic; confirmed marker checked before decay; archive reasons
    # recorded; relevance pass present.
    SESSION_CLOCK_PY = os.path.join(LEARNING_SCRIPTS_DIR, "session_clock.py")
    if os.path.isfile(SESSION_CLOCK_PY):
        result("PASS", "session_clock.py -- present")
    else:
        result("FAIL", "session_clock.py -- missing (session counter, "
                       "migration, permanence helpers)")

    for script_name in ("propose.py", "analyze.py", "observe.py"):
        spath = os.path.join(LEARNING_SCRIPTS_DIR, script_name)
        if not os.path.isfile(spath):
            continue
        ssrc = read_file(spath)
        for dead_key in ("proposal_decay_days", "proposal_archive_days",
                         "instinct_decay_per_month"):
            if re.search(rf'["\']{dead_key}["\']\s*[,:)\]]', ssrc):
                result("FAIL", f"{script_name} -- references date-based "
                               f"key '{dead_key}' (must be removed, "
                               "not flagged off)")
                break
        else:
            result("PASS", f"{script_name} -- no date-based staleness keys")

    if os.path.isfile(PROPOSE_PY):
        prop_src_st = read_file(PROPOSE_PY)
        if "is_confirmed" in prop_src_st and "content_is_confirmed" in prop_src_st:
            result("PASS", "propose.py -- confirmed-marker check present")
        else:
            result("FAIL", "propose.py -- staleness passes missing the "
                           "confirmed-marker exemption")
        if "archived_reason" in prop_src_st:
            result("PASS", "propose.py -- archive reasons recorded")
        else:
            result("FAIL", "propose.py -- proposals archived without a "
                           "recorded reason")

    if os.path.isfile(ANALYZE_PY):
        analyze_src_st = read_file(ANALYZE_PY)
        if "def relevance_pass" in analyze_src_st:
            result("PASS", "analyze.py -- relevance pass present")
        else:
            result("FAIL", "analyze.py -- relevance pass missing")
        if "irrelevant" in analyze_src_st:
            result("PASS", "analyze.py -- 'irrelevant' archive reason recorded")
        else:
            result("FAIL", "analyze.py -- relevance archive lacks reason")

    if os.path.isfile(OBSERVE_PY):
        obs_src_st = read_file(OBSERVE_PY)
        if "increment_session_count" in obs_src_st:
            result("PASS", "observe.py -- session counter ticks on SessionEnd")
        else:
            result("FAIL", "observe.py -- session counter never incremented")

    # Correction capture privacy boundary (corrections ADR): fixture-driven
    # proof that the correction path emits no raw transcript content. A mock
    # transcript carrying a sentinel secret is parsed; the derived
    # observations must register the correction without the sentinel.
    if os.path.isfile(OBSERVE_PY):
        import subprocess as _subprocess
        PRIVACY_FIXTURE_CHECK = r'''
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(".github", "scripts", "learning"))
import observe
SENTINEL = "SENTINEL-SECRET-axJ93q"
records = [
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Edit",
         "input": {"file_path": "src/billing.py"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "text",
         "text": "no, that's wrong. the API key is " + SENTINEL}]}},
]
fd, path = tempfile.mkstemp(suffix=".jsonl")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
try:
    obs = observe.parse_transcript_for_corrections(path, "fixture-session")
finally:
    os.remove(path)
serialized = json.dumps(obs)
assert obs, "fixture correction not detected"
assert obs[0]["event"] == "correction", "wrong observation type"
assert SENTINEL not in serialized, "raw transcript content leaked"
print("ok")
'''
        try:
            proc = _subprocess.run(
                [sys.executable, "-c", PRIVACY_FIXTURE_CHECK],
                capture_output=True, text=True, timeout=30, cwd=os.getcwd(),
            )
            if proc.returncode == 0 and "ok" in proc.stdout:
                result("PASS", "correction capture -- fixture emits derived "
                               "fields only, no transcript content")
            else:
                detail = (proc.stderr or proc.stdout).strip().splitlines()
                detail = detail[-1] if detail else "no output"
                result("FAIL", f"correction capture privacy check -- {detail}")
        except (OSError, _subprocess.TimeoutExpired) as e:
            result("FAIL", f"correction capture privacy check -- {e}")

    if os.path.isfile(ANALYZE_PY):
        analyze_src = read_file(ANALYZE_PY)
        si_match = re.search(r'def save_instinct\b.*?(?=\ndef |\Z)', analyze_src, re.DOTALL)
        if si_match:
            si_body = si_match.group()
            if 'replace(\'"\',' in si_body or ".replace('\"'," in si_body or '.replace(\\\'"\\\'' in si_body or 'replace(\'"\', ' in si_body or "safe_trigger" in si_body:
                result("PASS", "save_instinct() -- trigger value escaping present")
            else:
                result("FAIL", "save_instinct() -- trigger value not escaped (YAML injection risk)")

# ============================================================
# 22. Workflow, sync, and setup consistency
# ============================================================

current_check = "[22] Workflow/sync/setup consistency"
print("\n[22] Workflow/sync/setup consistency")

if should_run(22):
    SYNC_SCRIPT = os.path.join(SCRIPTS_DIR, "sync-claude-rules.py")
    DOCS_DIR_CHECK = os.path.join(".github", "docs")

    # 22a: Workflow checkout action versions -- flag only clearly outdated
    # majors. New majors ship over time, so do not cap the upper bound;
    # validating against a frozen "latest" would fail legitimate upgrades.
    for wf_name in sorted(os.listdir(WORKFLOWS_DIR)) if os.path.isdir(WORKFLOWS_DIR) else []:
        if not wf_name.endswith(".yml"):
            continue
        wf_path = os.path.join(WORKFLOWS_DIR, wf_name)
        wf_content = read_file(wf_path)
        versions = re.findall(r'actions/checkout@v(\d+)', wf_content)
        for ver in versions:
            if int(ver) < 4:
                result("WARN", f"{wf_name} -- uses actions/checkout@v{ver} (consider updating to v4+)")
            else:
                result("PASS", f"{wf_name} -- actions/checkout@v{ver}")

    # 22b: No ${{ }} interpolation in JS template literals (script injection risk)
    for wf_name in sorted(os.listdir(WORKFLOWS_DIR)) if os.path.isdir(WORKFLOWS_DIR) else []:
        if not wf_name.endswith(".yml"):
            continue
        wf_path = os.path.join(WORKFLOWS_DIR, wf_name)
        wf_content = read_file(wf_path)
        in_script_block = False
        for line_num, line in enumerate(wf_content.splitlines(), 1):
            if "actions/github-script" in line:
                in_script_block = True
            elif in_script_block and line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                in_script_block = False
            if in_script_block and "`" in line and "${{" in line:
                result("FAIL", f"{wf_name}:{line_num} -- ${{{{}}}} inside template literal (script injection risk)")
                break
        else:
            if in_script_block:
                pass
            result("PASS", f"{wf_name} -- no template literal injection")

    # 22c: Workflow label creation -- issues.create with labels should ensure label exists first
    for wf_name in sorted(os.listdir(WORKFLOWS_DIR)) if os.path.isdir(WORKFLOWS_DIR) else []:
        if not wf_name.endswith(".yml"):
            continue
        wf_path = os.path.join(WORKFLOWS_DIR, wf_name)
        wf_content = read_file(wf_path)
        if "issues.create" in wf_content:
            labels_used = re.findall(r"labels:\s*\[([^\]]+)\]", wf_content)
            has_get_label = "issues.getLabel" in wf_content or "issues.createLabel" in wf_content
            if labels_used and not has_get_label:
                result("FAIL", f"{wf_name} -- creates issues with labels but never ensures labels exist")
            elif labels_used:
                result("PASS", f"{wf_name} -- label creation before use")

    # 22d: Sync script applyTo handling -- must split comma-separated values
    if os.path.isfile(SYNC_SCRIPT):
        sync_src = read_file(SYNC_SCRIPT)
        if ".split(" in sync_src and "apply_to" in sync_src.lower():
            result("PASS", "sync-claude-rules.py -- applyTo comma splitting present")
        else:
            result("FAIL", "sync-claude-rules.py -- applyTo not split on comma (multi-value bug)")

    # 22e: Sync script empty applyTo guard
    if os.path.isfile(SYNC_SCRIPT):
        sync_src = read_file(SYNC_SCRIPT)
        if "not apply_to" in sync_src or "empty applyTo" in sync_src.lower():
            result("PASS", "sync-claude-rules.py -- empty applyTo guard present")
        else:
            result("FAIL", "sync-claude-rules.py -- no guard against empty applyTo")

    # 22f: Setup engine activate() guards on .git before installing hooks.
    # Setup is Python-only now (no shell/batch wrappers, ADR-SCAFFOLD Amendment
    # 2026-06-08), so the former shim parity and Python-detection checks are
    # gone with the files they policed.
    ENGINE_SETUP = os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.py")
    if os.path.isfile(ENGINE_SETUP):
        eng_src = read_file(ENGINE_SETUP)
        activate_match = re.search(r'def activate\(.*?(?=\ndef )', eng_src, re.DOTALL)
        if activate_match:
            if ".git" in activate_match.group():
                result("PASS", "repository-setup.py -- activate() checks for .git")
            else:
                result("FAIL", "repository-setup.py -- activate() missing .git check")
        else:
            result("FAIL", "repository-setup.py -- activate() function not found")

    # 22g: Proposals directory must NOT be gitignored (tracked for learning-summary workflow)
    if os.path.isfile(".gitignore"):
        gi_lines = read_file(".gitignore").splitlines()
        proposals_ignored = any(
            line.strip() == ".claude/learning/proposals/"
            or line.strip() == ".claude/learning/proposals"
            for line in gi_lines if not line.strip().startswith("#")
        )
        if proposals_ignored:
            result("FAIL", "proposals/ is gitignored (must be tracked for learning-summary workflow)")
        else:
            result("PASS", "proposals/ is not gitignored (tracked)")

    # 22k: Proposals directory has .gitkeep so it survives empty state
    proposals_gitkeep = os.path.join(LEARNING_DIR, "proposals", ".gitkeep")
    if os.path.isfile(proposals_gitkeep):
        result("PASS", "proposals/.gitkeep exists")
    else:
        result("FAIL", "proposals/.gitkeep missing (empty dir won't be tracked by git)")

    # 22l: Skill files must not hardcode python3 (breaks Windows)
    if os.path.isdir(SKILLS_DIR):
        for skill_name in sorted(os.listdir(SKILLS_DIR)):
            skill_md = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            skill_src = read_file(skill_md)
            python3_cmds = re.findall(r'`python3\s', skill_src)
            if python3_cmds:
                result("FAIL", f"{skill_name}/SKILL.md -- hardcodes python3 (use python for cross-platform)")
            else:
                result("PASS", f"{skill_name}/SKILL.md -- no hardcoded python3")

    # 22m: project-setup SKILL.md lists all instruction files with CUSTOMIZE markers
    setup_skill = os.path.join(SKILLS_DIR, "project-setup", "SKILL.md")
    if os.path.isfile(setup_skill) and os.path.isdir(SRC_DIR):
        setup_src = read_file(setup_skill)
        for inst_file in sorted(os.listdir(SRC_DIR)):
            if not inst_file.endswith(".instructions.md"):
                continue
            inst_path = os.path.join(SRC_DIR, inst_file)
            inst_content = read_file(inst_path)
            if "CUSTOMIZE" in inst_content:
                base = inst_file.replace(".instructions.md", "")
                if inst_file in setup_src or base in setup_src:
                    result("PASS", f"project-setup lists CUSTOMIZE file: {inst_file}")
                else:
                    result("FAIL", f"project-setup missing CUSTOMIZE file: {inst_file}")

# ============================================================
# 23. Template manifest integrity (ah-ide scaffolder)
# ============================================================

current_check = "[23] Template manifests"
print("\n[23] Template manifests")

if should_run(23):
    TEMPLATES_DIR_V = "templates"
    if os.path.isdir(TEMPLATES_DIR_V):
        found_any = False
        for tname in sorted(os.listdir(TEMPLATES_DIR_V)):
            tpath = os.path.join(TEMPLATES_DIR_V, tname)
            if not os.path.isdir(tpath):
                continue
            mpath = os.path.join(tpath, "manifest.json")
            if not os.path.isfile(mpath):
                result("FAIL", f"{tname}/ has no manifest.json")
                continue
            found_any = True
            try:
                manifest = json.loads(read_file(mpath))
            except (json.JSONDecodeError, ValueError) as exc:
                result("FAIL", f"{tname}/manifest.json does not parse: {exc}")
                continue
            missing = [k for k in ("stack", "token", "ide_assets")
                       if k not in manifest]
            if missing:
                result("FAIL",
                       f"{tname}/manifest.json missing: {', '.join(missing)}")
            else:
                result("PASS", f"{tname}/manifest.json declares stack, "
                               "token, ide_assets")
            token = manifest.get("token")
            if token:
                def _token_in_file(fp):
                    # Binary assets (images, icons) cannot carry the token in
                    # text; skip them instead of crashing the whole run.
                    try:
                        return token in read_file(fp)
                    except (UnicodeDecodeError, OSError):
                        return False
                hit = any(token in str(fp) or _token_in_file(fp)
                          for root_, _, files_ in os.walk(tpath)
                          for f_ in files_
                          for fp in [os.path.join(root_, f_)]
                          if f_ != "manifest.json")
                if hit:
                    result("PASS", f"{tname}: token '{token}' present in tree")
                else:
                    result("FAIL", f"{tname}: token '{token}' never appears; "
                                   "--name would have no effect")
            ide_assets = manifest.get("ide_assets", {})
            if isinstance(ide_assets, dict):
                for ide_key, roots in ide_assets.items():
                    for r in roots:
                        if not os.path.exists(os.path.join(tpath, r)):
                            result("FAIL", f"{tname}: ide_assets['{ide_key}'] "
                                           f"path missing: {r}")
            # test_frameworks: when declared, the overlay subtrees must exist.
            # See docs/adr/adr-scaffold-add-test-framework-dimension.md.
            tf = manifest.get("test_frameworks")
            if tf is not None:
                options = tf.get("options")
                default = tf.get("default")
                if not isinstance(options, list) or not options:
                    result("FAIL", f"{tname}: test_frameworks.options must be "
                                   "a non-empty list")
                elif default not in options:
                    result("FAIL", f"{tname}: test_frameworks.default "
                                   f"'{default}' not in options")
                else:
                    ok = True
                    for opt in options:
                        odir = os.path.join(tpath, "_testfw", opt)
                        has_files = os.path.isdir(odir) and any(
                            files_ for _, _, files_ in os.walk(odir))
                        if not has_files:
                            result("FAIL", f"{tname}: test framework '{opt}' "
                                           f"has no _testfw/{opt}/ overlay")
                            ok = False
                    if ok:
                        result("PASS", f"{tname}: test_frameworks "
                                       f"({', '.join(options)}) have overlays")
        if not found_any:
            result("WARN", "templates/ contains no template directories")
    elif os.path.isfile(os.path.join(".github", "scripts", "scaffold.py")):
        result("WARN", "templates/ missing -- scaffolder has no stacks")
    else:
        result("PASS", "scaffolder and templates removed (harness-eject Category B)")

    # Eject-manifest ADR coverage (template source only). Every harness ADR
    # must be listed in the eject manifest (Category B or C), or it would
    # survive eject and pollute consuming projects. Post-setup, docs/adr/
    # holds the consuming project's own ADRs, so the check gates on the
    # source sentinel.
    if os.path.isfile(os.path.join(".github", "TEMPLATE_SOURCE")):
        EJECT_MANIFEST = os.path.join(".github", "scripts", "eject-manifest.json")
        try:
            _em = json.loads(read_file(EJECT_MANIFEST))
            _listed = {item["path"]
                       for cat in _em.get("categories", {}).values()
                       for item in cat.get("paths", [])}
            _adr_dir = os.path.join("docs", "adr")
            _unlisted = sorted(
                f for f in os.listdir(_adr_dir)
                if f.startswith("adr-") and f.endswith(".md")
                and f"docs/adr/{f}" not in _listed)
            if _unlisted:
                for f in _unlisted:
                    result("FAIL", f"docs/adr/{f} -- not in eject manifest; "
                                   "it would survive eject")
            else:
                result("PASS", "every harness ADR is listed in the eject manifest")
        except (OSError, ValueError, KeyError) as exc:
            result("FAIL", f"eject-manifest ADR coverage check errored: {exc}")
    else:
        result("PASS", "eject-manifest ADR coverage -- skipped (consuming project)")

# ============================================================
# Summary
# ============================================================

print("")
print("=" * 70)
print(f"  PASS: {passes}  FAIL: {fails}  WARN: {warns}")
print("=" * 70)

if issues:
    print("")
    sev_w = max(len(s) for s, _, _ in issues)
    chk_w = max(len(c) for _, c, _ in issues)
    msg_w = max(len(m) for _, _, m in issues)
    header = f"  {'SEV':<{sev_w}}  {'CHECK':<{chk_w}}  {'DETAIL':<{msg_w}}"
    print(header)
    print(f"  {'-' * sev_w}  {'-' * chk_w}  {'-' * msg_w}")
    for sev, chk, msg in issues:
        print(f"  {sev:<{sev_w}}  {chk:<{chk_w}}  {msg:<{msg_w}}")

# Exit non-zero when any check failed, so the pre-commit hook and CI block
# on a broken tree. WARN does not fail the build; only FAIL does.
sys.exit(1 if fails > 0 else 0)
