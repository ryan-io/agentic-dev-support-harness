#!/usr/bin/env python3
"""
test_bootstrap_update.py
Tests for the update-mechanism bootstrap (audit G1, gap-fix plan Phase 1).

Coverage, all against temp fixtures: a fresh consumer receives update.py,
the manifest, both lifecycle skills, and a valid anchor; existing files are
never overwritten; the anchor records --record-source and resolves --anchor
via the harness clone; dry-run writes nothing; a template-source target, a
target with no .github/, an anchored target, and the harness clone itself
are all refused.

Stdlib only; no network, temp filesystem only. Run from repo root:
  python .github/scripts/tests/test_bootstrap_update.py
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# The engine file name carries a hyphen, so load it by path rather than import.
_ENGINE = os.path.join(os.path.dirname(__file__), "..", "bootstrap-update.py")
_spec = importlib.util.spec_from_file_location("bootstrap_update", _ENGINE)
bu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bu)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _write(path, content="x\n"):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _git(*args, cwd=None):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                          cwd=cwd)


def make_harness(root):
    """A minimal harness clone: the install set plus a git history."""
    _write(os.path.join(root, ".github", "scripts", "update.py"), "# engine\n")
    _write(os.path.join(root, ".github", "scripts", "update-manifest.json"),
           '{"governance_roots": [], "merge_set": [], "exclude": [], "guards": {}}\n')
    _write(os.path.join(root, ".github", "skills", "harness-update", "SKILL.md"),
           "# harness-update\n")
    _write(os.path.join(root, ".github", "skills", "harness-eject", "SKILL.md"),
           "# harness-eject\n")
    _git("init", cwd=root)
    _git("add", "-A", cwd=root)
    _git("-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "init", cwd=root)
    return _git("rev-parse", "HEAD", cwd=root).stdout.strip()


def make_consumer(root):
    """A minimal pre-mechanism consumer: governed (.github/) but no anchor."""
    _write(os.path.join(root, ".github", "copilot-instructions.md"), "# hub\n")


class BootstrapBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bootstrap-test-")
        self.harness = os.path.join(self.tmp, "harness")
        self.consumer = os.path.join(self.tmp, "consumer")
        os.makedirs(self.consumer)
        self.head = make_harness(self.harness)
        make_consumer(self.consumer)
        # Point the module at the fixture clone instead of the real repo.
        self._old_root = bu.HARNESS_ROOT
        bu.HARNESS_ROOT = self.harness

    def tearDown(self):
        bu.HARNESS_ROOT = self._old_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bu.main(["--target", self.consumer] + list(extra))
        return code, out.getvalue(), err.getvalue()


class TestInstall(BootstrapBase):
    def test_fresh_consumer_gets_all_artifacts_and_anchor(self):
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        for rel in ((".github", "scripts", "update.py"),
                    (".github", "scripts", "update-manifest.json"),
                    (".github", "skills", "harness-update", "SKILL.md"),
                    (".github", "skills", "harness-eject", "SKILL.md")):
            self.assertTrue(os.path.isfile(os.path.join(self.consumer, *rel)),
                            f"missing {'/'.join(rel)}")
        anchor = json.load(open(os.path.join(
            self.consumer, ".github", "harness-version.json")))
        self.assertEqual(anchor["commit"], self.head)
        self.assertEqual(anchor["source"], self.harness)

    def test_anchor_records_given_source_and_sha(self):
        code, _, _ = self.run_main("--record-source", "https://example/h.git",
                                   "--anchor", self.head)
        self.assertEqual(code, 0)
        anchor = json.load(open(os.path.join(
            self.consumer, ".github", "harness-version.json")))
        self.assertEqual(anchor["source"], "https://example/h.git")
        self.assertEqual(anchor["commit"], self.head)

    def test_existing_file_is_never_overwritten(self):
        local = os.path.join(self.consumer, ".github", "scripts", "update.py")
        _write(local, "# local customization\n")
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(open(local).read(), "# local customization\n")
        self.assertIn("skip (exists)", out)

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertFalse(os.path.exists(os.path.join(
            self.consumer, ".github", "harness-version.json")))
        self.assertFalse(os.path.exists(os.path.join(
            self.consumer, ".github", "scripts", "update.py")))

    def test_bad_anchor_ref_is_refused(self):
        code, _, err = self.run_main("--anchor", "no-such-ref")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)


class TestGuards(BootstrapBase):
    def test_template_source_target_is_refused(self):
        _write(os.path.join(self.consumer, ".github", "TEMPLATE_SOURCE"))
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("TEMPLATE_SOURCE", err)

    def test_ungoverned_target_is_refused(self):
        bare = os.path.join(self.tmp, "bare")
        os.makedirs(bare)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bu.main(["--target", bare])
        self.assertEqual(code, 1)
        self.assertIn(".github/", err.getvalue())

    def test_already_anchored_target_is_refused(self):
        _write(os.path.join(self.consumer, ".github", "harness-version.json"),
               '{"source": "s", "commit": "c"}\n')
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("already", err)

    def test_harness_clone_itself_is_refused(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bu.main(["--target", self.harness])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err.getvalue())

    def test_missing_target_is_refused(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bu.main(["--target", os.path.join(self.tmp, "nope")])
        self.assertEqual(code, 1)
        self.assertIn("not found", err.getvalue())


class TestRealClone(unittest.TestCase):
    def test_real_harness_carries_the_install_set(self):
        """The script's install lists must exist in the actual repo."""
        for rel in bu.FILE_INSTALLS:
            self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, rel)),
                            f"repo missing {rel}")
        for rel in bu.TREE_INSTALLS:
            self.assertTrue(os.path.isdir(os.path.join(REPO_ROOT, rel)),
                            f"repo missing {rel}/")


if __name__ == "__main__":
    unittest.main(verbosity=2)
