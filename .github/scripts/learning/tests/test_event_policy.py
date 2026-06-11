#!/usr/bin/env python3
"""
test_event_policy.py
Fixture tests for the 2026-06-10 system review fixes in the observation
and detection layer.

Covers: B1 (detectors count one event per tool call; PreToolUse duplicates
in an old log inflate nothing), B2 (instinct evidence merges additively and
stays capped), B5 (the analysis marker goes through the locked append and
rotation rewrites in place), B6 (the self-observation filter covers command
and pattern inputs, not just file_path).

Temp filesystem only; no network. Run from repo root:
  python .github/scripts/learning/tests/test_event_policy.py
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


def tool_obs(event, tool, path, session="s1", outcome="success"):
    """One observation record as observe.py would write it."""
    rec = {
        "ts": "2026-06-11T00:00:00Z",
        "event": event,
        "session_id": session,
        "tool": tool,
        "input_summary": path,
        "file_ext": os.path.splitext(path)[1],
        "domain_hint": "code-style",
    }
    if event == "PostToolUse":
        rec["outcome"] = outcome
    return rec


def pre_post_pair(tool, path, session="s1"):
    """The doubled shape an old log holds: PreToolUse plus PostToolUse."""
    return [tool_obs("PreToolUse", tool, path, session),
            tool_obs("PostToolUse", tool, path, session)]


class TempAnalyzeDirMixin:
    """Temp learning dir with analyze module paths patched in."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="event-policy-test-")
        self.learning = os.path.join(self.tmp, ".claude", "learning")
        self.instincts = os.path.join(self.learning, "instincts")
        os.makedirs(self.instincts)
        self._saved = {}
        patches = {
            "PROJECT_DIR": self.tmp,
            "LEARNING_DIR": self.learning,
            "OBS_FILE": os.path.join(self.learning, "observations.jsonl"),
            "INSTINCTS_DIR": self.instincts,
            "PROPOSALS_DIR": os.path.join(self.learning, "proposals"),
            "INSTRUCTIONS_DIR": os.path.join(
                self.tmp, ".github", "instructions"),
            "RULES_DIR": os.path.join(self.tmp, ".claude", "rules"),
        }
        for name, value in patches.items():
            self._saved[name] = getattr(analyze, name)
            setattr(analyze, name, value)

    def tearDown(self):
        for name, value in self._saved.items():
            setattr(analyze, name, value)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def project_path(self, rel):
        return os.path.join(self.tmp, rel).replace("\\", "/")


class TestDetectorEventPolicy(TempAnalyzeDirMixin, unittest.TestCase):
    """B1: every detector counts one event per tool call."""

    def test_file_conventions_count_calls_not_records(self):
        observations = []
        for i in range(3):
            observations += pre_post_pair(
                "Write", self.project_path(f".github/scripts/f{i}.json"))
        instincts = analyze.detect_file_conventions(observations)
        self.assertEqual(len(instincts), 1)
        # 3 calls, not the 6 records a doubled log holds.
        self.assertEqual(instincts[0]["evidence_count"], 3)

    def test_file_conventions_floor_needs_three_real_calls(self):
        """Two calls leave four records in a doubled log; the total < 3
        floor must hold against calls, not records."""
        observations = []
        for i in range(2):
            observations += pre_post_pair(
                "Write", self.project_path(f".github/scripts/f{i}.json"))
        self.assertEqual(analyze.detect_file_conventions(observations), [])

    def test_rule_consultation_counts_calls_not_records(self):
        os.makedirs(analyze.INSTRUCTIONS_DIR)
        rule = "csharp-code-standards.instructions.md"
        with open(os.path.join(analyze.INSTRUCTIONS_DIR, rule), "w",
                  encoding="utf-8") as f:
            f.write("# rules\n")
        observations = []
        for i in range(3):
            observations += pre_post_pair(
                "Edit", self.project_path(f"src/File{i}.cs"))
        instincts = analyze.detect_rule_consultation(observations)
        flagged = [i for i in instincts if rule in i["action"]]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["evidence_count"], 3)

    def test_tool_events_helper_filters_non_tool_records(self):
        observations = (
            pre_post_pair("Read", self.project_path("src/a.py"))
            + [{"event": "SessionStart", "session_id": "s1"},
               {"event": "correction", "session_id": "s1"}]
        )
        events = analyze.tool_events(observations)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "PostToolUse")


class TestEvidenceMerge(TempAnalyzeDirMixin, unittest.TestCase):
    """B2: reinforcement appends evidence instead of replacing it."""

    def read_instinct(self, iid):
        with open(os.path.join(self.instincts, f"{iid}.yaml"),
                  encoding="utf-8") as f:
            return f.read()

    def save(self, evidence):
        return analyze.save_instinct(
            iid="merge-test", trigger="when testing",
            action="Keep prior evidence", confidence=0.3,
            domain="code-style", evidence=evidence,
            file_scope="**/*.py", evidence_count=1)

    def test_prior_evidence_survives_reinforcement(self):
        self.save("- first batch")
        self.save("- second batch")
        content = self.read_instinct("merge-test")
        self.assertIn("- first batch", content)
        self.assertIn("- second batch", content)

    def test_duplicate_evidence_lines_not_repeated(self):
        self.save("- same line")
        self.save("- same line")
        content = self.read_instinct("merge-test")
        self.assertEqual(content.count("- same line"), 1)

    def test_evidence_capped_at_most_recent(self):
        for i in range(analyze.EVIDENCE_CAP + 3):
            self.save(f"- batch {i:02d}")
        content = self.read_instinct("merge-test")
        bullets = [ln for ln in content.split("\n")
                   if ln.startswith("- batch")]
        self.assertEqual(len(bullets), analyze.EVIDENCE_CAP)
        self.assertIn(f"- batch {analyze.EVIDENCE_CAP + 2:02d}", content)
        self.assertNotIn("- batch 00", content)


class TestAnalysisMarker(TempAnalyzeDirMixin, unittest.TestCase):
    """B5: the marker is appended under the observation-log lock."""

    def test_marker_goes_through_locked_append(self):
        calls = []
        saved = observe.locked_append
        observe.locked_append = lambda path, text: calls.append((path, text))
        try:
            analyze.write_analysis_marker()
        finally:
            observe.locked_append = saved
        self.assertEqual(len(calls), 1)
        path, text = calls[0]
        self.assertEqual(path, analyze.OBS_FILE)
        self.assertIn("_analysis_marker", text)
        self.assertTrue(text.endswith("\n"))

    def test_marker_lands_in_log(self):
        analyze.write_analysis_marker()
        with open(analyze.OBS_FILE, encoding="utf-8") as f:
            rec = json.loads(f.read().strip())
        self.assertEqual(rec["event"], "_analysis_marker")


class TestRotationInPlace(unittest.TestCase):
    """B5: rotation rewrites the live file in place under the lock."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rotation-test-")
        self.learning = os.path.join(self.tmp, ".claude", "learning")
        os.makedirs(self.learning)
        self._saved = {
            "LEARNING_DIR": observe.LEARNING_DIR,
            "OBS_FILE": observe.OBS_FILE,
            "MAX_OBSERVATIONS": observe.MAX_OBSERVATIONS,
        }
        observe.LEARNING_DIR = self.learning
        observe.OBS_FILE = os.path.join(self.learning, "observations.jsonl")
        observe.MAX_OBSERVATIONS = 10

    def tearDown(self):
        for name, value in self._saved.items():
            setattr(observe, name, value)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rotation_archives_and_carries_unanalyzed_tail(self):
        lines = [json.dumps({"event": "PostToolUse", "n": i}) + "\n"
                 for i in range(8)]
        lines.append(json.dumps({"event": "_analysis_marker"}) + "\n")
        lines += [json.dumps({"event": "PostToolUse", "n": i}) + "\n"
                  for i in range(8, 10)]
        with open(observe.OBS_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        observe.rotate_observations_if_needed()
        with open(observe.OBS_FILE, encoding="utf-8") as f:
            kept = [ln for ln in f if ln.strip()]
        self.assertEqual(len(kept), 2)  # the unanalyzed tail survives
        archive_dir = os.path.join(self.learning, "observations.archive")
        archived = os.listdir(archive_dir)
        self.assertEqual(len(archived), 1)
        with open(os.path.join(archive_dir, archived[0]),
                  encoding="utf-8") as f:
            self.assertEqual(len([ln for ln in f if ln.strip()]), 11)

    def test_no_rotation_below_threshold(self):
        with open(observe.OBS_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps({"event": "PostToolUse"}) + "\n")
        observe.rotate_observations_if_needed()
        self.assertFalse(os.path.isdir(
            os.path.join(self.learning, "observations.archive")))


class TestSelfObservationFilter(unittest.TestCase):
    """B6: target-naming inputs are all checked, content fields are not."""

    def test_bash_command_targeting_learning_dir_is_filtered(self):
        self.assertTrue(observe.is_self_observation(
            {"command": "cat .claude/learning/observations.jsonl"}))

    def test_grep_pattern_targeting_learning_dir_is_filtered(self):
        self.assertTrue(observe.is_self_observation(
            {"pattern": ".claude/learning/instincts"}))

    def test_glob_path_targeting_learning_dir_is_filtered(self):
        self.assertTrue(observe.is_self_observation(
            {"pattern": "*.yaml", "path": ".claude/learning/instincts"}))

    def test_file_path_still_filtered(self):
        self.assertTrue(observe.is_self_observation(
            {"file_path": ".claude/learning/config.json"}))

    def test_backslash_paths_normalized(self):
        self.assertTrue(observe.is_self_observation(
            {"command": "type .claude\\learning\\config.json"}))

    def test_ordinary_work_not_filtered(self):
        self.assertFalse(observe.is_self_observation(
            {"file_path": "src/app.py"}))
        self.assertFalse(observe.is_self_observation(
            {"command": "python -m pytest"}))

    def test_content_fields_not_scanned(self):
        """Editing a document that mentions the learning directory is real
        work; only target-naming fields count."""
        self.assertFalse(observe.is_self_observation(
            {"file_path": "docs/audit/review.md",
             "old_string": "data in .claude/learning/",
             "new_string": "data in .claude/learning/ (fixed)"}))

    def test_non_dict_input_safe(self):
        self.assertFalse(observe.is_self_observation(None))
        self.assertFalse(observe.is_self_observation("text"))
        self.assertFalse(observe.is_self_observation({}))


class TestErrorRecoveryDedup(unittest.TestCase):
    """G5: detector 3 templates the action (the instinct ID), so recoveries
    of the same tool pair merge instead of minting a sibling file per
    distinct command. The command detail lives in evidence."""

    def _recovery(self, cmd, session="s1"):
        return [tool_obs("PostToolUse", "Bash", cmd, session,
                         outcome="failure"),
                tool_obs("PostToolUse", "Read", f"after {cmd}", session,
                         outcome="success")]

    def test_same_tool_pair_yields_one_instinct_id(self):
        obs = self._recovery("cmd-one", "s1") + self._recovery("cmd-two", "s2")
        instincts = analyze.detect_error_recovery(obs)
        self.assertEqual(len(instincts), 2)
        ids = {analyze.instinct_id(i["action"]) for i in instincts}
        self.assertEqual(len(ids), 1, "distinct commands minted distinct IDs")

    def test_action_carries_no_command_detail(self):
        (inst,) = analyze.detect_error_recovery(self._recovery("rm -rf tmp"))
        self.assertNotIn("rm -rf", inst["action"])
        self.assertEqual(inst["action"], "Recover failed Bash with Read")

    def test_evidence_keeps_the_command_detail(self):
        (inst,) = analyze.detect_error_recovery(self._recovery("cmd-one"))
        self.assertIn("after cmd-one", inst["evidence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
