#!/usr/bin/env python3
"""
test_scaffold.py
Tests for the ah-ide scaffolder engine (audit I8; the other engines all have
suites, scaffold.py had only the CI matrix exercise).

Coverage, all via the CLI against temp out dirs: each of the four templates
scaffolds with a receipt and full token replacement, collisions refuse
without --force, undo removes exactly the emitted files and refuses on
modified ones unless forced, --ide controls IDE-asset emission, and
--test-framework selects the overlay. No dotnet build; file assertions only.

Stdlib only; no network, temp filesystem only. Run from repo root:
  python .github/scripts/tests/test_scaffold.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ENGINE = os.path.join(REPO_ROOT, ".github", "scripts", "scaffold.py")
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")
RECEIPT = ".ah-ide-scaffold.json"


def run_cli(*args, cwd=None):
    return subprocess.run([sys.executable, ENGINE] + list(args),
                          capture_output=True, text=True, cwd=cwd)


def manifest(template):
    with open(os.path.join(TEMPLATES_DIR, template, "manifest.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def tree_files(root):
    out = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            out.append(rel.replace(os.sep, "/"))
    return sorted(out)


class ScaffoldBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scaffold-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scaffold(self, *args):
        return run_cli(*args, "--out", self.tmp)


class TestAllTemplates(ScaffoldBase):
    CASES = [
        ("csharp-classlib", ["csharp", "--type", "classlib", "--name", "Acme"]),
        ("csharp-wpf-di", ["csharp", "--type", "wpf", "--name", "Acme"]),
        ("csharp-wpf-di-ef", ["csharp", "--type", "wpf-ef", "--name", "Acme"]),
        ("lua-wow-addon", ["lua", "--name", "Acme"]),
    ]

    def test_each_template_scaffolds_with_receipt_and_no_token(self):
        for template, args in self.CASES:
            with self.subTest(template=template):
                out = os.path.join(self.tmp, template)
                os.makedirs(out)
                res = run_cli(*args, "--out", out)
                self.assertEqual(res.returncode, 0,
                                 res.stdout + res.stderr)
                files = tree_files(out)
                self.assertIn(RECEIPT, files)
                self.assertGreater(len(files), 1)
                token = manifest(template)["token"]
                # Token must survive nowhere: not in paths, not in content.
                for rel in files:
                    self.assertNotIn(token, rel)
                    if rel == RECEIPT:
                        continue
                    path = os.path.join(out, rel)
                    try:
                        content = open(path, encoding="utf-8").read()
                    except UnicodeDecodeError:
                        continue  # binary asset
                    self.assertNotIn(token, content,
                                     f"{template}: token left in {rel}")
                # Receipt records every emitted file.
                runs = json.load(open(os.path.join(out, RECEIPT)))
                emitted = sorted(f["path"] for f in runs[-1]["files"])
                self.assertEqual(emitted,
                                 sorted(f for f in files if f != RECEIPT))


class TestCollisionsAndUndo(ScaffoldBase):
    ARGS = ["csharp", "--type", "classlib", "--name", "Acme"]

    def test_second_scaffold_refuses_without_force(self):
        self.assertEqual(self.scaffold(*self.ARGS).returncode, 0)
        res = self.scaffold(*self.ARGS)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("refusing to overwrite", res.stderr)

    def test_undo_removes_exactly_the_emitted_files(self):
        self.assertEqual(self.scaffold(*self.ARGS).returncode, 0)
        keep = os.path.join(self.tmp, "untouched.txt")
        open(keep, "w").write("mine\n")
        res = run_cli("undo", "--yes", "--out", self.tmp)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(os.path.isfile(keep))
        leftovers = [f for f in tree_files(self.tmp)
                     if f not in ("untouched.txt", RECEIPT)]
        self.assertEqual(leftovers, [])

    def test_undo_refuses_modified_file_unless_forced(self):
        self.assertEqual(self.scaffold(*self.ARGS).returncode, 0)
        runs = json.load(open(os.path.join(self.tmp, RECEIPT)))
        target = os.path.join(self.tmp, runs[-1]["files"][0]["path"])
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\n-- local edit\n")
        res = run_cli("undo", "--yes", "--out", self.tmp)
        self.assertNotEqual(res.returncode, 0)
        res = run_cli("undo", "--yes", "--force", "--out", self.tmp)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


class TestFlagSurface(ScaffoldBase):
    def test_ide_vs2026_omits_vscode_assets(self):
        res = self.scaffold("csharp", "--type", "classlib", "--name", "Acme",
                            "--ide", "vs2026")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, ".vscode")))

    def test_ide_vscode_emits_vscode_assets(self):
        res = self.scaffold("csharp", "--type", "classlib", "--name", "Acme",
                            "--ide", "vscode")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, ".vscode")))

    def test_test_framework_overlay_selected(self):
        res = self.scaffold("csharp", "--type", "classlib", "--name", "Acme",
                            "--test-framework", "xUnit")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        csprojs = [f for f in tree_files(self.tmp)
                   if f.endswith(".csproj") and "Tests" in f]
        self.assertTrue(csprojs, "no test project emitted")
        content = open(os.path.join(self.tmp, csprojs[0]),
                       encoding="utf-8").read().lower()
        self.assertIn("xunit", content)
        self.assertNotIn("nunit", content)

    def test_unknown_test_framework_refused(self):
        res = self.scaffold("csharp", "--type", "classlib", "--name", "Acme",
                            "--test-framework", "Jest")
        self.assertNotEqual(res.returncode, 0)

    def test_help_exits_zero(self):
        res = run_cli("help")
        self.assertEqual(res.returncode, 0)
        self.assertIn("ah-ide", res.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
