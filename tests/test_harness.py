from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_onenote", ROOT / "scripts/validate_onenote.py")
assert SPEC and SPEC.loader
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class HarnessTests(unittest.TestCase):
    def test_venv_executable_path_is_not_symlink_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            base = root / "base-python"
            base.touch()
            venv = root / "venv-python"
            venv.symlink_to(base)
            self.assertNotEqual(Path(str(venv.absolute())), venv.resolve())

    def test_manifest_records_relative_path_size_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "nested").mkdir()
            (root / "nested" / "item.txt").write_text("safe synthetic text", encoding="utf-8")
            items = HARNESS.manifest(root)
        self.assertEqual(items[0]["path"], "nested/item.txt")
        self.assertEqual(items[0]["size"], 19)
        self.assertEqual(len(items[0]["sha256"]), 64)

    def test_redactor_excludes_sensitive_fields(self) -> None:
        private = {
            "run": {"test_id": "JON-107-onenote-extraction"},
            "scope": "private_fixture_validation",
            "assessment": {"status": "BLOCKED_NOT_VALIDATED", "findings": [{"severity": "required", "message": "secret medical text"}]},
            "converter": {"package": "onenote-tool", "version": "0.1.5", "commit": HARNESS.COMMIT},
            "tool_versions": {"python": "3.x"},
            "execution": {"exit_status": 0, "command": ["secret-filename.one"], "command_sha256": "safe-command-digest"},
            "references": {"count": 0, "comparison_status": "not_applicable_no_references"},
            "content": {"totals": {"sections": 1, "pages": 2, "images": 3, "attachments": 4, "tables": 5}},
            "pdf_inspection": [],
            "duplicates": [],
            "input": {"original_filename": "secret-filename.one", "sha256": "privatehash", "origin": {"source_url": None, "license": None}},
        }
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "report.json"
            source.write_text(json.dumps(private), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/redact_report.py"), str(source)],
                text=True,
                capture_output=True,
                check=True,
            )
        self.assertNotIn("secret", result.stdout)
        self.assertNotIn("privatehash", result.stdout)
        self.assertIn("BLOCKED_NOT_VALIDATED", result.stdout)

    def test_baseline_rejects_unknown_distinct_row(self) -> None:
        baseline = {
            "expected_rows": [{"id": "row-a", "tokens": ["safe"]}],
            "must_remain_distinct": [["row-a", "row-missing"]],
        }
        with self.assertRaisesRegex(ValueError, "known row ids"):
            HARNESS.validate_text_baseline(baseline)

    def test_distinct_rows_cannot_share_an_ocr_window(self) -> None:
        candidates = {"row-a": [(1, 4, 1)], "row-b": [(1, 4, 1)]}
        self.assertEqual(HARNESS.maximum_nonoverlapping_matches(candidates, ["row-a", "row-b"]), 1)

    def test_distinct_rows_pass_in_separate_ocr_windows(self) -> None:
        candidates = {"row-a": [(1, 4, 1)], "row-b": [(1, 5, 1)]}
        self.assertEqual(HARNESS.maximum_nonoverlapping_matches(candidates, ["row-a", "row-b"]), 2)


if __name__ == "__main__":
    unittest.main()
