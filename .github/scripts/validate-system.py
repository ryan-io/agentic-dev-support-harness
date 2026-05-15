#!/usr/bin/env python3
"""
validate-system.py
Automated validation of the project setup template system.
Checks file existence, size limits, sync state, frontmatter, cross-references,
cross-platform parity, hook config, config schema, Python syntax, YAML validity,
pipeline chain integrity, and gitignore coverage.

Run from repo root: python .github/scripts/validate-system.py
Exit code: 0 = all pass, 1 = failures found.
"""

import json
import os
import re
import sys
import glob
import py_compile
import tempfile

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


# ============================================================
# 1. File existence
# ============================================================

current_check = "[1] File existence"
print("\n[1] File existence")

LEARNING_SCRIPTS_DIR = os.path.join(SCRIPTS_DIR, "learning")
SETUP_SCRIPTS_DIR = os.path.join(SCRIPTS_DIR, "setup")

REQUIRED_FILES = [
    HUB_SRC, HUB_DEST, SYSTEM_INDEX,
    os.path.join(SCRIPTS_DIR, "sync-claude-rules.py"),
    os.path.join(HOOKS_DIR, "pre-commit"),
    os.path.join(".github", "docs", "adr-template.md"),
    os.path.join(".github", "docs", "br-template.md"),
    os.path.join(".github", "pull_request_template.md"), ".gitignore",
    os.path.join(HOOKS_DIR, "observe.json"),
    os.path.join(LEARNING_SCRIPTS_DIR, "observe.py"),
    os.path.join(LEARNING_SCRIPTS_DIR, "analyze.py"),
    os.path.join(LEARNING_SCRIPTS_DIR, "propose.py"),
    os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.bat"),
    os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.sh"),
    os.path.join(SETUP_SCRIPTS_DIR, "sync.bat"),
    "setup.bat", "setup.sh", "sync.bat",
    CONFIG_FILE,
]

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

if os.path.isfile(HUB_SRC) and os.path.isfile(HUB_DEST):
    with open(HUB_SRC, "r", encoding="utf-8") as f:
        src_content = f.read().replace("\r", "").replace("\x00", "")
    with open(HUB_DEST, "r", encoding="utf-8") as f:
        dest_content = f.read().replace("\r", "").replace("\x00", "")
    if src_content == dest_content:
        result("PASS", "CLAUDE.md matches copilot-instructions.md")
    else:
        result("FAIL", "CLAUDE.md differs -- run sync")
else:
    result("FAIL", "Hub files missing -- cannot compare")


# ============================================================
# 3. Size limits
# ============================================================

current_check = "[3] Size limits (agent-loaded .md <= 4000 chars; README.md exempt)"
print("\n[3] Size limits (agent-loaded .md <= 4000 chars; README.md exempt)")

md_files = set(glob.glob("**/*.md", recursive=True))
md_files.update(glob.glob(".github/**/*.md", recursive=True))
md_files.update(glob.glob(".claude/**/*.md", recursive=True))
size_records = []
for md in sorted(md_files):
    if ".git/" in md or "node_modules/" in md:
        continue
    # README.md files are human-facing, not loaded by agents -- exempt from char limit
    if os.path.basename(md).lower() == "readme.md":
        continue
    with open(md, "r", encoding="utf-8") as f:
        size = len(f.read())
    size_records.append((md, size))
    if size > MAX_CHARS:
        result("FAIL", f"{md} -- {size} chars (limit {MAX_CHARS})")
    else:
        result("PASS", f"{md} -- {size} chars")

# Headroom report: show the 3 tightest files
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

src_files = sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md")))
expected_copies = set()

for src in src_files:
    filename = os.path.basename(src)
    with open(src, "r", encoding="utf-8") as f:
        content = f.read().replace("\r", "").replace("\x00", "")

    if content.strip().startswith("<!-- DEPRECATED"):
        result("PASS", f"{filename} -- deprecated, skipped")
        continue

    match = re.search(r'applyTo:\s*["\']?([^"\'\n]+)["\']?', content)
    if not match:
        result("FAIL", f"{filename} -- missing applyTo frontmatter")
        continue
    apply_to = match.group(1).strip()
    result("PASS", f"{filename} -- applyTo: {apply_to}")

    dest_name = filename.replace(".instructions", "")
    dest_path = os.path.join(DEST_DIR, dest_name)
    expected_copies.add(dest_name)

    if not os.path.isfile(dest_path):
        result("FAIL", f"{dest_name} -- missing in {DEST_DIR}")
        continue

    with open(dest_path, "r", encoding="utf-8") as f:
        dest_content = f.read().replace("\r", "").replace("\x00", "")
    paths_match = re.search(r'paths:\s*\["?([^"\]\n]+)"?\]', dest_content)
    if not paths_match:
        result("FAIL", f"{dest_name} -- missing paths frontmatter")
    elif paths_match.group(1).strip() != apply_to:
        result("FAIL", f"{dest_name} -- paths mismatch")
    else:
        result("PASS", f"{dest_name} -- synced, paths: {apply_to}")

if os.path.isdir(DEST_DIR):
    for f in os.listdir(DEST_DIR):
        if f.endswith(".md") and f not in expected_copies:
            result("WARN", f"{DEST_DIR}/{f} -- orphaned")


# ============================================================
# 5. Cross-references (hub + index)
# ============================================================

current_check = "[5] Cross-references"
print("\n[5] Cross-references")


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
    with open(HUB_SRC, "r", encoding="utf-8") as f:
        check_path_refs(f.read(), "hub")

if os.path.isfile(SYSTEM_INDEX):
    with open(SYSTEM_INDEX, "r", encoding="utf-8") as f:
        check_path_refs(f.read(), "index")


# ============================================================
# 6. Skills validation
# ============================================================

current_check = "[6] Skills validation"
print("\n[6] Skills validation")

if os.path.isdir(SKILLS_DIR):
    for skill_dir in sorted(os.listdir(SKILLS_DIR)):
        skill_full = os.path.join(SKILLS_DIR, skill_dir)
        # Skip non-directory entries (e.g. README.md, .DS_Store)
        if not os.path.isdir(skill_full):
            continue
        skill_path = os.path.join(skill_full, "SKILL.md")
        if not os.path.isfile(skill_path):
            result("FAIL", f"{skill_dir} -- no SKILL.md")
            continue
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            result("FAIL", f"{skill_dir} -- missing frontmatter")
        elif "name:" not in content.split("---")[1]:
            result("FAIL", f"{skill_dir} -- missing name")
        else:
            result("PASS", f"{skill_dir} -- valid ({len(content)} chars)")


# ============================================================
# 7. Cross-platform script parity
# ============================================================

current_check = "[7] Cross-platform script parity"
print("\n[7] Cross-platform script parity")

BAT_FILE = os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.bat")
SH_FILE = os.path.join(SETUP_SCRIPTS_DIR, "repository-setup.sh")

PARITY_MARKERS = [
    ("git init", "git init"),
    (".claude/rules", ".claude/rules" if os.name != "nt" else ".claude\\rules"),
    ("learning/config.json", "learning/config.json"),
    ("core.hooksPath", "core.hooksPath"),
    ("sync-claude-rules.py", "sync-claude-rules.py"),
]

if os.path.isfile(BAT_FILE) and os.path.isfile(SH_FILE):
    with open(BAT_FILE, "r", encoding="utf-8") as f:
        bat = f.read().lower()
    with open(SH_FILE, "r", encoding="utf-8") as f:
        sh = f.read().lower()
    for label, _ in PARITY_MARKERS:
        search = label.lower()
        in_bat = search in bat or search.replace("/", "\\") in bat
        in_sh = search in sh
        if in_bat and in_sh:
            result("PASS", f"parity: {label}")
        elif in_bat and not in_sh:
            result("FAIL", f"parity: {label} -- in .bat but missing from .sh")
        elif in_sh and not in_bat:
            result("FAIL", f"parity: {label} -- in .sh but missing from .bat")
        else:
            result("FAIL", f"parity: {label} -- missing from both")
else:
    if not os.path.isfile(BAT_FILE):
        result("FAIL", f"{BAT_FILE} -- missing")
    if not os.path.isfile(SH_FILE):
        result("FAIL", f"{SH_FILE} -- missing")


# ============================================================
# 8. Hook config validation
# ============================================================

current_check = "[8] Hook config validation"
print("\n[8] Hook config validation")

HOOK_FILE = os.path.join(HOOKS_DIR, "observe.json")
if os.path.isfile(HOOK_FILE):
    with open(HOOK_FILE, "r", encoding="utf-8") as f:
        try:
            hook_cfg = json.load(f)
            result("PASS", "observe.json -- valid JSON")
        except json.JSONDecodeError as e:
            hook_cfg = None
            result("FAIL", f"observe.json -- invalid JSON: {e}")

    if hook_cfg:
        hooks_root = hook_cfg.get("hooks", {})
        for event_name, event_list in hooks_root.items():
            for group in event_list:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    win = hook.get("windows", "")

                    # Check windows override exists
                    if not win:
                        result("FAIL", f"{event_name} -- missing windows override")
                    else:
                        result("PASS", f"{event_name} -- windows override present")

                    # Extract script path from command and verify it exists
                    cmd_match = re.search(r'["\']?\$CLAUDE_PROJECT_DIR/(.+?)["\']?$', cmd)
                    if cmd_match:
                        script_rel = cmd_match.group(1)
                        if os.path.isfile(script_rel):
                            result("PASS", f"{event_name} -- script exists: {script_rel}")
                        else:
                            result("FAIL", f"{event_name} -- script missing: {script_rel}")

                    # Verify unix uses python3, windows uses python
                    if "python3" in cmd:
                        result("PASS", f"{event_name} -- unix command uses python3")
                    else:
                        result("FAIL", f"{event_name} -- unix command should use python3")
                    if win and re.search(r'\bpython\b(?!3)', win):
                        result("PASS", f"{event_name} -- windows command uses python")
                    elif win:
                        result("FAIL", f"{event_name} -- windows command should use python (not python3)")


# ============================================================
# 9. Learning config schema validation
# ============================================================

current_check = "[9] Learning config schema"
print("\n[9] Learning config schema")

REQUIRED_THRESHOLDS = [
    "min_observations_before_analysis",
    "proposal_confidence_threshold",
    "commit_nudge_observation_count",
    "commit_nudge_proposal_count",
]
REQUIRED_STALENESS = [
    "proposal_decay_days",
    "proposal_archive_days",
    "instinct_decay_per_month",
]

if os.path.isfile(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            cfg = json.load(f)
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
else:
    result("FAIL", "config.json -- missing")


# ============================================================
# 10. Python syntax check
# ============================================================

current_check = "[10] Python syntax check"
print("\n[10] Python syntax check")

for search_dir in [SCRIPTS_DIR, LEARNING_SCRIPTS_DIR]:
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

# Use a lightweight YAML check: verify structure with basic parsing
# since PyYAML may not be installed. Check for common YAML errors.
if os.path.isdir(WORKFLOWS_DIR):
    for ymlfile in sorted(glob.glob(os.path.join(WORKFLOWS_DIR, "*.yml"))):
        fname = os.path.basename(ymlfile)
        try:
            with open(ymlfile, "r", encoding="utf-8") as f:
                content = f.read()

            # Basic structural checks
            errors = []
            if not content.strip():
                errors.append("empty file")
            if "name:" not in content:
                errors.append("missing 'name:' field")
            if "on:" not in content and "on :" not in content:
                errors.append("missing 'on:' trigger")
            if "jobs:" not in content:
                errors.append("missing 'jobs:' section")

            # Check for tab indentation (YAML uses spaces)
            for i, line in enumerate(content.split("\n"), 1):
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

PIPELINE = [
    (os.path.join(LEARNING_SCRIPTS_DIR, "observe.py"), "analyze.py"),
    (os.path.join(LEARNING_SCRIPTS_DIR, "analyze.py"), "propose.py"),
]

for caller, expected_target in PIPELINE:
    caller_name = os.path.basename(caller)
    if not os.path.isfile(caller):
        result("FAIL", f"{caller_name} -- missing, cannot check chain")
        continue

    with open(caller, "r", encoding="utf-8") as f:
        content = f.read()

    # Look for subprocess references to the target script
    if expected_target in content:
        # Verify the target script actually exists
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

REQUIRED_IGNORES = [
    "observations.jsonl",
    "observations.archive/",
    "instincts/",
    "proposals/",
    ".session-notices/",
    "session-delta.md",
    "last-modified.json",
]

if os.path.isfile(".gitignore"):
    with open(".gitignore", "r", encoding="utf-8") as f:
        gitignore = f.read()
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

# Read hub content once
hub_content = ""
if os.path.isfile(HUB_SRC):
    with open(HUB_SRC, "r", encoding="utf-8") as f:
        hub_content = f.read()

# 14a. Every non-deprecated instruction file must be referenced in the hub
for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
    fname = os.path.basename(src)
    with open(src, "r", encoding="utf-8") as f:
        first = f.read(50)
    if first.strip().startswith("<!-- DEPRECATED"):
        continue
    short_name = fname.replace(".instructions.md", "")
    if fname in hub_content or short_name in hub_content:
        result("PASS", f"hub refs instruction: {fname}")
    else:
        result("FAIL", f"hub missing instruction: {fname} -- not discoverable")

# 14b. Every skill directory with a SKILL.md must be referenced in the hub
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

# 14c. Every .claude/rules/ file must have a matching source instruction
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

# 14d. Claude hub must match Copilot hub (agents see identical content)
if os.path.isfile(HUB_DEST) and hub_content:
    with open(HUB_DEST, "r", encoding="utf-8") as f:
        claude_hub = f.read().replace("\r", "").replace("\x00", "")
    clean_hub = hub_content.replace("\r", "").replace("\x00", "")
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

SETUP_COMPLETE = os.path.join(".claude", "setup-complete")
setup_done = os.path.isfile(SETUP_COMPLETE)
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
    with open(md, "r", encoding="utf-8") as f:
        content = f.read()
    matches = [m.start() for m in re.finditer(r"<!--\s*CUSTOMIZE", content)]
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

PATTERNS_FILE = os.path.join(SRC_DIR, "patterns.instructions.md")
if os.path.isfile(PATTERNS_FILE):
    with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
        patterns_content = f.read()
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

if os.path.isfile(SYSTEM_INDEX):
    with open(SYSTEM_INDEX, "r", encoding="utf-8") as f:
        index_content = f.read()

    for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.instructions.md"))):
        fname = os.path.basename(src)
        with open(src, "r", encoding="utf-8") as f:
            first = f.read(50)
        if first.strip().startswith("<!-- DEPRECATED"):
            continue
        if fname in index_content:
            result("PASS", f"index lists instruction: {fname}")
        else:
            result("FAIL", f"index missing instruction: {fname}")

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
        print(f"  {sev:<{sev_w}}  {chk:<{chk_w}}  {msg}")
    print("")

sys.exit(1 if fails > 0 else 0)
