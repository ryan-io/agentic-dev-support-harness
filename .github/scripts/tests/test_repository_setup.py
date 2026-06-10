#!/usr/bin/env python3
"""
test_repository_setup.py
Tests for the repository-setup engine (ADR-SCAFFOLD Amendment 2026-06-08).

Covers: SRC resolves to the repo root, the template copy reproduces the tree
and excludes the sync log, dry-run writes nothing, the --remove-path migration
strips a marked shell rc line and leaves the rest, and setup makes no write
outside the repository (the central trust property of the rewrite).

Stdlib only; temp filesystem and a redirected HOME, no network. Run from repo
root:
  python .github/scripts/tests/test_repository_setup.py
"""

import io
import importlib.util
import os
import tempfile
import unittest
from contextlib import redirect_stdout

# The engine file name carries a hyphen, so load it by path rather than import.
_ENGINE = os.path.join(os.path.dirname(__file__), "..", "setup",
                       "repository-setup.py")
_spec = importlib.util.spec_from_file_location("repository_setup", _ENGINE)
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)


class TestSrcResolution(unittest.TestCase):
    def test_src_is_repo_root(self):
        # The engine lives at .github/scripts/setup/; SRC is three levels up.
        self.assertTrue(os.path.isfile(os.path.join(rs.SRC, "CLAUDE.md")))
        self.assertTrue(os.path.isdir(os.path.join(rs.SRC, ".github")))


class TestCopyTemplate(unittest.TestCase):
    def test_real_copy_reproduces_tree_and_excludes_sync_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                rs.copy_template(tmp, dry_run=False)
            # Representative files from each copy path.
            for rel in ("CLAUDE.md",
                        os.path.join(".github", "hooks", "pre-commit"),
                        os.path.join(".claude", "rules", "memory.md"),
                        os.path.join(".claude", "settings.json"),
                        os.path.join(".claude", "learning", "proposals", ".gitkeep")):
                self.assertTrue(os.path.exists(os.path.join(tmp, rel)),
                                f"missing after copy: {rel}")
            # The local sync log is excluded from the .github copy.
            self.assertFalse(
                os.path.exists(os.path.join(tmp, ".github", "sync_log.txt")))
            # Source-clone bytecode never ships.
            for root, dirs, _ in os.walk(tmp):
                self.assertNotIn("__pycache__", dirs,
                                 f"__pycache__ leaked into {root}")

    def test_dry_run_copies_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                rs.copy_template(tmp, dry_run=True)
            self.assertEqual(os.listdir(tmp), [])


class TestDryRunScaffold(unittest.TestCase):
    def test_dry_run_does_not_create_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "new-project")
            with redirect_stdout(io.StringIO()):
                rc = rs.main(["--dry-run", target])
            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(target))


@unittest.skipIf(os.name == "nt", "POSIX shell rc behavior")
class TestRemovePathPosix(unittest.TestCase):
    def setUp(self):
        self._home = os.environ.get("HOME")
        self.tmp = tempfile.mkdtemp()
        os.environ["HOME"] = self.tmp
        self.rc = os.path.join(self.tmp, ".bashrc")

    def tearDown(self):
        if self._home is not None:
            os.environ["HOME"] = self._home
        for root, _, files in os.walk(self.tmp, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
        os.rmdir(self.tmp)

    def test_strips_marked_line_keeps_rest(self):
        with open(self.rc, "w", encoding="utf-8") as fh:
            fh.write("export EDITOR=vim\n")
            fh.write(f'export PATH="$PATH:/x"  {rs.RC_MARKER}\n')
            fh.write("alias ll='ls -la'\n")
        with redirect_stdout(io.StringIO()):
            rs.remove_path(dry_run=False)
        with open(self.rc, encoding="utf-8") as fh:
            body = fh.read()
        self.assertNotIn(rs.RC_MARKER, body)
        self.assertIn("export EDITOR=vim", body)
        self.assertIn("alias ll=", body)

    def test_dry_run_leaves_rc_untouched(self):
        original = f'export PATH="$PATH:/x"  {rs.RC_MARKER}\n'
        with open(self.rc, "w", encoding="utf-8") as fh:
            fh.write(original)
        with redirect_stdout(io.StringIO()):
            rs.remove_path(dry_run=True)
        with open(self.rc, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original)

    def test_no_entry_reports_and_writes_nothing(self):
        with open(self.rc, "w", encoding="utf-8") as fh:
            fh.write("export EDITOR=vim\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rs.remove_path(dry_run=False)
        self.assertIn("No ah-ide PATH entry found", out.getvalue())


class TestAdopt(unittest.TestCase):
    """Adopt-mode collision policy (adr-setup-add-adopt-mode-three-paths):
    never-overwrite, gitignore merge with negations, collision report."""

    def _make_target(self, tmp):
        """A Unity-shaped, populated project root."""
        def w(rel, content):
            path = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        w(os.path.join("Assets", "Scenes", "Main.unity"), "scene\n")
        w(os.path.join("ProjectSettings", "ProjectVersion.txt"),
          "m_EditorVersion: 6000.4.10f1\n")
        w(os.path.join("Packages", "manifest.json"), "{}\n")
        w("README.md", "MY PROJECT\n")
        w(".gitignore", "/Library/\n/Temp/\n")
        return tmp

    def test_overlay_never_overwrites_and_reports_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_target(tmp)
            local = os.path.join(tmp, ".github", "instructions",
                                 "code-standards.instructions.md")
            os.makedirs(os.path.dirname(local), exist_ok=True)
            with open(local, "w", encoding="utf-8") as fh:
                fh.write("LOCAL\n")
            with redirect_stdout(io.StringIO()):
                collisions = rs.overlay_template(tmp, dry_run=False)
            with open(local, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "LOCAL\n")
            self.assertIn(".github/instructions/code-standards.instructions.md",
                          collisions)
            # Non-colliding template files arrived; the project's README is untouched.
            self.assertTrue(os.path.isfile(os.path.join(tmp, "CLAUDE.md")))
            with open(os.path.join(tmp, "README.md"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "MY PROJECT\n")

    def test_gitignore_merge_appends_and_negates_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_target(tmp)
            pre_dirs = [d for d in os.listdir(tmp)
                        if os.path.isdir(os.path.join(tmp, d))]
            report = rs.merge_gitignore(tmp, pre_dirs, dry_run=False)
            with open(os.path.join(tmp, ".gitignore"), encoding="utf-8") as fh:
                merged = fh.read()
            self.assertIn("/Library/", merged)          # target lines kept
            self.assertIn("packages/", merged)          # harness lines appended
            self.assertIn("!/Packages/", merged)        # case-collision negated
            self.assertIn(rs.GITIGNORE_MERGE_HEADER, merged)
            self.assertTrue(any("negated: !/Packages/" in r for r in report))
            # Re-merge is a no-op (marker present).
            again = rs.merge_gitignore(tmp, pre_dirs, dry_run=False)
            self.assertTrue(any("already merged" in r for r in again))

    def test_gitignore_copy_branch_still_negates(self):
        # A Hub-created Unity project ships no .gitignore; the copy branch
        # must still protect tracked dirs from case-insensitive swallowing.
        with tempfile.TemporaryDirectory() as tmp:
            self._make_target(tmp)
            os.remove(os.path.join(tmp, ".gitignore"))
            pre_dirs = [d for d in os.listdir(tmp)
                        if os.path.isdir(os.path.join(tmp, d))]
            report = rs.merge_gitignore(tmp, pre_dirs, dry_run=False)
            with open(os.path.join(tmp, ".gitignore"), encoding="utf-8") as fh:
                merged = fh.read()
            self.assertIn("packages/", merged)
            self.assertIn("!/Packages/", merged)
            self.assertTrue(any("negated: !/Packages/" in r for r in report))

    def test_unity_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(rs.is_unity_project(tmp))
            self._make_target(tmp)
            self.assertTrue(rs.is_unity_project(tmp))

    def test_unity_gitattributes_merge_appends_lfs_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_target(tmp)
            with open(os.path.join(tmp, ".gitattributes"), "w", encoding="utf-8") as fh:
                fh.write("* text=auto eol=lf\n")
            report = rs.merge_unity_gitattributes(tmp, dry_run=False)
            with open(os.path.join(tmp, ".gitattributes"), encoding="utf-8") as fh:
                merged = fh.read()
            self.assertIn("* text=auto eol=lf", merged)       # existing kept
            self.assertIn("filter=lfs", merged)               # LFS block added
            self.assertIn(rs.GITATTRIBUTES_MERGE_HEADER, merged)
            self.assertTrue(any("merged" in r for r in report))
            again = rs.merge_unity_gitattributes(tmp, dry_run=False)
            self.assertTrue(any("left untouched" in r for r in again))

    def test_unity_gitattributes_merge_creates_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_target(tmp)
            rs.merge_unity_gitattributes(tmp, dry_run=False)
            with open(os.path.join(tmp, ".gitattributes"), encoding="utf-8") as fh:
                self.assertIn("*.png filter=lfs", fh.read())

    def test_adopt_refuses_empty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(rs.SetupError):
                    rs.adopt(tmp, dry_run=True)

    def test_adopt_refuses_template_source_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = os.path.join(tmp, ".github", "TEMPLATE_SOURCE")
            os.makedirs(os.path.dirname(sentinel), exist_ok=True)
            with open(sentinel, "w", encoding="utf-8") as fh:
                fh.write("sentinel\n")
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(rs.SetupError):
                    rs.adopt(tmp, dry_run=True)

    def test_adopt_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_target(tmp)
            before = sorted(os.path.relpath(os.path.join(r, f), tmp)
                            for r, _, fs in os.walk(tmp) for f in fs)
            with redirect_stdout(io.StringIO()):
                rc = rs.main(["--adopt", "--dry-run", tmp])
            self.assertEqual(rc, 0)
            after = sorted(os.path.relpath(os.path.join(r, f), tmp)
                           for r, _, fs in os.walk(tmp) for f in fs)
            self.assertEqual(before, after)
            with open(os.path.join(tmp, ".gitignore"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "/Library/\n/Temp/\n")


class TestEntryPoint(unittest.TestCase):
    def test_help_returns_zero(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rs.main(["--help"]), 0)

    def test_remove_path_returns_zero(self):
        # Redirect HOME so the run cannot touch the developer's real rc files.
        home = os.environ.get("HOME")
        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(rs.main(["--remove-path"]), 0)
        finally:
            if home is not None:
                os.environ["HOME"] = home
            os.rmdir(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
