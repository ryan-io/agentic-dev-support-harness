#!/usr/bin/env python3
"""
test_fidelity.py
Fixture tests for the fidelity-plan Phase 2-4 features: correction-instinct
seeding with provenance, the proposal quality gate, the explicit
developer-flagged marker, and the memory-curation nudge counter.

Temp filesystem only; no network. Run from repo root:
  python .github/scripts/learning/tests/test_fidelity.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import analyze  # noqa: E402
import observe  # noqa: E402
import propose  # noqa: E402


def correction_obs(target="docs/foo.md", category="rejection",
                   provenance="user-correction", change="user x on y"):
    return {"event": "correction", "provenance": provenance,
            "category": category, "tool": "Edit", "target": target,
            "file_ext": ".md", "domain_hint": "code-style",
            "change": change, "session_id": "abc"}


class TestUserCorrectionSeeding(unittest.TestCase):

    def test_seeds_at_configured_confidence_with_provenance(self):
        instincts = analyze.detect_user_corrections(
            [correction_obs(), correction_obs(change="user x2 on y")],
            seed_confidence=0.45)
        self.assertEqual(len(instincts), 1)
        inst = instincts[0]
        self.assertEqual(inst["confidence"], 0.45)
        self.assertEqual(inst["provenance"], "user-correction")
        self.assertEqual(inst["evidence_count"], 2)
        self.assertIn("- user x on y", inst["evidence"])

    def test_groups_by_target_and_category(self):
        instincts = analyze.detect_user_corrections([
            correction_obs(target="a.md", category="rejection"),
            correction_obs(target="a.md", category="redirect"),
            correction_obs(target="b.py", category="rejection"),
        ])
        self.assertEqual(len(instincts), 3)

    def test_ignores_non_correction_and_self_correction(self):
        self.assertEqual(analyze.detect_user_corrections([
            {"event": "PostToolUse", "tool": "Edit"},
            correction_obs(provenance="self-correction"),
        ]), [])

    def test_developer_flagged_included(self):
        instincts = analyze.detect_user_corrections(
            [correction_obs(provenance="developer-flagged",
                            category="explicit")])
        self.assertEqual(len(instincts), 1)
        self.assertEqual(instincts[0]["provenance"], "developer-flagged")


class TestProvenancePersistence(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prov-test-")
        self._saved = {
            "INSTINCTS_DIR": analyze.INSTINCTS_DIR,
            "LEARNING_DIR": analyze.LEARNING_DIR,
        }
        analyze.INSTINCTS_DIR = os.path.join(self.tmp, "instincts")
        analyze.LEARNING_DIR = self.tmp

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(analyze, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_writes_provenance_and_merge_preserves_it(self):
        path = analyze.save_instinct(
            iid="t1", trigger="t", action="A", confidence=0.45,
            domain="code-style", evidence="- e", provenance="user-correction")
        data = analyze.load_instinct(path)
        self.assertEqual(data["provenance"], "user-correction")
        # A later merge under a different provenance must not conflate.
        analyze.save_instinct(
            iid="t1", trigger="t", action="A", confidence=0.3,
            domain="code-style", evidence="- e2", provenance="frequency")
        data = analyze.load_instinct(path)
        self.assertEqual(data["provenance"], "user-correction")

    def test_default_provenance_is_frequency(self):
        path = analyze.save_instinct(
            iid="t2", trigger="t", action="A", confidence=0.3,
            domain="code-style", evidence="- e")
        self.assertEqual(analyze.load_instinct(path)["provenance"],
                         "frequency")


class TestQualityGate(unittest.TestCase):

    def test_imperative_headline_passes(self):
        self.assertTrue(propose.has_actionable_rule(
            {"provenance": "frequency",
             "body": "# Place .py files in scripts/\n\n## Evidence\n- x"}))
        self.assertTrue(propose.has_actionable_rule(
            {"provenance": "frequency",
             "body": "# Also read companion guide x-guide.md"}))

    def test_descriptive_headline_held(self):
        self.assertFalse(propose.has_actionable_rule(
            {"provenance": "frequency",
             "body": "# csharp-code-standards.instructions.md rarely "
                     "consulted despite 12 edits in scope"}))
        self.assertFalse(propose.has_actionable_rule(
            {"provenance": "self-correction",
             "body": "# Repeated failed Edit edits to the same .md file"}))

    def test_correction_provenance_passes_with_body(self):
        self.assertTrue(propose.has_actionable_rule(
            {"provenance": "user-correction",
             "body": "# User rejection corrections on a.md: codify"}))
        self.assertFalse(propose.has_actionable_rule(
            {"provenance": "user-correction", "body": ""}))


class TestExplicitMarker(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="marker-test-")
        self.learning = os.path.join(self.tmp, "learning")
        os.makedirs(self.learning)
        self._saved = {
            "LEARNING_DIR": observe.LEARNING_DIR,
            "OBS_FILE": observe.OBS_FILE,
            "SESSION_DELTA_FILE": observe.SESSION_DELTA_FILE,
        }
        observe.LEARNING_DIR = self.learning
        observe.OBS_FILE = os.path.join(self.learning, "observations.jsonl")
        observe.SESSION_DELTA_FILE = os.path.join(
            self.learning, "session-delta.md")

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(observe, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read_obs(self):
        if not os.path.isfile(observe.OBS_FILE):
            return []
        with open(observe.OBS_FILE, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def seed_session_edit(self, session_id, file_path):
        rec = {"event": "PostToolUse", "session_id": session_id,
               "tool": "Edit", "input_summary": file_path,
               "file_ext": ".md"}
        with open(observe.OBS_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def test_marker_records_developer_flagged_correction(self):
        sid = "sess-abc-12345"
        self.seed_session_edit(sid[:12], "src/notes.md")
        secret = "the-secret-detail-xyz"
        observe.handle_prompt_submit(
            {"prompt": f"#correction you keep using tabs, {secret}"}, sid)
        obs = self.read_obs()
        self.assertEqual(len(obs), 2)
        rec = obs[-1]
        self.assertEqual(rec["event"], "correction")
        self.assertEqual(rec["provenance"], "developer-flagged")
        self.assertEqual(rec["category"], "explicit")
        self.assertEqual(rec["tool"], "Edit")
        self.assertNotIn(secret, json.dumps(rec))

    def test_marker_without_prior_action_still_records(self):
        observe.handle_prompt_submit({"prompt": "#correction stop that"},
                                     "sess-empty")
        obs = self.read_obs()
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["target"], "general")

    def test_normal_prompt_records_nothing(self):
        observe.handle_prompt_submit(
            {"prompt": "please add a correction factor to the model"},
            "sess-abc")
        self.assertEqual(self.read_obs(), [])

    def test_malformed_payload_fails_closed(self):
        observe.handle_prompt_submit({"prompt": None}, "sess")
        observe.handle_prompt_submit({}, "sess")
        self.assertEqual(self.read_obs(), [])


class TestCurationNudge(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nudge-test-")
        self._saved = observe.SESSION_DELTA_FILE
        observe.SESSION_DELTA_FILE = os.path.join(self.tmp, "delta.md")

    def tearDown(self):
        observe.SESSION_DELTA_FILE = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_counts_session_blocks(self):
        self.assertEqual(observe.count_session_delta_blocks(), 0)
        with open(observe.SESSION_DELTA_FILE, "w", encoding="utf-8") as f:
            for i in range(6):
                f.write(f"# Session Delta (2026-06-0{i + 1} 10:00 UTC)\n\n"
                        f"Files modified: x.md\n\n")
        self.assertEqual(observe.count_session_delta_blocks(), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
