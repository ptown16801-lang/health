#!/usr/bin/env python3
"""Private subprocess adapter for onenote-tool. Output is sensitive by design."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

from onenote_tool.convert import convert_onepkg
from onenote_tool.models import ConversionResult, ElementReport, SectionResult
from onenote_tool.parser import parse_one_file


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def safe_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", value).strip(" .")
    return (cleaned or fallback)[:80]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    report = ElementReport()
    if args.fixture.suffix.lower() == ".onepkg":
        result = convert_onepkg(str(args.fixture), work_dir=str(args.output / "unpacked"))
    elif args.fixture.suffix.lower() == ".one":
        pages, password_status = parse_one_file(str(args.fixture), report)
        result = ConversionResult(
            notebook_name=args.fixture.stem,
            sections=[SectionResult(name=args.fixture.stem, pages=pages, password_status=password_status)],
            report=report,
        )
    else:
        raise ValueError("fixture must end in .one or .onepkg")

    inventory: dict = {
        "notebook_name": result.notebook_name,
        "converted_elements": result.report.converted,
        "failed_elements": result.report.failed,
        "sections": [],
    }
    for section_index, section in enumerate(result.sections, 1):
        section_dir = args.output / f"section-{section_index:03d}-{safe_name(section.name, 'untitled')}"
        section_dir.mkdir()
        section_record = {
            "name": section.name,
            "group_path": section.group_path,
            "password_status": section.password_status,
            "pages": [],
        }
        for page_index, page in enumerate(section.pages, 1):
            page_dir = section_dir / f"page-{page_index:04d}-{safe_name(page.title, 'untitled')}"
            page_dir.mkdir()
            joined_html = "\n".join(block.get("html", "") for block in page.blocks)
            (page_dir / "content.html").write_text(joined_html, encoding="utf-8")
            extractor = TextExtractor()
            extractor.feed(joined_html)
            native_text = "\n".join(part.strip() for part in extractor.parts if part.strip())
            (page_dir / "native-text.txt").write_text(native_text, encoding="utf-8")

            images = []
            for image_index, image in enumerate(page.images, 1):
                name = f"image-{image_index:04d}{image.ext or '.bin'}"
                (page_dir / name).write_bytes(image.data)
                images.append({
                    "path": name,
                    "source_filename": image.filename,
                    "size": len(image.data),
                    "sha256": sha256(image.data),
                    "width": image.width,
                    "height": image.height,
                })

            files = []
            for file_index, attached in enumerate(page.files, 1):
                suffix = Path(attached.filename).suffix[:16]
                name = f"attachment-{file_index:04d}{suffix or '.bin'}"
                (page_dir / name).write_bytes(attached.data)
                files.append({
                    "path": name,
                    "source_filename": attached.filename,
                    "size": len(attached.data),
                    "sha256": sha256(attached.data),
                })

            kinds = [block.get("kind", "unknown") for block in page.blocks]
            section_record["pages"].append({
                "title": page.title,
                "content_path": str((page_dir / "content.html").relative_to(args.output)),
                "sub_level": page.sub_level,
                "created_at": page.created_at.isoformat() if page.created_at else None,
                "block_kinds": kinds,
                "native_text_characters": len(native_text),
                "native_text_sha256": sha256(native_text.encode()),
                "table_count": kinds.count("table"),
                "images": images,
                "attachments": files,
            })
        inventory["sections"].append(section_record)

    (args.output / "converter-inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Converter completed; sensitive inventory written to private run storage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
