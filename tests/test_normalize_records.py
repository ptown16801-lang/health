from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("normalize_records", ROOT / "scripts/normalize_records.py")
assert SPEC and SPEC.loader
NORMALIZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = NORMALIZER
SPEC.loader.exec_module(NORMALIZER)


class NormalizeRecordsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads((ROOT / "fixtures/repeat-labs.synthetic.json").read_text(encoding="utf-8"))

    def event_assertions(self, result: dict) -> set[frozenset[str]]:
        return {frozenset(item["id"] for item in event["assertions"]) for event in result["events"]}

    def test_controlled_fixture_has_zero_false_automatic_merges(self) -> None:
        result = NORMALIZER.normalize(self.fixture)
        expected = {frozenset(ids) for ids in self.fixture["expected_event_assertions"]}
        self.assertEqual(self.event_assertions(result), expected)
        self.assertEqual(len(result["events"]), 6)
        observed_ids = sorted(
            assertion["id"] for event in result["events"] for assertion in event["assertions"]
        )
        self.assertEqual(observed_ids, sorted(item["id"] for item in self.fixture["assertions"]))

    def test_exact_file_copies_retain_every_location(self) -> None:
        result = NORMALIZER.normalize(self.fixture)
        portal_evidence = next(item for item in result["evidence"] if item["sha256"].startswith("a"))
        self.assertEqual(portal_evidence["source_ids"], ["portal-download", "portal-download-copy"])
        self.assertEqual(len(portal_evidence["locations"]), 2)
        duplicate_event = next(
            event for event in result["events"]
            if {item["id"] for item in event["assertions"]} == {"exact-1", "exact-2"}
        )
        self.assertEqual(duplicate_event["automatic_grouping_reason"], "exact_file_and_record_key")

    def test_same_name_value_and_day_are_not_merge_evidence(self) -> None:
        fixture = deepcopy(self.fixture)
        for assertion_id in ("lookalike-1", "lookalike-2"):
            assertion = next(item for item in fixture["assertions"] if item["id"] == assertion_id)
            assertion.pop("source_record_key")
        result = NORMALIZER.normalize(fixture)
        self.assertIn(frozenset(["lookalike-1"]), self.event_assertions(result))
        self.assertIn(frozenset(["lookalike-2"]), self.event_assertions(result))

    def test_repeat_same_day_observations_remain_distinct(self) -> None:
        result = NORMALIZER.normalize(self.fixture)
        self.assertIn(frozenset(["repeat-morning"]), self.event_assertions(result))
        self.assertIn(frozenset(["repeat-afternoon"]), self.event_assertions(result))

    def test_conflicting_assertions_are_both_preserved(self) -> None:
        result = NORMALIZER.normalize(self.fixture)
        event = next(
            event for event in result["events"]
            if {item["id"] for item in event["assertions"]} == {"conflict-structured", "conflict-document"}
        )
        value_conflict = next(item for item in event["conflicts"] if item["field"] == "value")
        self.assertEqual({variant["value"] for variant in value_conflict["assertions"]}, {4.2, 4.7})

    def test_incorrect_manual_merge_is_reviewable_and_undoable(self) -> None:
        result = NORMALIZER.normalize(self.fixture)
        event_by_assertion = {
            event["assertions"][0]["id"]: event["id"]
            for event in result["events"] if len(event["assertions"]) == 1
        }
        before = deepcopy(result["events"])
        decision_id = NORMALIZER.merge_events(
            result,
            [event_by_assertion["repeat-morning"], event_by_assertion["repeat-afternoon"]],
            reviewer="synthetic-reviewer",
            rationale="intentional incorrect merge exercise",
        )
        self.assertEqual(result["manual_decisions"][0]["status"], "applied")
        self.assertEqual(result["manual_decisions"][0]["rationale"], "intentional incorrect merge exercise")
        NORMALIZER.undo_merge(
            result,
            decision_id,
            reviewer="synthetic-reviewer",
            rationale="repeat accessions prove separate events",
        )
        self.assertEqual(result["events"], before)
        self.assertEqual(result["manual_decisions"][0]["status"], "undone")

    def test_rejects_missing_or_ambiguous_provenance(self) -> None:
        fixture = deepcopy(self.fixture)
        fixture["sources"][0]["locations"] = []
        with self.assertRaisesRegex(NORMALIZER.NormalizationError, "provenance location"):
            NORMALIZER.normalize(fixture)


if __name__ == "__main__":
    unittest.main()
