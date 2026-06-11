#!/usr/bin/env python3
"""
test_update.py
Tests for the harness-update engine (adr-setup-add-harness-update-mechanism).

Coverage: the real manifest loads and classifies correctly, the anchor
round-trips and fails closed, and against temp git fixtures (a stub harness
source plus an adopted project): --check reports behind, dry-run predicts the
plan and changes nothing, a live run overwrites consume-only files, three-way
merges customized files, never resurrects locally deleted files, keeps local
files the upstream deleted from the merge set, bumps the anchor, and lands one
revertable commit; conflicts stop before the commit and --finish completes
after resolution; the sentinel and a dirty tree refuse.

Stdlib only; no network, temp filesystem only. Run from repo root:
  python .github/scripts/tests/test_update.py
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import update  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REAL_MANIFEST = os.path.join(REPO_ROOT, ".github", "scripts", "update-manifest.json")


def _git(*args, cwd=None):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                          cwd=cwd)


def _write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestRealManifest(unittest.TestCase):
    def test_loads_and_parses(self):
        m = update.load_manifest(REAL_MANIFEST)
        for key in ("governance_roots", "merge_set", "exclude", "guards"):
            self.assertIn(key, m)

    def test_merge_set_files_exist_in_source(self):
        m = update.load_manifest(REAL_MANIFEST)
        for p in m["merge_set"]:
            self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, p)),
                            f"merge_set path missing in source tree: {p}")

    def test_classification(self):
        m = update.load_manifest(REAL_MANIFEST)
        self.assertEqual(update.classify(
            ".github/instructions/memory.instructions.md", m), "merge")
        self.assertEqual(update.classify(
            ".github/instructions/agent-guardrails.instructions.md", m), "overwrite")
        self.assertEqual(update.classify(
            ".github/skills/harness-update/SKILL.md", m), "overwrite")
        self.assertEqual(update.classify(
            ".github/scripts/setup/repository-setup.py", m), "excluded")
        self.assertEqual(update.classify("templates/lua-wow-addon/x.lua", m),
                         "out-of-scope")
        self.assertEqual(update.classify(".claude/rules/memory.md", m),
                         "out-of-scope")
        self.assertEqual(update.classify("src/Program.cs", m), "out-of-scope")

    def test_eject_protected_roots_are_covered(self):
        """Every path eject keeps must be one the update manifest can reach
        (or is documented out of scope), so kept governance never goes stale."""
        m = update.load_manifest(REAL_MANIFEST)
        with open(os.path.join(REPO_ROOT, ".github", "scripts",
                               "eject-manifest.json"), encoding="utf-8") as fh:
            eject_m = json.load(fh)
        for root in eject_m["protected_roots"]:
            probe = root.rstrip("/") + ("/probe.md" if root.endswith("/") else "")
            bucket = update.classify(probe or root, m)
            self.assertIn(bucket, ("merge", "overwrite", "out-of-scope"),
                          f"eject-protected root unclassifiable: {root}")
            if bucket == "out-of-scope":
                covered = any(update._under(root.rstrip("/"), o)
                              for o in m.get("out_of_scope", []))
                self.assertTrue(covered,
                                f"eject-protected root not covered: {root}")


class TestAnchor(unittest.TestCase):
    def test_round_trip(self):
        tmp = tempfile.mkdtemp(prefix="anchor-")
        try:
            p = os.path.join(tmp, "harness-version.json")
            update.write_anchor("https://example/x.git", "a" * 40, path=p)
            a = update.read_anchor(path=p)
            self.assertEqual(a["commit"], "a" * 40)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_anchor_fails_closed(self):
        with self.assertRaises(update.ManifestError):
            update.read_anchor(path=os.path.join(tempfile.gettempdir(),
                                                 "no-such-anchor.json"))


# --- Fixtures: a stub harness source and an adopted project ------------------

TEST_MANIFEST = {
    "description": "test",
    "guards": {"refuse_if_present": ".github/TEMPLATE_SOURCE",
               "anchor": ".github/harness-version.json"},
    "governance_roots": [".github/instructions/", ".github/skills/",
                         ".github/scripts/", ".github/copilot-instructions.md"],
    "merge_set": [".github/instructions/memory.instructions.md",
                  ".github/instructions/research.instructions.md",
                  ".github/copilot-instructions.md"],
    "exclude": [".github/scripts/setup/"],
    "out_of_scope": [".claude/rules/", "CLAUDE.md",
                     ".github/harness-version.json"],
}

GUARDRAILS = ".github/instructions/agent-guardrails.instructions.md"
MEMORY = ".github/instructions/memory.instructions.md"
RESEARCH = ".github/instructions/research.instructions.md"
SETUP_PY = ".github/scripts/setup/repository-setup.py"
NEW_SKILL = ".github/skills/new-skill/SKILL.md"

MEMORY_V0 = "# Memory\n\nline one\nline two\nline three\n"


class UpdateFixture(unittest.TestCase):
    """A harness source repo with two commits, and a project anchored at the
    first commit that copied the v0 files (the adopt overlay)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="update-fixture-")
        self.cwd = os.getcwd()
        self.harness = os.path.join(self.tmp, "harness")
        self.project = os.path.join(self.tmp, "project")

        # Harness v0.
        os.makedirs(self.harness)
        os.chdir(self.harness)
        _git("init", "-q")
        _git("config", "user.email", "t@e.com")
        _git("config", "user.name", "t")
        _write(GUARDRAILS, "rules v0\n")
        _write(MEMORY, MEMORY_V0)
        _write(RESEARCH, "research v0\n")
        _write(SETUP_PY, "print('setup v0')\n")
        _write(".github/copilot-instructions.md", "# Hub\nv0\n")
        _git("add", "-A")
        _git("commit", "-q", "-m", "v0")
        self.v0 = _git("rev-parse", "HEAD").stdout.strip()

        # Harness v1: modify overwrite + merge files, add a skill, delete research.
        _write(GUARDRAILS, "rules v1\n")
        _write(MEMORY, MEMORY_V0.replace("line three", "line three (upstream)"))
        _write(NEW_SKILL, "# New Skill\n")
        _write(SETUP_PY, "print('setup v1')\n")
        os.remove(RESEARCH)
        _git("add", "-A")
        _git("commit", "-q", "-m", "v1")
        self.v1 = _git("rev-parse", "HEAD").stdout.strip()

        # Project: the v0 files as adopted, plus project-own content.
        os.makedirs(self.project)
        os.chdir(self.project)
        _git("init", "-q")
        _git("config", "user.email", "t@e.com")
        _git("config", "user.name", "t")
        for p, c in ((GUARDRAILS, "rules v0\n"),
                     (MEMORY, MEMORY_V0),
                     (RESEARCH, "research v0 customized\n"),
                     (".github/copilot-instructions.md", "# Hub\nv0\n"),
                     ("src/app.py", "project code\n")):
            _write(p, c)
        _write(update.MANIFEST_PATH, json.dumps(TEST_MANIFEST))
        update.write_anchor(self.harness, self.v0)
        _git("add", "-A")
        _git("commit", "-q", "-m", "adopted")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = update.main(list(argv))
        return rc, out.getvalue()

    # --- read-only modes ---

    def test_check_reports_behind(self):
        rc, out = self._run("--check")
        self.assertEqual(rc, 0)
        self.assertIn("Behind: 1 commit(s)", out)

    def test_check_up_to_date(self):
        update.write_anchor(self.harness, self.v1)
        rc, out = self._run("--check")
        self.assertEqual(rc, 0)
        self.assertIn("Up to date", out)

    def test_dry_run_predicts_and_changes_nothing(self):
        rc, out = self._run("--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn(GUARDRAILS, out)          # overwrite planned
        self.assertIn(NEW_SKILL, out)           # addition planned
        self.assertIn("excluded", out)          # setup engine skipped
        self.assertIn("would merge", out)       # memory merge planned
        self.assertIn("clean", out)
        # Nothing changed, no commit landed.
        self.assertEqual(_read(GUARDRAILS), "rules v0\n")
        self.assertFalse(os.path.exists(NEW_SKILL))
        self.assertEqual(update.read_anchor()["commit"], self.v0)
        self.assertEqual(_git("status", "--porcelain").stdout.strip(), "")

    # --- live run, clean path ---

    def test_live_run_applies_and_lands_one_commit(self):
        rc, out = self._run("--run")
        self.assertEqual(rc, 0, out)
        self.assertEqual(_read(GUARDRAILS), "rules v1\n")          # overwrite
        self.assertIn("line three (upstream)", _read(MEMORY))      # clean merge
        self.assertTrue(os.path.exists(NEW_SKILL))                 # addition
        self.assertEqual(_read(RESEARCH), "research v0 customized\n")  # kept
        self.assertNotIn("setup v1", "" if not os.path.exists(SETUP_PY)
                         else _read(SETUP_PY))                     # excluded
        self.assertEqual(update.read_anchor()["commit"], self.v1)  # anchor bumped
        self.assertEqual(_git("log", "--oneline").stdout.count("\n"), 2)
        self.assertIn(self.v1[:9], _git("log", "-1", "--format=%s").stdout)
        self.assertEqual(_git("status", "--porcelain").stdout.strip(), "")

    def test_live_run_merges_local_edit_in_other_region(self):
        _write(MEMORY, MEMORY_V0.replace("line one", "line one (local)"))
        _git("add", "-A")
        _git("commit", "-q", "-m", "local memory edit")
        rc, _ = self._run("--run")
        self.assertEqual(rc, 0)
        merged = _read(MEMORY)
        self.assertIn("line one (local)", merged)
        self.assertIn("line three (upstream)", merged)
        self.assertNotIn("<<<<<<<", merged)

    def test_locally_deleted_overwrite_file_not_resurrected(self):
        os.remove(GUARDRAILS)
        _git("add", "-A")
        _git("commit", "-q", "-m", "project removed guardrails")
        rc, out = self._run("--run")
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(GUARDRAILS))
        self.assertIn("locally removed", out)

    def test_revert_restores_pre_update_tree(self):
        rc, _ = self._run("--run")
        self.assertEqual(rc, 0)
        res = _git("revert", "--no-edit", "HEAD")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(_read(GUARDRAILS), "rules v0\n")
        self.assertFalse(os.path.exists(NEW_SKILL))
        self.assertEqual(update.read_anchor()["commit"], self.v0)

    # --- conflicts and --finish ---

    def test_conflict_stops_before_commit_then_finish_completes(self):
        _write(MEMORY, MEMORY_V0.replace("line three", "line three (local)"))
        _git("add", "-A")
        _git("commit", "-q", "-m", "conflicting local edit")
        rc, out = self._run("--run")
        self.assertEqual(rc, 2)
        self.assertIn("CONFLICTS", out)
        self.assertIn("<<<<<<<", _read(MEMORY))
        self.assertEqual(update.read_anchor()["commit"], self.v0)  # not bumped
        self.assertEqual(_git("log", "--oneline").stdout.count("\n"), 2)

        # --finish refuses while markers remain.
        rc, out = self._run("--finish")
        self.assertEqual(rc, 1)
        self.assertIn("markers remain", out)

        # Resolve, then finish: gate, anchor bump, single commit.
        _write(MEMORY, MEMORY_V0.replace("line three",
                                         "line three (resolved)"))
        rc, out = self._run("--finish")
        self.assertEqual(rc, 0, out)
        self.assertEqual(update.read_anchor()["commit"], self.v1)
        self.assertEqual(_git("log", "--oneline").stdout.count("\n"), 3)
        self.assertEqual(_git("status", "--porcelain").stdout.strip(), "")
        self.assertFalse(os.path.exists(update.PENDING_PATH))

    def test_finish_without_pending_refuses(self):
        rc, out = self._run("--finish")
        self.assertEqual(rc, 1)
        self.assertIn("no pending", out)

    def test_finish_ignores_marker_text_in_unconflicted_file(self):
        """B7: --finish gates on the recorded conflicted paths only. A
        merge-set doc that legitimately contains conflict-marker text must
        not block completion forever."""
        _write(RESEARCH, "research doc\nexample marker: <<<<<<< ours\n")
        _write(MEMORY, MEMORY_V0.replace("line three", "line three (local)"))
        _git("add", "-A")
        _git("commit", "-q", "-m", "local edits")
        rc, out = self._run("--run")
        self.assertEqual(rc, 2)
        with open(update.PENDING_PATH, encoding="utf-8") as fh:
            pending = json.load(fh)
        self.assertEqual(pending["conflicts"], [MEMORY])
        # Resolve the real conflict; the doc's marker text must not block.
        _write(MEMORY, MEMORY_V0.replace("line three",
                                         "line three (resolved)"))
        rc, out = self._run("--finish")
        self.assertEqual(rc, 0, out)
        self.assertFalse(os.path.exists(update.PENDING_PATH))

    def test_finish_falls_back_to_merge_set_without_recorded_conflicts(self):
        """A pending file from before the conflict list existed still gates
        on the whole merge set rather than skipping the check."""
        _write(MEMORY, MEMORY_V0.replace("line three", "line three (local)"))
        _git("add", "-A")
        _git("commit", "-q", "-m", "conflicting local edit")
        rc, _ = self._run("--run")
        self.assertEqual(rc, 2)
        # Strip the conflicts key, simulating an old pending file.
        with open(update.PENDING_PATH, encoding="utf-8") as fh:
            pending = json.load(fh)
        del pending["conflicts"]
        with open(update.PENDING_PATH, "w", encoding="utf-8") as fh:
            json.dump(pending, fh)
        rc, out = self._run("--finish")
        self.assertEqual(rc, 1)
        self.assertIn("markers remain", out)

    # --- guards ---

    def test_refuses_on_template_source(self):
        _write(".github/TEMPLATE_SOURCE", "")
        for flag in ("--check", "--dry-run", "--run"):
            rc, out = self._run(flag)
            self.assertEqual(rc, 1, flag)
            self.assertIn("sentinel", out)

    def test_live_run_refuses_dirty_tree(self):
        _write("uncommitted.txt", "dirty\n")
        rc, out = self._run("--run")
        self.assertEqual(rc, 1)
        self.assertIn("dirty", out)
        self.assertEqual(_read(GUARDRAILS), "rules v0\n")

    def test_missing_anchor_points_at_bootstrap(self):
        os.remove(update.ANCHOR_PATH)
        rc, _ = self._run("--check")
        self.assertEqual(rc, 1)

    def test_anchor_bootstrap_writes_resolved_sha(self):
        os.remove(update.ANCHOR_PATH)
        rc, out = self._run("--anchor", self.v0[:9], "--source", self.harness)
        self.assertEqual(rc, 0, out)
        self.assertEqual(update.read_anchor()["commit"], self.v0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
