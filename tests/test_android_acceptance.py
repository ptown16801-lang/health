from pathlib import Path
import tempfile
import unittest

from scripts.run_android_acceptance import run_acceptance


class AndroidAcceptanceTest(unittest.TestCase):
    def test_controlled_candidate_passes_every_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_acceptance(Path(directory))

        self.assertEqual("pass", report["gate"])
        self.assertEqual(0, report["false_automatic_merges"])
        self.assertTrue(
            all(item["status"] == "pass" for item in report["coverage"].values())
        )


if __name__ == "__main__":
    unittest.main()
