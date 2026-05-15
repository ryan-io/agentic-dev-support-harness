#!/usr/bin/env python3
"""
test_corrections.py
Fixture tests for transcript-parse correction capture
(adr-learn-capture-corrections-via-transcript-parse) and the contradiction
reducer (adr-learn-replace-wall-clock-decay-with-evidence-based-staleness,
Phase 4 of the staleness plan).

Mock transcripts cover: clear correction, ambiguous turn, no corrections,
malformed JSON, oversized file, tool_result machine turns, and the privacy
boundary (no raw transcript content in derived observations).

Temp filesystem only; no network. Run from repo root:
  python .github/scripts/learning/tests/test_corrections.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import observe  # noqa: E402
import analyze  # noqa: E402
import session_clock  # noqa: E402


def assistant_edit(file_path, tool="Edit"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": tool, "input": {"file_path": file_path}}
    ]}}


def user_text(text):
    return {"type": "user", "message": {"content": [
        {"type": "text", "text": text}
    ]}}


def user_tool_result(text):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "content": text}
    ]}}


class TranscriptMixin:

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="corrections-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_transcript(self, records, raw=None):
        path = os.path.join(self.tmp, "transcript.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            if raw is not None:
                f.write(raw)
            else:
                for r in records:
                    f.write(json.dumps(r) + "\n")
        return path

    def parse(self, records, raw=None):
        return observe.parse_transcript_for_corrections(
            self.write_transcript(records, raw=raw), "test-session-id")


class TestCorrectionCapture(TranscriptMixin, unittest.TestCase):

    def test_clear_correction_detected(self):
        obs = self.parse([
            assistant_edit("src/billing.py"),
            user_text("no, that's wrong. revert that change."),
        ])
        self.assertEqual(len(obs), 1)
        rec = obs[0]
        self.assertEqual(rec["event"], "correction")
        self.assertEqual(rec["provenance"], "user-correction")
        self.assertIn(rec["category"], ("negation", "rejection"))
        self.assertEqual(rec["tool"], "Edit")
        self.assertEqual(rec["target"], "billing.py")
        self.assertEqual(rec["session_id"], "test-session")

    def test_ambiguous_turn_is_not_a_correction(self):
        obs = self.parse([
            assistant_edit("src/billing.py"),
            user_text("looks good, now add the tax calculation too"),
        ])
        self.assertEqual(obs, [])

    def test_no_corrections_in_clean_session(self):
        obs = self.parse([
            assistant_edit("src/a.py"),
            user_text("great, thanks"),
            assistant_edit("src/b.py"),
            user_text("perfect"),
        ])
        self.assertEqual(obs, [])

    def test_malformed_json_degrades_quietly(self):
        obs = self.parse(None, raw="{not json}\n\x00\x01garbage\n")
        self.assertEqual(obs, [])

    def test_partially_malformed_still_parses_valid_lines(self):
        path = self.write_transcript([assistant_edit("src/c.py")])
        with open(path, "a", encoding="utf-8") as f:
            f.write("{broken\n")
            f.write(json.dumps(user_text("no, that's wrong")) + "\n")
        obs = observe.parse_transcript_for_corrections(path, "sid")
        self.assertEqual(len(obs), 1)

    def test_oversized_transcript_skipped(self):
        path = self.write_transcript([assistant_edit("src/a.py")])
        with open(path, "a", encoding="utf-8") as f:
            f.write(" " * (observe.MAX_TRANSCRIPT_BYTES + 1))
        self.assertEqual(
            observe.parse_transcript_for_corrections(path, "sid"), [])

    def test_missing_transcript_returns_empty(self):
        self.assertEqual(
            observe.parse_transcript_for_corrections(
                os.path.join(self.tmp, "absent.jsonl"), "sid"), [])
        self.assertEqual(
            observe.parse_transcript_for_corrections("", "sid"), [])

    def test_tool_result_turns_are_not_user_speech(self):
        obs = self.parse([
            assistant_edit("src/a.py"),
            user_tool_result("error: no, this is wrong, incorrect input"),
        ])
        self.assertEqual(obs, [])

    def test_correction_without_prior_action_dropped(self):
        obs = self.parse([
            user_text("no, that's wrong"),
        ])
        self.assertEqual(obs, [])

    def test_correction_pairs_with_most_recent_mutating_tool(self):
        obs = self.parse([
            assistant_edit("src/old.py"),
            user_text("fine"),
            assistant_edit("docs/new.md", tool="Write"),
            user_text("actually, use the template instead"),
        ])
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["tool"], "Write")
        self.assertEqual(obs[0]["target"], "new.md")
        self.assertEqual(obs[0]["category"], "redirect")

    def test_privacy_no_raw_transcript_content(self):
        secret = "SENTINEL-API-KEY-93qxz"
        obs = self.parse([
            assistant_edit("src/billing.py"),
            user_text(f"no, that's wrong. the key is {secret}, use it"),
        ])
        self.assertEqual(len(obs), 1)
        self.assertNotIn(secret, json.dumps(obs))

    def test_classifier_is_conservative(self):
        self.assertIsNone(observe.classify_correction("yes, do that"))
        self.assertIsNone(observe.classify_correction(""))
        self.assertIsNone(observe.classify_correction(None))
        self.assertEqual(
            observe.classify_correction("no, undo that"), "negation")
        self.assertEqual(
            observe.classify_correction("that's wrong"), "rejection")
        self.assertEqual(
            observe.classify_correction("use tabs instead"), "redirect")
        # Phrase buried past the head window does not count.
        buried = ("x" * (observe.CLASSIFY_HEAD_CHARS + 10)) + " incorrect"
        self.assertIsNone(observe.classify_correction(buried))


def instinct_yaml(iid, confidence=0.6, file_scope="**/*.md",
                  confirmed=False):
    confirmed_line = "confirmed: true\n" if confirmed else ""
    return f"""---
id: {iid}
trigger: "when editing files"
confidence: {confidence:.2f}
domain: code-style
file_scope: "{file_scope}"
evidence_count: 3
last_seen: "2026-06-05"
last_seen_session: 0
{confirmed_line}---

# Test instinct {iid}

## Evidence
- fixture
"""


def correction_obs(target, provenance="user-correction"):
    return {"event": "correction", "provenance": provenance,
            "category": "rejection", "tool": "Edit", "target": target,
            "session_id": "abc"}


class TestContradictionReducer(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="reducer-test-")
        self.learning = os.path.join(self.tmp, ".claude", "learning")
        self.instincts = os.path.join(self.learning, "instincts")
        os.makedirs(self.instincts)
        self._saved = {}
        for name, value in {
            "LEARNING_DIR": self.learning,
            "INSTINCTS_DIR": self.instincts,
            "CONFIG_FILE": os.path.join(self.learning, "config.json"),
        }.items():
            self._saved[name] = getattr(analyze, name)
            setattr(analyze, name, value)
        self.config = {"staleness": dict(session_clock.DEFAULT_STALENESS)}

    def tearDown(self):
        for name, value in self._saved.items():
            setattr(analyze, name, value)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def confidence_of(self, iid):
        return analyze.load_instinct(
            os.path.join(self.instincts, f"{iid}.yaml")).get("confidence")

    def put(self, iid, **kwargs):
        with open(os.path.join(self.instincts, f"{iid}.yaml"), "w",
                  encoding="utf-8") as f:
            f.write(instinct_yaml(iid, **kwargs))

    def test_matching_contradiction_reduces_confidence(self):
        self.put("md-rule", confidence=0.6, file_scope="**/*.md")
        reduced = analyze.contradiction_pass(
            [correction_obs("docs/adr/foo.md")], self.config)
        self.assertEqual(reduced, 1)
        self.assertAlmostEqual(self.confidence_of("md-rule"), 0.5, places=2)

    def test_non_matching_correction_leaves_instinct_alone(self):
        self.put("md-rule", confidence=0.6, file_scope="**/*.md")
        reduced = analyze.contradiction_pass(
            [correction_obs("src/foo.py")], self.config)
        self.assertEqual(reduced, 0)
        self.assertAlmostEqual(self.confidence_of("md-rule"), 0.6, places=2)

    def test_self_correction_weighs_half(self):
        self.put("md-rule", confidence=0.6, file_scope="**/*.md")
        analyze.contradiction_pass(
            [correction_obs("a.md", provenance="self-correction")],
            self.config)
        self.assertAlmostEqual(self.confidence_of("md-rule"), 0.55, places=2)

    def test_confirmed_instinct_nudges_instead_of_reducing(self):
        self.put("kept", confidence=0.6, file_scope="**/*.md",
                 confirmed=True)
        reduced = analyze.contradiction_pass(
            [correction_obs("docs/foo.md")], self.config)
        self.assertEqual(reduced, 0)
        self.assertAlmostEqual(self.confidence_of("kept"), 0.6, places=2)

    def test_confidence_floors_at_point_one(self):
        self.put("md-rule", confidence=0.15, file_scope="**/*.md")
        analyze.contradiction_pass(
            [correction_obs("a.md"), correction_obs("b.md")], self.config)
        self.assertAlmostEqual(self.confidence_of("md-rule"), 0.1, places=2)

    def test_dry_run_does_not_write(self):
        self.put("md-rule", confidence=0.6, file_scope="**/*.md")
        reduced = analyze.contradiction_pass(
            [correction_obs("a.md")], self.config, dry_run=True)
        self.assertEqual(reduced, 1)
        self.assertAlmostEqual(self.confidence_of("md-rule"), 0.6, places=2)

    def test_no_corrections_is_a_noop(self):
        self.put("md-rule", confidence=0.6, file_scope="**/*.md")
        self.assertEqual(
            analyze.contradiction_pass(
                [{"event": "PostToolUse", "tool": "Edit"}], self.config), 0)

    def test_correction_derived_instinct_not_self_reduced(self):
        # A correction corroborates the instinct it seeded; the reducer
        # must not consume it as evidence against that same instinct.
        path = os.path.join(self.instincts, "corr.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(instinct_yaml("corr", confidence=0.45,
                                  file_scope="**/*.md").replace(
                "last_seen_session: 0",
                "provenance: user-correction\nlast_seen_session: 0"))
        reduced = analyze.contradiction_pass(
            [correction_obs("docs/foo.md")], self.config)
        self.assertEqual(reduced, 0)
        self.assertAlmostEqual(self.confidence_of("corr"), 0.45, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
