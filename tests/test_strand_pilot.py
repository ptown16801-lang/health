from __future__ import annotations

import importlib.util
import copy
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_strand_pilot", ROOT / "scripts/verify_strand_pilot.py")
assert SPEC and SPEC.loader
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class StrandPilotVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = json.loads((ROOT / "templates/strand-repeat-labs.synthetic.json").read_text())
        self.result = json.loads((ROOT / "templates/strand-review-result.example.json").read_text())
        self.result["round_trip"]["reimported_assertions"] = copy.deepcopy(self.spec["assertions"])

    def test_example_result_passes(self) -> None:
        self.assertEqual(VERIFIER.verify(self.spec, self.result), [])

    def test_forbidden_merge_fails(self) -> None:
        self.result["events"][1]["source_assertion_ids"].append("A7")
        self.result["events"][-1]["source_assertion_ids"].remove("A7")
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertTrue(any("false merge: A3 and A7" in failure for failure in failures))

    def test_missing_round_trip_assertion_fails(self) -> None:
        self.result["round_trip"]["reimported_assertions"][5]["value"] = 9.9
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertIn("round-trip assertion content, order, or provenance changed", failures)

    def test_missing_event_ids_cannot_hide_a_forbidden_merge(self) -> None:
        self.result["events"] = [{
            "source_assertion_ids": [item["id"] for item in self.spec["assertions"]],
            "provenance": [],
        }]
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertTrue(any("non-empty string ID" in failure for failure in failures))
        self.assertTrue(any("unapproved merge" in failure for failure in failures))

    def test_unlisted_different_records_cannot_merge(self) -> None:
        self.result["events"][2]["source_assertion_ids"].append("A5")
        self.result["events"][3]["source_assertion_ids"].remove("A5")
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertTrue(any("unapproved merge: event E3 groups A4, A5" in failure for failure in failures))

    def test_string_flags_are_not_boolean_evidence(self) -> None:
        self.result["workspace_is_synthetic_only"] = "false"
        self.result["manual_review"] = {
            "timeline_usable": "false", "search_usable": "false", "export_inspected": "false"
        }
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertEqual(sum("boolean true" in failure for failure in failures), 4)


if __name__ == "__main__":
    unittest.main()
