from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from health_ingest.archive import (
    ArchiveValidationError,
    export_archive,
    import_archive,
    snapshot,
)


class ArchiveRoundTripTest(unittest.TestCase):
    def test_export_and_import_preserve_every_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            (source / "nested").mkdir(parents=True)
            (source / "manifest.json").write_text('{"synthetic":true}\n', encoding="utf-8")
            (source / "nested/evidence.bin").write_bytes(bytes(range(64)))

            archive = root / "export.zip"
            restored = root / "restored"
            manifest = export_archive(source, archive)
            imported_manifest = import_archive(archive, restored)

            self.assertEqual(manifest, imported_manifest)
            self.assertEqual(snapshot(source), snapshot(restored))

    def test_rejects_tampered_content_without_partial_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "tampered.zip"
            manifest = {
                "schema": "health.local-archive/v1",
                "files": {"record.json": {"sha256": "0" * 64, "size": 2}},
            }
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("archive-manifest.json", json.dumps(manifest))
                output.writestr("files/record.json", b"{}")

            restored = root / "restored"
            with self.assertRaisesRegex(ArchiveValidationError, "integrity check"):
                import_archive(archive, restored)
            self.assertFalse(restored.exists())

    def test_rejects_unmanifested_archive_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "extra.zip"
            manifest = {"schema": "health.local-archive/v1", "files": {}}
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("archive-manifest.json", json.dumps(manifest))
                output.writestr("files/../escape", b"unsafe")
            with self.assertRaisesRegex(ArchiveValidationError, "do not match"):
                import_archive(archive, root / "restored")


if __name__ == "__main__":
    unittest.main()
