from __future__ import annotations

import importlib.util
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

    def test_example_result_passes(self) -> None:
        self.assertEqual(VERIFIER.verify(self.spec, self.result), [])

    def test_forbidden_merge_fails(self) -> None:
        self.result["events"][1]["source_assertion_ids"].append("A7")
        self.result["events"][-1]["source_assertion_ids"].remove("A7")
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertTrue(any("false merge: A3 and A7" in failure for failure in failures))

    def test_missing_round_trip_assertion_fails(self) -> None:
        self.result["round_trip"]["reimported_assertion_ids"].remove("A6")
        failures = VERIFIER.verify(self.spec, self.result)
        self.assertIn("round-trip assertion set is incomplete or duplicated", failures)


if __name__ == "__main__":
    unittest.main()

