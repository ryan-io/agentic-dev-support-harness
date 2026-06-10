#!/usr/bin/env python3
"""
test_eject.py
Tests for the harness-eject engine (adr-setup-introduce-harness-eject).

Phase 0 coverage: manifest loads and parses, the real manifest respects the
keep-set guard, the guard rejects a planted Category D path, is_protected
matches roots and descendants, the --keep-scaffolder opt-out drops Category B,
and guard_state refuses on the template source.

Phase 1 coverage (temp git fixtures only): dry-run output matches the manifest
and changes nothing, a live run removes A and C and lands one commit, the
opt-out retains Category B, clear honors its keep list, resets write project
skeletons, guards and the dirty-tree precondition refuse, the runtime keep-set
guard refuses a planted protected path, and a single git revert restores the
pre-eject tree.

Stdlib only; no network or fixtures on disk beyond temp. Run from repo root:
  python .github/scripts/tests/test_eject.py
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

import eject  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REAL_MANIFEST = os.path.join(REPO_ROOT, ".github", "scripts", "eject-manifest.json")


class TestRealManifest(unittest.TestCase):
    def test_loads_and_parses(self):
        m = eject.load_manifest(REAL_MANIFEST)
        self.assertIn("categories", m)
        self.assertIn("protected_roots", m)

    def test_real_manifest_passes_keep_set_guard(self):
        m = eject.load_manifest(REAL_MANIFEST)
        self.assertEqual(eject.validate_manifest(m), [])

    def test_category_b_is_optout(self):
        m = eject.load_manifest(REAL_MANIFEST)
        with_b = {e["path"] for e in eject.removal_entries(m, keep_scaffolder=False)}
        without_b = {e["path"] for e in eject.removal_entries(m, keep_scaffolder=True)}
        self.assertIn("templates/", with_b)
        self.assertNotIn("templates/", without_b)
        # Category A survives the opt-out.
        self.assertIn(".github/scripts/setup/repository-setup.py", without_b)

    def test_every_reset_path_has_a_skeleton(self):
        m = eject.load_manifest(REAL_MANIFEST)
        for e in eject.removal_entries(m):
            if e["action"] == "reset":
                self.assertIn(e["path"], eject.RESET_CONTENT,
                              f"reset path missing a skeleton: {e['path']}")


class TestKeepSetGuard(unittest.TestCase):
    def _manifest(self, paths, action="remove", roots=None):
        return {
            "protected_roots": roots if roots is not None else [".github/instructions/"],
            "categories": {
                "X": {"label": "test", "action": action,
                      "paths": [{"path": p, "type": "file"} for p in paths]}
            },
        }

    def test_rejects_planted_protected_path(self):
        m = self._manifest([".github/instructions/code-standards.instructions.md"])
        violations = eject.validate_manifest(m)
        self.assertTrue(violations)
        self.assertIn("protected root", violations[0])

    def test_rejects_protected_root_itself(self):
        m = self._manifest([".github/instructions/"])
        self.assertTrue(eject.validate_manifest(m))

    def test_allows_reset_action_on_protected_file(self):
        # A reset rewrites a kept file; it is not a deletion, so it is allowed.
        m = self._manifest([".github/instructions/memory.instructions.md"], action="reset")
        self.assertEqual(eject.validate_manifest(m), [])

    def test_allows_unprotected_remove(self):
        m = self._manifest(["templates/", "setup.sh"], roots=[".github/instructions/"])
        self.assertEqual(eject.validate_manifest(m), [])


class TestIsProtected(unittest.TestCase):
    def setUp(self):
        self.roots = [".github/instructions/", ".github/scripts/validate-system.py"]

    def test_descendant_of_dir_root(self):
        self.assertTrue(eject.is_protected(".github/instructions/memory.instructions.md", self.roots))

    def test_dir_root_itself(self):
        self.assertTrue(eject.is_protected(".github/instructions", self.roots))

    def test_exact_file_root(self):
        self.assertTrue(eject.is_protected(".github/scripts/validate-system.py", self.roots))

    def test_unprotected_path(self):
        self.assertFalse(eject.is_protected("templates/csharp-classlib", self.roots))

    def test_prefix_is_not_a_false_match(self):
        # ".github/instructionsX" must not match the ".github/instructions/" root.
        self.assertFalse(eject.is_protected(".github/instructionsX/foo.md", self.roots))


class TestGuardState(unittest.TestCase):
    def test_refuses_when_sentinel_present(self):
        m = {"guards": {"require_marker": ".claude/setup-complete",
                        "refuse_if_present": ".github/TEMPLATE_SOURCE"},
             "categories": {}, "protected_roots": []}
        cwd = os.getcwd()
        os.chdir(REPO_ROOT)
        try:
            can, reasons = eject.guard_state(m)
        finally:
            os.chdir(cwd)
        # In the source repo the sentinel exists and the marker does not, so refuse.
        self.assertFalse(can)
        self.assertTrue(any("sentinel" in r for r in reasons))


# --- Phase 1: execution on temp git fixtures --------------------------------

def _git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True)


def _write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class EjectFixture(unittest.TestCase):
    """A throwaway git repo carrying a stub file for every manifest entry."""

    def setUp(self):
        self.manifest = eject.load_manifest(REAL_MANIFEST)
        self.tmp = tempfile.mkdtemp(prefix="eject-fixture-")
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        _git("init", "-q")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "test")

        # The fixture's own copy of the manifest, where the engine expects it.
        _write(eject.MANIFEST_PATH, json.dumps(self.manifest))

        # Stub every removal entry (full set; opt-out filtering happens at run time).
        for e in eject.removal_entries(self.manifest, keep_scaffolder=False):
            p = e["path"].rstrip("/")
            if e["action"] == "reset":
                _write(p, "OLD CONTENT\n")
            elif e["type"] == "dir":
                _write(os.path.join(p, "stub.md"), "stub\n")
            else:
                _write(p, "stub\n")

        # The clear target gets its keep file plus a stale entry to sweep.
        _write(os.path.join(".claude", "learning", "proposals", ".gitkeep"), "")
        _write(os.path.join(".claude", "learning", "proposals", "stale-proposal.md"), "old\n")

        # A protected file that must survive every run.
        self.protected = os.path.join(".github", "instructions", "code-standards.instructions.md")
        _write(self.protected, "protected\n")

        # Phase 2 scrub/trim targets: gated files, skills README, project-setup.
        _write(os.path.join(".github", "copilot-instructions.md"),
               "# Hub\n"
               "- Scaffolder: `templates/` and `.github/scripts/scaffold.py`\n"
               "- Setup: `.github/scripts/setup/repository-setup.py`\n"
               "- Keep: `.github/instructions/code-standards.instructions.md`\n")
        _write(os.path.join(".github", "docs", "system-index.md"),
               "# Index\n"
               "| `docs/process/` | plans |\n"
               "| `templates/README.md` | authoring |\n"
               "| `.github/instructions/code-standards.instructions.md` | standards |\n")
        _write(os.path.join(".github", "skills", "README.md"),
               "# Skills\n"
               "`project-setup` offers scaffolding (`python .github/scripts/scaffold.py`).\n"
               "`system-review` audits the harness.\n")
        _write(os.path.join(".github", "skills", "project-setup", "SKILL.md"),
               "# Project Setup Skill\n"
               "### Step 0: Scaffold the Solution (ah-ide)\n"
               "Run the scaffolder via scaffold.py.\n"
               "### Step 1: Identify the Stack\n"
               "Confirm Step 0's choice matches.\n"
               "Ask about languages.\n")

        # Marker is local-only in real clones; gitignore it so the tree stays clean.
        _write(".gitignore", ".claude/setup-complete\n")
        _git("add", "-A")
        _git("commit", "-q", "-m", "fixture: initial tree")
        _write(os.path.join(".claude", "setup-complete"), "2026-06-10\n")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _execute(self, dry_run, keep_scaffolder=False):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = eject.cmd_execute(self.manifest, dry_run=dry_run,
                                   keep_scaffolder=keep_scaffolder)
        return rc, out.getvalue()

    def test_dry_run_matches_manifest_and_changes_nothing(self):
        rc, out = self._execute(dry_run=True)
        self.assertEqual(rc, 0)
        for e in eject.removal_entries(self.manifest):
            self.assertIn(e["path"].rstrip("/"), out)
        # Nothing was touched: every stubbed path still exists, no commit landed.
        self.assertTrue(os.path.exists(".github/scripts/setup/repository-setup.py"))
        self.assertTrue(os.path.exists("templates"))
        self.assertIn("OLD CONTENT", _read("README.md"))
        self.assertTrue(_git("status", "--porcelain").stdout.strip() == "")

    def test_live_run_removes_a_and_c_and_lands_one_commit(self):
        rc, out = self._execute(dry_run=False)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(".github/scripts/setup/repository-setup.py"))
        self.assertFalse(os.path.exists("docs/process"))
        self.assertFalse(os.path.exists("templates"))
        # Clear kept the keep list, swept the rest.
        self.assertTrue(os.path.exists(".claude/learning/proposals/.gitkeep"))
        self.assertFalse(os.path.exists(".claude/learning/proposals/stale-proposal.md"))
        # Resets carry the project name (the fixture directory).
        name = os.path.basename(self.tmp)
        self.assertIn(name, _read("README.md"))
        self.assertIn(name, _read(".github/instructions/memory.instructions.md"))
        # Protected file survived; the eject landed as exactly one new commit.
        self.assertTrue(os.path.exists(self.protected))
        self.assertEqual(_git("log", "--oneline").stdout.count("\n"), 2)
        self.assertIn(eject.EJECT_COMMIT_MESSAGE, _git("log", "-1", "--format=%s").stdout)
        self.assertTrue(_git("status", "--porcelain").stdout.strip() == "")

    def test_keep_scaffolder_retains_category_b(self):
        rc, _ = self._execute(dry_run=False, keep_scaffolder=True)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists("templates"))
        self.assertTrue(os.path.exists(".github/scripts/scaffold.py"))
        self.assertFalse(os.path.exists(".github/scripts/setup/repository-setup.py"))

    def test_revert_restores_pre_eject_tree(self):
        rc, _ = self._execute(dry_run=False)
        self.assertEqual(rc, 0)
        res = _git("revert", "--no-edit", "HEAD")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(os.path.exists(".github/scripts/setup/repository-setup.py"))
        self.assertTrue(os.path.exists("templates"))
        self.assertIn("OLD CONTENT", _read("README.md"))
        self.assertTrue(os.path.exists(".claude/learning/proposals/stale-proposal.md"))

    def test_live_run_refuses_without_marker(self):
        os.remove(os.path.join(".claude", "setup-complete"))
        rc, out = self._execute(dry_run=False)
        self.assertEqual(rc, 1)
        self.assertIn("REFUSED", out)
        self.assertTrue(os.path.exists("templates"))

    def test_dry_run_allowed_without_marker(self):
        os.remove(os.path.join(".claude", "setup-complete"))
        rc, out = self._execute(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertIn("will REFUSE", out)

    def test_live_run_refuses_dirty_tree(self):
        _write("uncommitted.txt", "dirty\n")
        rc, out = self._execute(dry_run=False)
        self.assertEqual(rc, 1)
        self.assertIn("dirty", out)
        self.assertTrue(os.path.exists("templates"))

    def test_live_run_scrubs_references_and_trims_scaffolder(self):
        rc, _ = self._execute(dry_run=False)
        self.assertEqual(rc, 0)
        hub = _read(".github/copilot-instructions.md")
        self.assertNotIn("templates/", hub)
        self.assertNotIn("repository-setup.py", hub)
        self.assertIn("code-standards.instructions.md", hub)
        index = _read(".github/docs/system-index.md")
        self.assertNotIn("docs/process/", index)
        self.assertNotIn("templates/README.md", index)
        self.assertIn("code-standards.instructions.md", index)
        skill = _read(".github/skills/project-setup/SKILL.md")
        self.assertNotIn("Step 0", skill)
        self.assertNotIn("scaffold.py", skill)
        self.assertIn("Step 1", skill)
        self.assertIn("Ask about languages", skill)
        readme = _read(".github/skills/README.md")
        self.assertNotIn("scaffold.py", readme)
        self.assertIn("system-review", readme)

    def test_keep_scaffolder_preserves_scaffolder_docs(self):
        rc, _ = self._execute(dry_run=False, keep_scaffolder=True)
        self.assertEqual(rc, 0)
        # Scaffolder kept, so its references and the Step 0 section survive.
        self.assertIn("templates/", _read(".github/copilot-instructions.md"))
        self.assertIn("Step 0", _read(".github/skills/project-setup/SKILL.md"))
        # Category A references still scrub.
        self.assertNotIn("repository-setup.py", _read(".github/copilot-instructions.md"))

    def test_scrub_content_unit(self):
        content = ("keep `a/b.md` here\n"
                   "drop `gone/x.md` ref\n"
                   "drop subpath `gonedir/sub/file.md`\n"
                   "keep `gonedir2/x.md` (paren-guarded `cmd gone/x.md`)\n")
        new, dropped = eject.scrub_content(content, {"gone/x.md"}, {"gonedir"})
        self.assertEqual(dropped, 2)
        self.assertIn("a/b.md", new)
        self.assertIn("gonedir2/x.md", new)

    def test_runtime_guard_refuses_protected_destructive_entry(self):
        entry = {"path": self.protected, "type": "file",
                 "category": "X", "action": "remove", "keep": []}
        with self.assertRaises(eject.EjectError):
            eject.apply_entry(entry, [".github/instructions/"], dry_run=False)
        self.assertTrue(os.path.exists(self.protected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
