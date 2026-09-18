#!/usr/bin/env python3
"""Build a local, provenance-preserving bundle from recovered OneNote content."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Callable


SCHEMA = "health.onenote-ingest/v1"
RASTER_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".pgm", ".png", ".tif", ".tiff", ".webp"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_file(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"recovered path escapes extraction directory: {value}") from error
    if not candidate.is_file():
        raise ValueError(f"recovered file is missing: {value}")
    return candidate


def direct_pdf_text(path: Path, executable: str = "pdftotext") -> str:
    completed = subprocess.run(
        [executable, "-layout", str(path), "-"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"exit status {completed.returncode}"
        raise RuntimeError(f"cannot inspect PDF text: {detail}")
    return completed.stdout.strip()


def command_ocr(command: str) -> Callable[[Path, str], str]:
    arguments = shlex.split(command)
    if not arguments:
        raise ValueError("OCR command cannot be empty")

    def extract(path: Path, _media_type: str) -> str:
        completed = subprocess.run(
            [*arguments, str(path)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or f"exit status {completed.returncode}"
            raise RuntimeError(f"OCR failed: {detail}")
        return completed.stdout.strip()

    return extract


class BundleBuilder:
    def __init__(self, root: Path):
        self.root = root
        self.assets: dict[str, dict] = {}

    def store(self, path: Path, *, media_type: str | None = None) -> tuple[str, dict]:
        digest = file_sha256(path)
        suffix = path.suffix.lower() if re.fullmatch(r"\.[a-z0-9]{1,12}", path.suffix.lower()) else ".bin"
        relative = Path("originals") / digest[:2] / f"{digest}{suffix}"
        destination = self.root / relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        record = {
            "sha256": digest,
            "size": path.stat().st_size,
            "media_type": media_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "bundle_path": str(relative),
        }
        self.assets[digest] = record
        return digest, record

    def write_text(self, key: str, text: str) -> str:
        relative = Path("search") / f"{key}.txt"
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text.rstrip() + ("\n" if text else ""), encoding="utf-8")
        return str(relative)


def ingest(
    source: Path,
    extracted: Path,
    output: Path,
    *,
    pdf_text: Callable[[Path], str] = direct_pdf_text,
    ocr: Callable[[Path, str], str] | None = None,
) -> dict:
    """Ingest converter output. The destination must not already exist."""

    source = source.resolve()
    extracted = extracted.resolve()
    output = output.resolve()
    if source.suffix.lower() not in {".one", ".onepkg"} or not source.is_file():
        raise ValueError("source must be an existing .one or .onepkg file")
    inventory_path = extracted / "converter-inventory.json"
    if not inventory_path.is_file():
        raise ValueError("extraction directory has no converter-inventory.json")
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        builder = BundleBuilder(temporary)
        source_digest, source_asset = builder.store(source, media_type="application/onenote")
        occurrences: list[dict] = []
        searchable: list[dict] = []

        def add_search(occurrence_id: str, text: str, method: str, ocr_status: str) -> None:
            if not text.strip():
                return
            normalized = text.strip()
            searchable.append({
                "occurrence_id": occurrence_id,
                "method": method,
                "ocr_status": ocr_status,
                "text_path": builder.write_text(occurrence_id, normalized),
                "characters": len(normalized),
                "sha256": hashlib.sha256(normalized.encode()).hexdigest(),
            })

        for section_index, section in enumerate(inventory.get("sections", []), 1):
            for page_index, page in enumerate(section.get("pages", []), 1):
                page_id = f"section-{section_index:03d}-page-{page_index:04d}"
                provenance = {
                    "source_sha256": source_digest,
                    "notebook": inventory.get("notebook_name"),
                    "section_index": section_index,
                    "section_name": section.get("name"),
                    "group_path": section.get("group_path", []),
                    "page_index": page_index,
                    "page_title": page.get("title"),
                    "page_created_at": page.get("created_at"),
                }
                native_value = page.get("native_text_path")
                if not native_value and page.get("content_path"):
                    native_value = str(Path(page["content_path"]).with_name("native-text.txt"))
                if native_value:
                    native_path = relative_file(extracted, native_value)
                    native_text = native_path.read_text(encoding="utf-8", errors="replace").strip()
                    native_id = f"{page_id}-native"
                    native_digest = hashlib.sha256(native_text.encode()).hexdigest()
                    expected_digest = page.get("native_text_sha256")
                    if expected_digest and expected_digest != native_digest:
                        raise ValueError(f"hash mismatch for {native_value}")
                    occurrences.append({
                        "id": native_id,
                        "kind": "native_text",
                        "text_sha256": native_digest,
                        "provenance": provenance,
                    })
                    add_search(native_id, native_text, "onenote_native_text", "not_required")

                for kind, entries in (("image", page.get("images", [])), ("attachment", page.get("attachments", []))):
                    for item_index, item in enumerate(entries, 1):
                        occurrence_id = f"{page_id}-{kind}-{item_index:04d}"
                        recovered = relative_file(extracted, item["path"])
                        digest, asset = builder.store(recovered)
                        if item.get("sha256") and item["sha256"] != digest:
                            raise ValueError(f"hash mismatch for {item['path']}")
                        if item.get("size") is not None and item["size"] != recovered.stat().st_size:
                            raise ValueError(f"size mismatch for {item['path']}")
                        occurrence = {
                            "id": occurrence_id,
                            "kind": kind,
                            "source_filename": item.get("source_filename"),
                            "asset_sha256": digest,
                            "provenance": provenance,
                        }
                        occurrences.append(occurrence)
                        suffix = recovered.suffix.lower()
                        media_type = asset["media_type"]
                        if suffix == ".pdf" or media_type == "application/pdf":
                            text = pdf_text(recovered)
                            if text.strip():
                                occurrence["ocr_status"] = "skipped_searchable_pdf"
                                add_search(occurrence_id, text, "pdf_direct_text", "skipped_searchable_pdf")
                            elif ocr:
                                occurrence["ocr_status"] = "performed_image_pdf"
                                add_search(occurrence_id, ocr(recovered, media_type), "ocr", "performed_image_pdf")
                            else:
                                occurrence["ocr_status"] = "required_image_pdf"
                        elif suffix in RASTER_SUFFIXES or media_type.startswith("image/"):
                            if ocr:
                                occurrence["ocr_status"] = "performed_image"
                                add_search(occurrence_id, ocr(recovered, media_type), "ocr", "performed_image")
                            else:
                                occurrence["ocr_status"] = "required_image"
                        elif media_type.startswith("text/"):
                            add_search(
                                occurrence_id,
                                recovered.read_text(encoding="utf-8", errors="replace"),
                                "attachment_native_text",
                                "not_required",
                            )

        manifest = {
            "schema": SCHEMA,
            "source": {
                "original_name": source.name,
                "sha256": source_digest,
                "size": source.stat().st_size,
                "bundle_path": source_asset["bundle_path"],
                "container_type": source.suffix.lower()[1:],
            },
            "converter": {
                "notebook_name": inventory.get("notebook_name"),
                "converted_elements": inventory.get("converted_elements"),
                "failed_elements": inventory.get("failed_elements"),
            },
            "assets": sorted(builder.assets.values(), key=lambda item: item["sha256"]),
            "occurrences": occurrences,
            "searchable_text": searchable,
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        temporary.rename(output)
        return manifest
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="untouched .one or .onepkg source")
    parser.add_argument("extracted", type=Path, help="private converter output directory")
    parser.add_argument("output", type=Path, help="new local Android import bundle")
    parser.add_argument("--pdftotext", default="pdftotext", help="pdftotext executable")
    parser.add_argument(
        "--ocr-command",
        help="optional local command that accepts an image/image-only PDF path and writes text to stdout",
    )
    args = parser.parse_args()

    def pdf_probe(path: Path) -> str:
        return direct_pdf_text(path, args.pdftotext)

    ocr = command_ocr(args.ocr_command) if args.ocr_command else None
    ingest(args.source, args.extracted, args.output, pdf_text=pdf_probe, ocr=ocr)
    print(f"OneNote import bundle written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
