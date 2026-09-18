from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from health_ingest.jefferson import ImportValidationError, import_jefferson

FIXTURE = Path(__file__).parent / "data" / "jefferson-synthetic-ccda.xml"
FIXED_TIME = datetime(2026, 9, 18, tzinfo=timezone.utc)


class JeffersonImportTest(unittest.TestCase):
    def test_imports_ccda_and_keeps_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = import_jefferson(FIXTURE, output, clock=lambda: FIXED_TIME)
            digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

            self.assertEqual((output / "originals" / digest).read_bytes(), FIXTURE.read_bytes())
            self.assertEqual(manifest["artifact"]["sha256"], digest)
            self.assertEqual(manifest["normalized"]["record_count"], 3)
            records = [
                json.loads(line)
                for line in (output / "normalized" / f"{digest}.ndjson").read_text().splitlines()
            ]
            self.assertEqual(
                [record["kind"] for record in records],
                ["clinical_document", "clinical_section", "clinical_section"],
            )
            self.assertTrue(
                all(record["provenance"]["artifact_sha256"] == digest for record in records)
            )

    def test_imports_xml_documents_from_zip_and_preserves_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "download.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("export/summary.xml", FIXTURE.read_bytes())
                archive.writestr("export/readme.txt", "synthetic fixture")

            manifest = import_jefferson(archive_path, root / "output", clock=lambda: FIXED_TIME)
            digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            self.assertEqual(manifest["format"], "ccda_zip")
            self.assertEqual(manifest["documents"][0]["path"], "export/summary.xml")
            self.assertEqual(
                (root / "output" / "originals" / digest).read_bytes(),
                archive_path.read_bytes(),
            )

    def test_keeps_identical_documents_at_distinct_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "download.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("first/summary.xml", FIXTURE.read_bytes())
                archive.writestr("second/summary.xml", FIXTURE.read_bytes())

            manifest = import_jefferson(archive_path, root / "output", clock=lambda: FIXED_TIME)
            normalized = root / "output" / manifest["normalized"]["stored_path"]
            records = [json.loads(line) for line in normalized.read_text().splitlines()]
            document_ids = [
                record["id"]
                for record in records
                if record["kind"] == "clinical_document"
            ]
            self.assertEqual(len(document_ids), 2)
            self.assertEqual(len(set(document_ids)), 2)

    def test_rejects_non_ccda_xml_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "other.xml"
            source.write_text("<not-clinical-document />")
            output = root / "output"

            with self.assertRaisesRegex(ImportValidationError, "not a C-CDA"):
                import_jefferson(source, output)
            self.assertFalse(output.exists())

    def test_does_not_overwrite_a_corrupt_stored_original(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
            original = output / "originals" / digest
            original.parent.mkdir()
            original.write_bytes(b"corrupt")

            with self.assertRaisesRegex(ImportValidationError, "content hash"):
                import_jefferson(FIXTURE, output)
            self.assertEqual(original.read_bytes(), b"corrupt")

    def test_rejects_zip_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "unsafe.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../summary.xml", FIXTURE.read_bytes())

            with self.assertRaisesRegex(ImportValidationError, "unsafe path"):
                import_jefferson(source, root / "output")


if __name__ == "__main__":
    unittest.main()
