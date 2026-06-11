#!/usr/bin/env python3
"""
test_sync_log_rotation.py
Tests for the sync-log cap in sync-claude-rules.py (audit G6, gap-fix plan
Phase 6). The script runs as a subprocess against a minimal temp repo: an
oversized log rotates to roughly half the cap keeping the newest whole runs
behind a truncation notice, and a normal-size log is appended untouched.

Stdlib only; no network, temp filesystem only. Run from repo root:
  python .github/scripts/tests/test_sync_log_rotation.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SYNC_SCRIPT = os.path.join(REPO_ROOT, ".github", "scripts", "sync-claude-rules.py")
MAX_LOG_BYTES = 256 * 1024


def _write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


class SyncFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sync-log-test-")
        _write(os.path.join(self.tmp, ".github", "copilot-instructions.md"),
               "# Hub\n")
        _write(os.path.join(self.tmp, ".github", "instructions",
                            "sample.instructions.md"),
               '---\napplyTo: "**"\n---\n\n# Sample\n\nBody.\n')
        self.log = os.path.join(self.tmp, ".claude", "sync_log.txt")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_sync(self):
        return subprocess.run([sys.executable, SYNC_SCRIPT],
                              capture_output=True, text=True, cwd=self.tmp)

    def seed_log(self, runs, stamp="2026-01-01 00:00:00"):
        blocks = [f"[{stamp}]\nrun {i}\n\n" for i in range(runs)]
        _write(self.log, "".join(blocks))

    def test_normal_log_is_appended_not_rotated(self):
        self.seed_log(3)
        before = os.path.getsize(self.log)
        res = self.run_sync()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        content = open(self.log, encoding="utf-8").read()
        self.assertNotIn("log rotated", content)
        self.assertIn("run 0", content)
        self.assertGreater(os.path.getsize(self.log), before)

    def test_oversized_log_rotates_keeping_newest_runs(self):
        # Enough uniform runs to clear the cap comfortably.
        runs = 11000  # ~330 KB of uniform blocks, comfortably over the cap
        self.seed_log(runs)
        self.assertGreater(os.path.getsize(self.log), MAX_LOG_BYTES)
        res = self.run_sync()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertLess(os.path.getsize(self.log), MAX_LOG_BYTES)
        content = open(self.log, encoding="utf-8").read()
        self.assertIn("log rotated", content.splitlines()[0])
        self.assertIn(f"run {runs - 1}", content)   # newest kept
        self.assertNotIn("run 0\n", content)        # oldest dropped

    def test_rotation_keeps_whole_runs(self):
        runs = 11000  # ~330 KB of uniform blocks, comfortably over the cap
        self.seed_log(runs)
        self.run_sync()
        content = open(self.log, encoding="utf-8").read()
        # Every kept fixture block survived intact: a timestamp line
        # followed by its run line.
        for block in content.split("\n\n"):
            if block.strip().startswith("[2026-01-01"):
                self.assertIn("\nrun ", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
