import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
FIXTURE = REPOSITORY / "fixtures" / "onenote-derived-synthetic"

sys.path.insert(0, str(REPOSITORY / "scripts"))

from ingest_onenote import SCHEMA, ingest  # noqa: E402


class OneNoteIngestTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "Synthetic Notebook.one"
        self.source.write_bytes(bytes.fromhex("e4525c7b8cd8a74daeb15378d02996d3") + b"synthetic")

    def tearDown(self):
        self.temporary.cleanup()

    def test_ingests_original_assets_native_text_and_selective_ocr(self):
        ocr_calls = []

        def pdf_text(path):
            return "Selectable PDF text" if path.name == "searchable.pdf" else ""

        def ocr(path, media_type):
            ocr_calls.append((path.name, media_type))
            return f"OCR text for {path.name}"

        output = self.root / "bundle"
        manifest = ingest(self.source, FIXTURE, output, pdf_text=pdf_text, ocr=ocr)

        self.assertEqual(SCHEMA, manifest["schema"])
        self.assertEqual("Synthetic Notebook.one", manifest["source"]["original_name"])
        self.assertTrue((output / manifest["source"]["bundle_path"]).is_file())
        self.assertEqual(5, len(manifest["occurrences"]))
        self.assertEqual({"diagram.pgm", "image-only.pdf"}, {item[0] for item in ocr_calls})

        methods = {item["occurrence_id"]: item for item in manifest["searchable_text"]}
        searchable_pdf = methods["section-001-page-0001-attachment-0002"]
        self.assertEqual("pdf_direct_text", searchable_pdf["method"])
        self.assertEqual("skipped_searchable_pdf", searchable_pdf["ocr_status"])
        occurrences = {item["id"]: item for item in manifest["occurrences"]}
        self.assertEqual(
            "skipped_searchable_pdf",
            occurrences["section-001-page-0001-attachment-0002"]["ocr_status"],
        )
        self.assertEqual("ocr", methods["section-001-page-0001-attachment-0003"]["method"])
        self.assertIn("onenote_native_text", {item["method"] for item in methods.values()})
        self.assertIn("attachment_native_text", {item["method"] for item in methods.values()})
        native = occurrences["section-001-page-0001-native"]
        self.assertEqual("Synthetic Health Notebook", native["provenance"]["notebook"])
        self.assertEqual(manifest["source"]["sha256"], native["provenance"]["source_sha256"])

    def test_records_ocr_requirements_without_an_ocr_engine(self):
        output = self.root / "bundle"
        manifest = ingest(self.source, FIXTURE, output, pdf_text=lambda _path: "")
        statuses = {item.get("ocr_status") for item in manifest["occurrences"]}
        self.assertIn("required_image", statuses)
        self.assertIn("required_image_pdf", statuses)

    def test_rejects_tampered_recovered_asset(self):
        extracted = self.root / "extracted"
        import shutil
        shutil.copytree(FIXTURE, extracted)
        (extracted / "page" / "reference.txt").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            ingest(self.source, extracted, self.root / "bundle", pdf_text=lambda _path: "")
        self.assertFalse((self.root / "bundle").exists())

    def test_fixture_hashes_and_sizes_are_self_consistent(self):
        inventory = json.loads((FIXTURE / "converter-inventory.json").read_text())
        entries = inventory["sections"][0]["pages"][0]
        for item in entries["images"] + entries["attachments"]:
            path = FIXTURE / item["path"]
            self.assertEqual(path.stat().st_size, item["size"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])


if __name__ == "__main__":
    unittest.main()
