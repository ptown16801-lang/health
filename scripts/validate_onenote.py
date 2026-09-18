#!/usr/bin/env python3
"""Run an isolated JON-107 OneNote extraction validation."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
import mimetypes
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid

PACKAGE = "onenote-tool"
VERSION = "0.1.5"
REPOSITORY = "https://github.com/vanarebane/onenote-tool.git"
COMMIT = "abd2065c28a2dcfd45edcc944d8be078c313dd02"
PARSER_VERSION = "0.0.2"
RENDERER_VERSION = "66.0"
ONE_MAGIC = bytes.fromhex("e4525c7b8cd8a74daeb15378d02996d3")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def is_git_tracked(path: Path, repository: Path) -> bool:
    if not is_relative_to(path, repository):
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path.relative_to(repository))],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def manifest(root: Path) -> list[dict]:
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append({
            "path": str(path.relative_to(root)),
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
            "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        })
    return entries


def run_capture(command: list[str], stdout_path: Path, stderr_path: Path, *, block_network: bool = False) -> int:
    environment = os.environ.copy()
    if block_network:
        environment.update({
            "ALL_PROXY": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "",
        })
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        completed = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            env=environment, check=False,
        )
    return completed.returncode


def version_line(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    lines = (completed.stdout + completed.stderr).splitlines()
    return lines[0].strip() if lines else "unavailable"


def inspect_pdfs(extracted: Path, inspection_dir: Path) -> list[dict]:
    inspection_dir.mkdir()
    records = []
    candidates = []
    for path in extracted.rglob("*"):
        if path.is_file():
            with path.open("rb") as stream:
                if stream.read(5) == b"%PDF-":
                    candidates.append(path)
    for index, pdf in enumerate(candidates, 1):
        item_dir = inspection_dir / f"pdf-{index:04d}"
        item_dir.mkdir()
        info_code = run_capture(
            ["pdfinfo", str(pdf)], item_dir / "pdfinfo.stdout.txt", item_dir / "pdfinfo.stderr.txt"
        )
        text_code = run_capture(
            ["pdftotext", "-layout", str(pdf), str(item_dir / "direct-text.txt")],
            item_dir / "pdftotext.stdout.txt",
            item_dir / "pdftotext.stderr.txt",
        )
        text_path = item_dir / "direct-text.txt"
        text_chars = len(text_path.read_text(encoding="utf-8", errors="replace").strip()) if text_path.exists() else 0
        records.append({
            "source_path": str(pdf.relative_to(extracted)),
            "sha256": file_sha256(pdf),
            "pdfinfo_exit_status": info_code,
            "pdfinfo_command": ["pdfinfo", str(pdf)],
            "pdftotext_exit_status": text_code,
            "pdftotext_command": ["pdftotext", "-layout", str(pdf), str(item_dir / "direct-text.txt")],
            "integrity": "pass" if info_code == 0 and text_code == 0 else "fail",
            "direct_text_characters": text_chars,
            "ocr": "not_run; optional comparison only",
        })
    return records


def summarize_inventory(inventory: dict) -> dict:
    totals = Counter(sections=len(inventory.get("sections", [])))
    hierarchy = []
    for section in inventory.get("sections", []):
        hierarchy.append({
            "group_path": section.get("group_path", []),
            "section": section.get("name"),
            "pages": [page.get("title") for page in section.get("pages", [])],
        })
        for page in section.get("pages", []):
            totals["pages"] += 1
            totals["native_text_characters"] += page.get("native_text_characters", 0)
            totals["tables"] += page.get("table_count", 0)
            totals["images"] += len(page.get("images", []))
            totals["attachments"] += len(page.get("attachments", []))
    return {"totals": dict(totals), "hierarchy": hierarchy}


def recovered_asset_duplicates(inventory: dict) -> list[list[str]]:
    by_hash = defaultdict(list)
    for section_index, section in enumerate(inventory.get("sections", []), 1):
        for page_index, page in enumerate(section.get("pages", []), 1):
            for kind in ("images", "attachments"):
                for asset_index, asset in enumerate(page.get(kind, []), 1):
                    digest = asset.get("sha256")
                    if digest:
                        by_hash[digest].append(
                            f"section-{section_index}/page-{page_index}/{kind}-{asset_index}"
                        )
    return [references for references in by_hash.values() if len(references) > 1]


def normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def validate_text_baseline(baseline: dict) -> None:
    expected_images = baseline.get("expected_image_count")
    if expected_images is not None and (
        not isinstance(expected_images, int) or isinstance(expected_images, bool) or expected_images < 0
    ):
        raise ValueError("expected_image_count must be a non-negative integer")

    rows = baseline.get("expected_rows", [])
    if not isinstance(rows, list):
        raise ValueError("expected_rows must be a list")
    row_ids = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("every expected row must have a non-empty string id")
        tokens = row.get("tokens")
        if not isinstance(tokens, list) or not tokens or any(
            not isinstance(token, str) or not normalize(token) for token in tokens
        ):
            raise ValueError("every expected row must have one or more non-empty string tokens")
        row_ids.append(row["id"])
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("expected row ids must be unique")

    known_ids = set(row_ids)
    groups = baseline.get("must_remain_distinct", [])
    if not isinstance(groups, list):
        raise ValueError("must_remain_distinct must be a list of row-id lists")
    for group in groups:
        if not isinstance(group, list) or len(group) < 2 or any(item not in known_ids for item in group):
            raise ValueError("each must_remain_distinct group needs at least two known row ids")
        if len(group) != len(set(group)):
            raise ValueError("must_remain_distinct groups cannot repeat a row id")


def maximum_nonoverlapping_matches(
    row_candidates: dict[str, list[tuple[int, int, int]]], row_ids: list[str]
) -> int:
    """Return how many rows can occupy distinct, non-overlapping OCR windows."""

    ordered = sorted(row_ids, key=lambda row_id: len(row_candidates.get(row_id, [])))

    def search(index: int, occupied: set[tuple[int, int]], matched: int) -> int:
        if index == len(ordered):
            return matched
        best = search(index + 1, occupied, matched)
        for image_index, line_index, span in row_candidates.get(ordered[index], []):
            window = {(image_index, offset) for offset in range(line_index, line_index + span)}
            if occupied.isdisjoint(window):
                best = max(best, search(index + 1, occupied | window, matched + 1))
        return best

    return search(0, set(), 0)


def compare_text_baseline(extracted: Path, baseline: dict, comparison_dir: Path) -> dict:
    comparison_dir.mkdir()
    image_paths = []
    for path in extracted.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            image_paths.append(path)
    ocr_records = []
    lines_by_image = []
    for index, image_path in enumerate(image_paths, 1):
        stdout_path = comparison_dir / f"image-{index:04d}.ocr.txt"
        stderr_path = comparison_dir / f"image-{index:04d}.stderr.log"
        exit_status = run_capture(
            ["tesseract", str(image_path), "stdout", "--psm", "6"], stdout_path, stderr_path,
            block_network=True,
        )
        lines = stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
        lines_by_image.append(lines)
        ocr_records.append({"image_index": index, "exit_status": exit_status, "text_characters": sum(map(len, lines))})

    lines = [
        {
            "image_index": image_index,
            "line_index": line_index,
            "normalized_text": normalize(line),
        }
        for image_index, image_lines in enumerate(lines_by_image, 1)
        for line_index, line in enumerate(image_lines)
    ]
    windows = [
        {
            "image_index": image_index,
            "line_index": line_index,
            "normalized_text": normalize(" ".join(lines[line_index:line_index + 3])),
        }
        for image_index, lines in enumerate(lines_by_image, 1)
        for line_index in range(len(lines))
    ]
    row_results = []
    row_candidates = {}
    for expected in baseline.get("expected_rows", []):
        tokens = [normalize(token) for token in expected["tokens"]]
        candidates = [
            (line["image_index"], line["line_index"], 1)
            for line in lines
            if all(token in line["normalized_text"] for token in tokens)
        ]
        if not candidates:
            candidates = [
                (window["image_index"], window["line_index"], 3)
                for window in windows
                if all(token in window["normalized_text"] for token in tokens)
            ]
        row_candidates[expected["id"]] = candidates
        row_results.append({
            "id": expected["id"],
            "matched_in_single_three_line_window": bool(candidates),
            "candidate_window_count": len(candidates),
        })
    distinct_results = []
    for group in baseline.get("must_remain_distinct", []):
        matched = maximum_nonoverlapping_matches(row_candidates, group)
        distinct_results.append({
            "row_ids": group,
            "required_distinct_rows": len(group),
            "observed_distinct_nonoverlapping_rows": matched,
            "pass": matched == len(group),
        })
    expected_images = baseline.get("expected_image_count")
    return {
        "reference_type": "written_text_ground_truth_not_screenshot",
        "expected_image_count": expected_images,
        "observed_image_count": len(image_paths),
        "image_count_matches": expected_images is None or expected_images == len(image_paths),
        "ocr_engine": "tesseract",
        "ocr_records": ocr_records,
        "expected_rows": row_results,
        "all_expected_rows_matched": bool(row_results) and all(item["matched_in_single_three_line_window"] for item in row_results),
        "must_remain_distinct": distinct_results,
        "all_distinctness_requirements_met": all(item["pass"] for item in distinct_results),
        "interpretation": "OCR is comparison evidence only; extracted image bytes remain the source.",
    }


def render_semantic_pdf(
    extracted: Path, inventory: dict, run_dir: Path, renderer: Path, expected_text: list[str]
) -> dict:
    render_dir = run_dir / "semantic-pdf"
    render_dir.mkdir()
    fragments = ["<!doctype html><meta charset='utf-8'><style>body{font:12pt sans-serif}h1{page-break-before:always}h1:first-of-type{page-break-before:auto}</style>"]
    native_text_parts = []
    for section in inventory.get("sections", []):
        fragments.append(f"<h1>Section: {html.escape(section.get('name') or 'Untitled')}</h1>")
        for page in section.get("pages", []):
            fragments.append(f"<h2>{html.escape(page.get('title') or 'Untitled')}</h2>")
            content_path = extracted / page["content_path"]
            fragments.append(content_path.read_text(encoding="utf-8"))
            text_path = content_path.with_name("native-text.txt")
            native_text_parts.append(page.get("title") or "")
            native_text_parts.append(text_path.read_text(encoding="utf-8", errors="replace"))
    html_path = render_dir / "semantic-inspection.html"
    pdf_path = render_dir / "semantic-inspection.pdf"
    html_path.write_text("\n".join(fragments), encoding="utf-8")
    command = [str(renderer), str(html_path), str(pdf_path)]
    exit_status = run_capture(
        command, render_dir / "renderer.stdout.log", render_dir / "renderer.stderr.log", block_network=True
    )
    inspection = inspect_pdfs(render_dir, run_dir / "semantic-pdf-inspection")
    direct_text_path = run_dir / "semantic-pdf-inspection" / "pdf-0001" / "direct-text.txt"
    pdf_text = direct_text_path.read_text(encoding="utf-8", errors="replace") if direct_text_path.exists() else ""
    native_text = "\n".join(native_text_parts)
    expectations = [
        {
            "id": f"expected-text-{index:03d}",
            "native_text_match": value.casefold() in native_text.casefold(),
            "pdf_text_match": value.casefold() in pdf_text.casefold(),
        }
        for index, value in enumerate(expected_text, 1)
    ]
    return {
        "path": "onenote-tool semantic parse -> inspection HTML -> WeasyPrint PDF -> Poppler pdfinfo/pdftotext",
        "renderer": f"weasyprint=={RENDERER_VERSION}",
        "renderer_command": command,
        "renderer_command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
        "renderer_exit_status": exit_status,
        "output_pdf_sha256": file_sha256(pdf_path) if pdf_path.exists() else None,
        "output_pdf_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
        "pdf_inspection": inspection,
        "expected_text_results": expectations,
        "pass": exit_status == 0 and len(inspection) == 1 and inspection[0]["integrity"] == "pass" and all(item["native_text_match"] and item["pdf_text_match"] for item in expectations),
        "limitation": "Semantic/lossy inspection PDF; not a pixel-perfect OneNote page rendering.",
    }


def markdown_report(report: dict) -> str:
    status = report["assessment"]["status"]
    totals = report.get("content", {}).get("totals", {})
    lines = [
        "# JON-107 private converter evidence report",
        "",
        "> Protected health information: keep this report in private local storage. Do not commit, upload, or paste it.",
        "",
        f"Run: `{report['run']['id']}`  ",
        f"Status: **{status}**  ",
        f"Converter exit status: `{report['execution']['exit_status']}`",
        "",
        "## Converter pin",
        "",
        f"`{PACKAGE}=={VERSION}` from `{REPOSITORY}` at `{COMMIT}`.",
        "",
        "## Recovered content",
        "",
    ]
    for key in ("sections", "pages", "native_text_characters", "images", "attachments", "tables"):
        lines.append(f"- {key.replace('_', ' ')}: {totals.get(key, 0)}")
    lines.extend(["", "## Findings", ""])
    for finding in report["assessment"]["findings"]:
        lines.append(f"- [{finding['severity']}] {finding['message']}")
    lines.extend([
        "",
        "## Manual source comparison",
        "",
        f"Reference screenshots: {report['references']['count']}. ",
        report["references"]["comparison_instruction"],
        "",
        "Validation remains blocked until a representative private fixture and source-to-output manual inspection are recorded.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="Private .one or .onepkg fixture")
    parser.add_argument("--reference", action="append", type=Path, default=[], help="Private source screenshot (repeatable)")
    parser.add_argument("--private-root", type=Path, default=Path(".private/runs"))
    parser.add_argument("--converter-python", type=Path, default=Path(".private/tools/venv/bin/python"))
    parser.add_argument("--converter-source", type=Path, default=Path(".private/tools/onenote-tool"))
    parser.add_argument("--text-baseline", type=Path, help="Private JSON written ground truth; enables local OCR comparison")
    parser.add_argument("--fixture-source-url", help="Public fixture provenance URL")
    parser.add_argument("--fixture-license", help="SPDX identifier or license name for a public fixture")
    parser.add_argument("--synthetic-generation-method", help="Method used to create a synthetic fixture")
    parser.add_argument(
        "--expected-count", action="append", default=[], metavar="CATEGORY=COUNT",
        help="Non-sensitive expected total (sections/pages/images/attachments/tables; repeatable)",
    )
    parser.add_argument("--expected-text", action="append", default=[], help="Known-good source-visible text expected in native and rendered PDF text")
    parser.add_argument("--max-input-bytes", type=int, default=5 * 1024 * 1024 * 1024)
    parser.add_argument("--allow-dirty-repository", action="store_true", help="Development-only override")
    args = parser.parse_args()
    if args.fixture_source_url and args.synthetic_generation_method:
        parser.error("choose public fixture provenance or synthetic generation, not both")
    if args.fixture_source_url and not args.fixture_license:
        parser.error("--fixture-source-url requires --fixture-license")
    expectations = {}
    allowed_expectations = {"sections", "pages", "images", "attachments", "tables"}
    for raw_expectation in args.expected_count:
        try:
            category, raw_count = raw_expectation.split("=", 1)
            count = int(raw_count)
        except ValueError:
            parser.error("--expected-count must be CATEGORY=COUNT")
        if category not in allowed_expectations or count < 0:
            parser.error("expected-count category/count is invalid")
        expectations[category] = count

    fixture = args.fixture.resolve()
    if fixture.is_symlink() or fixture.suffix.lower() not in {".one", ".onepkg"} or not fixture.is_file():
        parser.error("fixture must be an existing regular .one or .onepkg file")
    if fixture.stat().st_size > args.max_input_bytes:
        parser.error("fixture exceeds --max-input-bytes")
    with fixture.open("rb") as stream:
        signature = stream.read(16)
    if fixture.suffix.lower() == ".one" and signature != ONE_MAGIC:
        parser.error("fixture does not have the expected MS-ONESTORE signature")
    if fixture.suffix.lower() == ".onepkg" and signature[:4] != b"MSCF":
        parser.error("fixture does not have the expected CAB signature")
    references = [path.resolve() for path in args.reference]
    if any(path.is_symlink() or not path.is_file() for path in references):
        parser.error("every --reference must be an existing regular file")
    baseline_path = args.text_baseline.resolve() if args.text_baseline else None
    if baseline_path and (baseline_path.is_symlink() or not baseline_path.is_file()):
        parser.error("--text-baseline must be an existing regular JSON file")
    # Keep the venv executable path itself. Resolving its symlink to the base
    # interpreter bypasses pyvenv.cfg and loses the pinned installed packages.
    converter_python = Path(os.path.abspath(args.converter_python))
    if not converter_python.is_file():
        parser.error("converter Python not found; run scripts/install_converter.sh first")
    renderer = converter_python.parent / "weasyprint"
    if not renderer.is_file():
        parser.error("pinned WeasyPrint renderer not found; rerun scripts/install_converter.sh")

    repository = Path(__file__).resolve().parents[1]
    private_inputs = [fixture, *references, *([baseline_path] if baseline_path else [])]
    if any(is_git_tracked(path, repository) for path in private_inputs):
        parser.error("refusing a Git-tracked fixture/reference; move protected input to private storage")
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repository, text=True)
    if dirty and not args.allow_dirty_repository:
        parser.error("repository is not clean; review git status before processing PHI")
    private_root = args.private_root.resolve()
    repository_private = repository / ".private"
    if is_relative_to(private_root, repository) and not is_relative_to(private_root, repository_private):
        parser.error("in-repository run storage must be under the ignored .private directory")
    executables = ["pdfinfo", "pdftotext"] + (["tesseract"] if baseline_path else [])
    for executable in executables:
        if shutil.which(executable) is None:
            parser.error(f"required PDF tool not found: {executable}")
    if fixture.suffix.lower() == ".onepkg" and not (shutil.which("cabextract") or shutil.which("expand")):
        parser.error(".onepkg requires cabextract (or Windows expand.exe)")

    converter_source = args.converter_source.resolve()
    try:
        source_commit = subprocess.check_output(
            ["git", "-C", str(converter_source), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError as exc:
        parser.error(f"cannot verify converter source checkout: {exc}")
    if source_commit != COMMIT:
        parser.error(f"converter commit mismatch: required {COMMIT}, found {source_commit}")
    source_dirty = subprocess.run(
        ["git", "-C", str(converter_source), "diff", "--quiet"], check=False
    ).returncode
    if source_dirty:
        parser.error("converter source checkout has local modifications")

    try:
        versions = subprocess.check_output(
            [str(converter_python), "-c", "import importlib.metadata as m; print(m.version('onenote-tool')); print(m.version('pyOneNote')); print(m.version('weasyprint'))"],
            text=True,
        ).splitlines()
    except subprocess.CalledProcessError as exc:
        parser.error(f"cannot verify converter installation: {exc}")
    if versions != [VERSION, PARSER_VERSION, RENDERER_VERSION]:
        parser.error(f"dependency version mismatch: required {VERSION}/{PARSER_VERSION}/{RENDERER_VERSION}, found {versions}")

    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private_root, 0o700)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    run_dir = private_root / run_id
    run_dir.mkdir(mode=0o700)
    source_dir = run_dir / "source"
    source_dir.mkdir(mode=0o700)

    before = fixture.stat()
    source_copy = source_dir / ("fixture" + fixture.suffix.lower())
    shutil.copy2(fixture, source_copy)
    original_hash = file_sha256(fixture)
    copy_hash = file_sha256(source_copy)
    reference_records = []
    reference_dir = run_dir / "references"
    if references:
        reference_dir.mkdir(mode=0o700)
        for index, reference in enumerate(references, 1):
            destination = reference_dir / f"reference-{index:04d}{reference.suffix.lower()}"
            shutil.copy2(reference, destination)
            reference_records.append({
                "original_filename": reference.name,
                "size": reference.stat().st_size,
                "sha256": file_sha256(reference),
                "private_copy": str(destination.relative_to(run_dir)),
            })
    baseline = None
    if baseline_path:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if not isinstance(baseline, dict):
            parser.error("--text-baseline root must be a JSON object")
        try:
            validate_text_baseline(baseline)
        except ValueError as exc:
            parser.error(f"invalid --text-baseline: {exc}")
        if not reference_dir.exists():
            reference_dir.mkdir(mode=0o700)
        shutil.copy2(baseline_path, reference_dir / "written-text-baseline.json")

    extracted = run_dir / "extracted"
    stdout_path = run_dir / "converter.stdout.log"
    stderr_path = run_dir / "converter.stderr.log"
    driver = Path(__file__).with_name("converter_driver.py").resolve()
    command = [str(converter_python), str(driver), str(source_copy), str(extracted)]
    doctor_command = [str(converter_python.parent / "onenote-tool"), "doctor"]
    doctor_status = run_capture(
        doctor_command, run_dir / "doctor.stdout.log", run_dir / "doctor.stderr.log", block_network=True
    )
    exit_status = run_capture(command, stdout_path, stderr_path, block_network=True)

    inventory_path = extracted / "converter-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8")) if inventory_path.exists() else {}
    content = summarize_inventory(inventory) if inventory else {"totals": {}, "hierarchy": []}
    pdf_records = inspect_pdfs(extracted, run_dir / "pdf-inspection") if extracted.exists() else []
    semantic_pdf = render_semantic_pdf(extracted, inventory, run_dir, renderer, args.expected_text) if inventory else None
    baseline_comparison = compare_text_baseline(extracted, baseline, run_dir / "text-baseline-comparison") if baseline and extracted.exists() else None

    duplicates = recovered_asset_duplicates(inventory)
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    warnings = [line for line in stderr_text.splitlines() if "warn" in line.lower()]

    findings = []
    if exit_status != 0:
        findings.append({"severity": "error", "message": "Converter exited unsuccessfully; inspect private stderr log."})
    if not inventory:
        findings.append({"severity": "error", "message": "No converter inventory was produced (silent/early failure)."})
    if inventory and content["totals"].get("pages", 0) == 0:
        findings.append({"severity": "error", "message": "Converter reported zero pages; possible silent omission."})
    for kind, count in inventory.get("failed_elements", {}).items():
        findings.append({"severity": "error", "message": f"Converter reported unsupported/failed element {kind}: {count}."})
    protected = [section for section in inventory.get("sections", []) if section.get("password_status")]
    if protected:
        findings.append({"severity": "error", "message": "Protected section limitations were reported; tables/layout/content may be incomplete."})
    if doctor_status != 0:
        findings.append({"severity": "error", "message": "onenote-tool doctor preflight failed; inspect private doctor logs."})
    for record in pdf_records:
        if record["integrity"] == "fail":
            findings.append({"severity": "error", "message": "At least one recovered PDF failed structural/text extraction checks."})
    if warnings:
        findings.append({"severity": "warning", "message": f"Converter stderr contains {len(warnings)} warning line(s)."})
    if duplicates:
        findings.append({"severity": "warning", "message": f"Detected {len(duplicates)} byte-identical derived-file group(s); review provenance before deduplication."})
    if references:
        findings.append({"severity": "required", "message": "Reference screenshots supplied; manual source-to-output comparison is not yet attested."})
    else:
        findings.append({"severity": "required", "message": "No reference screenshots were supplied; screenshot comparison is not applicable for this run."})
    if baseline_comparison and not baseline_comparison["image_count_matches"]:
        findings.append({"severity": "error", "message": "Observed image count does not match the private written baseline."})
    if baseline_comparison and not baseline_comparison["all_expected_rows_matched"]:
        findings.append({"severity": "warning", "message": "OCR comparison did not match every written-baseline row; manual image review is required."})
    if baseline_comparison and not baseline_comparison["all_distinctness_requirements_met"]:
        findings.append({"severity": "error", "message": "OCR evidence did not preserve every written-baseline row declared as distinct; private manual review is required."})
    expectation_results = {
        category: {"expected": expected, "observed": content["totals"].get(category, 0), "matches": content["totals"].get(category, 0) == expected}
        for category, expected in expectations.items()
    }
    for category, result in expectation_results.items():
        if not result["matches"]:
            findings.append({"severity": "error", "message": f"Observed {category} count does not match the declared fixture expectation."})
    if not semantic_pdf or not semantic_pdf["pass"]:
        findings.append({"severity": "error", "message": "Semantic OneNote-to-PDF rendering or expected-text verification failed."})
    findings.append({"severity": "required", "message": "Missing source-visible content cannot be cleared until manual source-to-output inspection is completed."})

    after = fixture.stat()
    final_original_hash = file_sha256(fixture)
    report = {
        "schema_version": 1,
        "run": {"id": run_id, "test_id": "JON-107-onenote-extraction", "started_at": datetime.now(timezone.utc).isoformat(), "private_directory": str(run_dir)},
        "scope": "tooling_harness_only" if (args.fixture_source_url or args.synthetic_generation_method) else "private_fixture_validation",
        "input": {
            "original_filename": fixture.name,
            "size": before.st_size,
            "sha256": original_hash,
            "preserved_copy": str(source_copy.relative_to(run_dir)),
            "copy_sha256": copy_hash,
            "copy_matches": original_hash == copy_hash,
            "original_unchanged_during_run": before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns and original_hash == final_original_hash,
            "origin": {
                "source_url": args.fixture_source_url,
                "license": args.fixture_license,
                "synthetic_generation_method": args.synthetic_generation_method,
            },
        },
        "converter": {
            "package": PACKAGE,
            "version": VERSION,
            "parser_dependency": f"pyOneNote=={PARSER_VERSION}",
            "semantic_pdf_renderer": f"weasyprint=={RENDERER_VERSION}",
            "repository": REPOSITORY,
            "commit": COMMIT,
            "installation_method": "pip install of locally cloned, detached, commit-verified source with cli extra",
        },
        "tool_versions": {
            "python": sys.version.split()[0],
            "pdfinfo": version_line(["pdfinfo", "-v"]),
            "pdftotext": version_line(["pdftotext", "-v"]),
            "weasyprint": RENDERER_VERSION,
        },
        "execution": {
            "command": command,
            "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
            "exit_status": exit_status,
            "doctor_command": doctor_command,
            "doctor_exit_status": doctor_status,
            "network_control": "proxy environment redirected to loopback refusal; best effort, not OS network isolation",
            "stdout": stdout_path.name,
            "stderr": stderr_path.name,
            "warning_lines": warnings,
        },
        "content": content,
        "expected_content": expectation_results,
        "converter_findings": inventory.get("failed_elements", {}),
        "pdf_inspection": pdf_records,
        "semantic_pdf": semantic_pdf,
        "duplicates": duplicates,
        "written_baseline_comparison": baseline_comparison,
        "references": {
            "count": len(reference_records),
            "items": reference_records,
            "comparison_status": "manual_review_required" if references else "not_applicable_no_references",
            "comparison_instruction": "Compare every supplied source screenshot against extracted hierarchy, HTML/native text, images, attachments, and tables; record omissions/corruption in the private report before changing status.",
        },
        "assessment": {
            "status": (
                "TOOLING_VALIDATION_PASS_MEDICAL_BLOCK_REMAINS"
                if args.fixture_source_url and semantic_pdf and semantic_pdf["pass"] and not any(item["severity"] == "error" for item in findings)
                else "BLOCKED_NOT_VALIDATED"
            ),
            "findings": findings,
        },
        "evidence": {"reference": "private run directory only", "redaction_status": "not_redacted_do_not_publish"},
    }
    report_path = run_dir / "evidence-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "evidence-report.md").write_text(markdown_report(report), encoding="utf-8")
    final_manifest = manifest(run_dir)
    (run_dir / "output-manifest.json").write_text(json.dumps(final_manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(run_dir, stat.S_IRWXU)

    print(f"Private run complete: {run_dir}")
    print(f"Assessment: {report['assessment']['status']}")
    return 0 if exit_status == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
