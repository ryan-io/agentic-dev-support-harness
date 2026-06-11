#!/usr/bin/env python3
"""
test_staleness.py
Fixture tests for the evidence-based staleness model
(adr-learn-replace-wall-clock-decay-with-evidence-based-staleness).

Covers: session counter, config migration, backfill, session-clock decay for
instincts and proposals, the confirmed permanence guarantee, relevance
archiving with recorded reasons, and dry-run parity (no writes).

Temp filesystem only; no network. Run from repo root:
  python .github/scripts/learning/tests/test_staleness.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import session_clock  # noqa: E402
import propose  # noqa: E402
import analyze  # noqa: E402


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def instinct_yaml(iid, confidence=0.5, last_seen_session=0, confirmed=False,
                  file_scope="**/*.py"):
    confirmed_line = "confirmed: true\n" if confirmed else ""
    return f"""---
id: {iid}
trigger: "when testing"
confidence: {confidence:.2f}
domain: code-style
file_scope: "{file_scope}"
evidence_count: 3
last_seen: "2026-06-01"
last_seen_session: {last_seen_session}
{confirmed_line}---

# Test instinct {iid}

## Evidence
- fixture
"""


def proposal_md(iid, status="pending", created_session=0, confirmed=False):
    confirmed_line = "confirmed: true\n" if confirmed else ""
    return f"""---
id: {iid}
status: {status}
target: code-standards.instructions.md
instinct_confidence: 0.75
evidence_count: 3
priority: 3
created: "2026-06-01"
created_session: {created_session}
last_reviewed: "2026-06-01"
{confirmed_line}---

# Proposal: test {iid}
"""


class TempLearningDirMixin:
    """Temp learning dir with propose/analyze module paths patched in."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="staleness-test-")
        self.learning = os.path.join(self.tmp, ".claude", "learning")
        self.instincts = os.path.join(self.learning, "instincts")
        self.proposals = os.path.join(self.learning, "proposals")
        os.makedirs(self.instincts)
        os.makedirs(self.proposals)
        self._saved = {}
        patches = {
            propose: {
                "LEARNING_DIR": self.learning,
                "INSTINCTS_DIR": self.instincts,
                "PROPOSALS_DIR": self.proposals,
                "ARCHIVE_DIR": os.path.join(self.learning,
                                            "proposals.archive"),
                "CONFIG_FILE": os.path.join(self.learning, "config.json"),
            },
            analyze: {
                "PROJECT_DIR": self.tmp,
                "LEARNING_DIR": self.learning,
                "INSTINCTS_DIR": self.instincts,
                "INSTINCTS_ARCHIVE_DIR": os.path.join(self.learning,
                                                      "instincts.archive"),
                "CONFIG_FILE": os.path.join(self.learning, "config.json"),
            },
        }
        for module, attrs in patches.items():
            for name, value in attrs.items():
                self._saved[(module, name)] = getattr(module, name)
                setattr(module, name, value)

    def tearDown(self):
        for (module, name), value in self._saved.items():
            setattr(module, name, value)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def config(self, **overrides):
        staleness = dict(session_clock.DEFAULT_STALENESS)
        staleness.update(overrides)
        return {"thresholds": {}, "staleness": staleness}


class TestSessionCounter(TempLearningDirMixin, unittest.TestCase):

    def test_increment_and_read(self):
        self.assertEqual(session_clock.read_session_count(self.learning), 0)
        self.assertEqual(
            session_clock.increment_session_count(self.learning), 1)
        self.assertEqual(
            session_clock.increment_session_count(self.learning), 2)
        self.assertEqual(session_clock.read_session_count(self.learning), 2)

    def test_corrupt_counter_reads_zero(self):
        write(os.path.join(self.learning, "session-counter.json"), "{not json")
        self.assertEqual(session_clock.read_session_count(self.learning), 0)
        self.assertEqual(
            session_clock.increment_session_count(self.learning), 1)


class TestConfigMigration(TempLearningDirMixin, unittest.TestCase):

    def test_date_keys_replaced_with_session_keys(self):
        cfg = {"thresholds": {"proposal_confidence_threshold": 0.7},
               "staleness": {"proposal_decay_days": 30,
                             "proposal_archive_days": 60,
                             "instinct_decay_per_month": 0.05}}
        migrated, changed = session_clock.migrate_config_dict(cfg)
        self.assertTrue(changed)
        staleness = migrated["staleness"]
        for dead in ("proposal_decay_days", "proposal_archive_days",
                     "instinct_decay_per_month"):
            self.assertNotIn(dead, staleness)
        self.assertEqual(staleness["proposal_decay_sessions"], 15)
        self.assertEqual(staleness["proposal_archive_sessions"], 30)
        self.assertEqual(staleness["instinct_decay_per_sessions"], 0.05)
        self.assertEqual(
            migrated["thresholds"]["pending_proposal_soft_cap"], 10)

    def test_migration_is_idempotent(self):
        cfg, _ = session_clock.migrate_config_dict(
            {"staleness": {"proposal_decay_days": 30}})
        again, changed = session_clock.migrate_config_dict(cfg)
        self.assertFalse(changed)
        self.assertEqual(cfg, again)

    def test_migrate_config_file_writes_in_place(self):
        path = os.path.join(self.learning, "config.json")
        write(path, json.dumps(
            {"staleness": {"proposal_decay_days": 30}}))
        session_clock.migrate_config_file(path)
        with open(path, encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertNotIn("proposal_decay_days", on_disk["staleness"])
        self.assertIn("proposal_decay_sessions", on_disk["staleness"])


class TestBackfill(TempLearningDirMixin, unittest.TestCase):

    def test_stamps_missing_session_fields(self):
        inst = instinct_yaml("a").replace("last_seen_session: 0\n", "")
        prop = proposal_md("b").replace("created_session: 0\n", "")
        write(os.path.join(self.instincts, "a.yaml"), inst)
        write(os.path.join(self.proposals, "b.md"), prop)
        stamped = session_clock.backfill_session_fields(self.learning, 7)
        self.assertEqual(stamped, 2)
        with open(os.path.join(self.instincts, "a.yaml"),
                  encoding="utf-8") as f:
            self.assertIn("last_seen_session: 7", f.read())
        with open(os.path.join(self.proposals, "b.md"),
                  encoding="utf-8") as f:
            self.assertIn("created_session: 7", f.read())
        # Idempotent: second pass stamps nothing.
        self.assertEqual(
            session_clock.backfill_session_fields(self.learning, 9), 0)


class TestInstinctDecay(TempLearningDirMixin, unittest.TestCase):

    def load(self, name):
        return propose.parse_instinct(
            os.path.join(self.instincts, f"{name}.yaml"))

    def test_decays_past_window(self):
        write(os.path.join(self.instincts, "old.yaml"),
              instinct_yaml("old", confidence=0.5, last_seen_session=0))
        inst = self.load("old")
        propose.apply_instinct_decay([inst], self.config(), 31)
        # 31 sessions stale // window 15 = 2 full windows -> 0.5 - 0.05*2
        self.assertAlmostEqual(inst["confidence"], 0.4, places=2)
        self.assertAlmostEqual(self.load("old")["confidence"], 0.4, places=2)

    def test_no_decay_within_window(self):
        write(os.path.join(self.instincts, "fresh.yaml"),
              instinct_yaml("fresh", confidence=0.5, last_seen_session=20))
        inst = self.load("fresh")
        propose.apply_instinct_decay([inst], self.config(), 30)
        self.assertEqual(inst["confidence"], 0.5)

    def test_confirmed_never_decays(self):
        write(os.path.join(self.instincts, "kept.yaml"),
              instinct_yaml("kept", confidence=0.5, last_seen_session=0,
                            confirmed=True))
        inst = self.load("kept")
        propose.apply_instinct_decay([inst], self.config(), 500)
        self.assertEqual(inst["confidence"], 0.5)

    def test_dry_run_does_not_write(self):
        write(os.path.join(self.instincts, "old.yaml"),
              instinct_yaml("old", confidence=0.5, last_seen_session=0))
        inst = self.load("old")
        propose.apply_instinct_decay([inst], self.config(), 31, dry_run=True)
        self.assertAlmostEqual(self.load("old")["confidence"], 0.5, places=2)

    def test_decay_is_idempotent_within_a_window(self):
        """B3: two propose runs in the same stale span charge decay once.
        The old code subtracted rate * windows_stale on every run."""
        write(os.path.join(self.instincts, "old.yaml"),
              instinct_yaml("old", confidence=0.5, last_seen_session=0))
        inst = self.load("old")
        propose.apply_instinct_decay([inst], self.config(), 31)
        self.assertAlmostEqual(inst["confidence"], 0.4, places=2)
        # Same session count, fresh parse (as a new propose run would see).
        inst = self.load("old")
        propose.apply_instinct_decay([inst], self.config(), 31)
        self.assertAlmostEqual(self.load("old")["confidence"], 0.4, places=2)

    def test_decay_charges_only_new_windows(self):
        """B3: after the idempotent charge, one more completed window
        costs exactly one more decrement."""
        write(os.path.join(self.instincts, "old.yaml"),
              instinct_yaml("old", confidence=0.5, last_seen_session=0))
        inst = self.load("old")
        propose.apply_instinct_decay([inst], self.config(), 31)  # 2 windows
        inst = self.load("old")
        propose.apply_instinct_decay([inst], self.config(), 46)  # 3rd window
        self.assertAlmostEqual(self.load("old")["confidence"], 0.35, places=2)


class TestProposalStaleness(TempLearningDirMixin, unittest.TestCase):

    def read(self, directory, name):
        with open(os.path.join(directory, f"{name}.md"),
                  encoding="utf-8") as f:
            return f.read()

    def test_marked_stale_past_decay_sessions(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", created_session=0))
        propose.process_existing_proposals(self.config(), 16)
        self.assertIn("status: stale", self.read(self.proposals, "p"))

    def test_archived_with_decayed_reason(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", created_session=0))
        propose.process_existing_proposals(self.config(), 30)
        self.assertFalse(
            os.path.isfile(os.path.join(self.proposals, "p.md")))
        archived = self.read(propose.ARCHIVE_DIR, "p")
        self.assertIn("archived_reason: decayed", archived)
        self.assertIn("archived_session: 30", archived)

    def test_confirmed_proposal_untouched(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", created_session=0, confirmed=True))
        propose.process_existing_proposals(self.config(), 500)
        self.assertIn("status: pending", self.read(self.proposals, "p"))

    def test_applied_proposal_untouched(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", status="applied", created_session=0))
        propose.process_existing_proposals(self.config(), 500)
        self.assertIn("status: applied", self.read(self.proposals, "p"))

    def test_dry_run_does_not_write(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", created_session=0))
        propose.process_existing_proposals(self.config(), 500, dry_run=True)
        self.assertIn("status: pending", self.read(self.proposals, "p"))

    def test_reinforced_proposal_does_not_decay_or_archive(self):
        """B4/F4: staleness reads reinforced_session when present, so a
        proposal whose instinct keeps gathering evidence stays pending."""
        content = proposal_md("p", created_session=0).replace(
            "created_session: 0", "created_session: 0\nreinforced_session: 39")
        write(os.path.join(self.proposals, "p.md"), content)
        propose.process_existing_proposals(self.config(), 40)
        self.assertIn("status: pending", self.read(self.proposals, "p"))

    def test_reinforce_proposal_stamps_and_revives(self):
        """B4: analyze.reinforce_proposal stamps reinforced_session and
        flips a stale proposal back to pending."""
        saved = analyze.PROPOSALS_DIR
        analyze.PROPOSALS_DIR = self.proposals
        try:
            write(os.path.join(self.proposals, "p.md"),
                  proposal_md("p", status="stale", created_session=0))
            analyze.reinforce_proposal("p", 12)
            content = self.read(self.proposals, "p")
            self.assertIn("reinforced_session: 12", content)
            self.assertIn("status: pending", content)
            # Re-stamp updates in place rather than duplicating the key.
            analyze.reinforce_proposal("p", 14)
            content = self.read(self.proposals, "p")
            self.assertIn("reinforced_session: 14", content)
            self.assertEqual(content.count("reinforced_session"), 1)
        finally:
            analyze.PROPOSALS_DIR = saved

    def test_reinforce_does_not_touch_resolved_proposals(self):
        """B4: applied or rejected proposals are a developer's decision;
        reinforcement must not revive them."""
        saved = analyze.PROPOSALS_DIR
        analyze.PROPOSALS_DIR = self.proposals
        try:
            write(os.path.join(self.proposals, "p.md"),
                  proposal_md("p", status="applied", created_session=0))
            analyze.reinforce_proposal("p", 12)
            self.assertNotIn("reinforced_session",
                             self.read(self.proposals, "p"))
        finally:
            analyze.PROPOSALS_DIR = saved

    def test_archived_proposal_blocks_repromotion(self):
        """B4: proposal_exists sees the archive, so a hot instinct cannot
        mint a fresh proposal the run after its old one archived."""
        os.makedirs(propose.ARCHIVE_DIR, exist_ok=True)
        write(os.path.join(propose.ARCHIVE_DIR, "p.md"),
              proposal_md("p", created_session=0))
        self.assertTrue(propose.proposal_exists("p"))
        self.assertFalse(propose.proposal_exists("other"))


class TestResolvedArchive(TempLearningDirMixin, unittest.TestCase):
    """G3: applied and rejected proposals leave the tracked directory."""

    def read(self, directory, name):
        with open(os.path.join(directory, f"{name}.md"),
                  encoding="utf-8") as f:
            return f.read()

    def test_applied_moves_with_reason(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", status="applied", created_session=0))
        propose.archive_resolved_proposals(7)
        self.assertFalse(os.path.isfile(os.path.join(self.proposals, "p.md")))
        archived = self.read(propose.ARCHIVE_DIR, "p")
        self.assertIn("archived_reason: applied", archived)
        self.assertIn("archived_session: 7", archived)

    def test_rejected_moves_with_reason(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", status="rejected", created_session=0))
        propose.archive_resolved_proposals(7)
        self.assertFalse(os.path.isfile(os.path.join(self.proposals, "p.md")))
        self.assertIn("archived_reason: rejected",
                      self.read(propose.ARCHIVE_DIR, "p"))

    def test_pending_and_stale_stay(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", status="pending", created_session=0))
        write(os.path.join(self.proposals, "s.md"),
              proposal_md("s", status="stale", created_session=0))
        propose.archive_resolved_proposals(7)
        self.assertTrue(os.path.isfile(os.path.join(self.proposals, "p.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.proposals, "s.md")))

    def test_dry_run_moves_nothing(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", status="applied", created_session=0))
        propose.archive_resolved_proposals(7, dry_run=True)
        self.assertTrue(os.path.isfile(os.path.join(self.proposals, "p.md")))
        self.assertNotIn("archived_reason",
                         self.read(self.proposals, "p"))

    def test_idempotent_second_run_is_a_no_op(self):
        write(os.path.join(self.proposals, "p.md"),
              proposal_md("p", status="rejected", created_session=0))
        propose.archive_resolved_proposals(7)
        archived_first = self.read(propose.ARCHIVE_DIR, "p")
        propose.archive_resolved_proposals(9)
        self.assertEqual(archived_first, self.read(propose.ARCHIVE_DIR, "p"))


class TestRelevancePass(TempLearningDirMixin, unittest.TestCase):

    def test_unmatched_scope_archived_as_irrelevant(self):
        write(os.path.join(self.instincts, "dead.yaml"),
              instinct_yaml("dead", file_scope="**/*.zig"))
        archived = analyze.relevance_pass()
        self.assertEqual(archived, 1)
        self.assertFalse(
            os.path.isfile(os.path.join(self.instincts, "dead.yaml")))
        with open(os.path.join(analyze.INSTINCTS_ARCHIVE_DIR, "dead.yaml"),
                  encoding="utf-8") as f:
            self.assertIn("archived_reason: irrelevant", f.read())

    def test_matching_scope_survives(self):
        write(os.path.join(self.tmp, "src", "real.py"), "x = 1\n")
        write(os.path.join(self.instincts, "live.yaml"),
              instinct_yaml("live", file_scope="**/*.py"))
        self.assertEqual(analyze.relevance_pass(), 0)
        self.assertTrue(
            os.path.isfile(os.path.join(self.instincts, "live.yaml")))

    def test_universal_scope_skipped(self):
        write(os.path.join(self.instincts, "uni.yaml"),
              instinct_yaml("uni", file_scope="**"))
        self.assertEqual(analyze.relevance_pass(), 0)

    def test_confirmed_exempt_even_when_unmatched(self):
        write(os.path.join(self.instincts, "kept.yaml"),
              instinct_yaml("kept", file_scope="**/*.zig", confirmed=True))
        self.assertEqual(analyze.relevance_pass(), 0)
        self.assertTrue(
            os.path.isfile(os.path.join(self.instincts, "kept.yaml")))

    def test_dry_run_does_not_move_files(self):
        write(os.path.join(self.instincts, "dead.yaml"),
              instinct_yaml("dead", file_scope="**/*.zig"))
        self.assertEqual(analyze.relevance_pass(dry_run=True), 1)
        self.assertTrue(
            os.path.isfile(os.path.join(self.instincts, "dead.yaml")))


class TestPermanenceHelpers(unittest.TestCase):

    def test_is_confirmed_variants(self):
        self.assertTrue(session_clock.is_confirmed({"confirmed": True}))
        self.assertTrue(session_clock.is_confirmed({"confirmed": "true"}))
        self.assertTrue(session_clock.is_confirmed({"confirmed": "True"}))
        self.assertFalse(session_clock.is_confirmed({"confirmed": False}))
        self.assertFalse(session_clock.is_confirmed({}))
        self.assertFalse(session_clock.is_confirmed(None))

    def test_content_is_confirmed(self):
        self.assertTrue(
            session_clock.content_is_confirmed("id: x\nconfirmed: true\n"))
        self.assertFalse(
            session_clock.content_is_confirmed("id: x\nstatus: pending\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
