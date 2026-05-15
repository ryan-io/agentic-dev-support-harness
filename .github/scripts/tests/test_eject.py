#!/usr/bin/env python3
"""
test_eject.py
Tests for the harness-eject engine (adr-setup-introduce-harness-eject), Phase 0.

Covers: manifest loads and parses, the real manifest respects the keep-set
guard, the guard rejects a planted Category D path, is_protected matches roots
and descendants, the --keep-scaffolder opt-out drops Category B, and guard_state
refuses on the template source.

Stdlib only; no network or fixtures on disk beyond temp. Run from repo root:
  python .github/scripts/tests/test_eject.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import eject  # noqa: E402


class TestRealManifest(unittest.TestCase):
    def test_loads_and_parses(self):
        m = eject.load_manifest()
        self.assertIn("categories", m)
        self.assertIn("protected_roots", m)

    def test_real_manifest_passes_keep_set_guard(self):
        m = eject.load_manifest()
        self.assertEqual(eject.validate_manifest(m), [])

    def test_category_b_is_optout(self):
        m = eject.load_manifest()
        with_b = {e["path"] for e in eject.removal_entries(m, keep_scaffolder=False)}
        without_b = {e["path"] for e in eject.removal_entries(m, keep_scaffolder=True)}
        self.assertIn("templates/", with_b)
        self.assertNotIn("templates/", without_b)
        # Category A survives the opt-out.
        self.assertIn(".github/scripts/setup/repository-setup.py", without_b)


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
        can, reasons = eject.guard_state(m)
        # In the source repo the sentinel exists and the marker does not, so refuse.
        self.assertFalse(can)
        self.assertTrue(any("sentinel" in r for r in reasons))


if __name__ == "__main__":
    unittest.main(verbosity=2)
