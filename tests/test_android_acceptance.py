import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_android_acceptance import run_acceptance
from scripts.build_android_corpus import build_android_corpus


class AndroidAcceptanceTest(unittest.TestCase):
    def test_android_assets_are_built_from_the_integrated_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "controlled-corpus"
            build_android_corpus(output)
            index = json.loads((output / "android-index.json").read_text(encoding="utf-8"))
            self.assertTrue(all((output / item["path"]).is_file() for item in index["records"]))

        titles = [item["title"] for item in index["records"]]
        self.assertTrue(any("OneNote" in title for title in titles))
        self.assertTrue(any("Jefferson" in title for title in titles))
        self.assertTrue(any("Repeats and conflicts" in title for title in titles))

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
