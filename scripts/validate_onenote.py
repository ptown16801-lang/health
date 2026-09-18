#!/usr/bin/env python3
"""Run an isolated JON-107 OneNote extraction validation."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
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
            "pdftotext_exit_status": text_code,
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


def compare_text_baseline(extracted: Path, baseline: dict, comparison_dir: Path) -> dict:
    comparison_dir.mkdir()
    image_paths = []
    for path in extracted.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            image_paths.append(path)
    ocr_records = []
    combined_lines = []
    for index, image_path in enumerate(image_paths, 1):
        stdout_path = comparison_dir / f"image-{index:04d}.ocr.txt"
        stderr_path = comparison_dir / f"image-{index:04d}.stderr.log"
        exit_status = run_capture(
            ["tesseract", str(image_path), "stdout", "--psm", "6"], stdout_path, stderr_path,
            block_network=True,
        )
        lines = stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
        combined_lines.extend(lines)
        ocr_records.append({"image_index": index, "exit_status": exit_status, "text_characters": sum(map(len, lines))})

    windows = []
    for index in range(len(combined_lines)):
        windows.append(normalize(" ".join(combined_lines[index:index + 3])))
    row_results = []
    for expected in baseline.get("expected_rows", []):
        tokens = [normalize(str(token)) for token in expected.get("tokens", [])]
        row_results.append({
            "id": expected.get("id", "unnamed-row"),
            "matched_in_single_three-line_window": bool(tokens) and any(all(token in window for token in tokens) for window in windows),
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
        "all_expected_rows_matched": bool(row_results) and all(item["matched_in_single_three-line_window"] for item in row_results),
        "interpretation": "OCR is comparison evidence only; extracted image bytes remain the source.",
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
    parser.add_argument("--max-input-bytes", type=int, default=5 * 1024 * 1024 * 1024)
    parser.add_argument("--allow-dirty-repository", action="store_true", help="Development-only override")
    args = parser.parse_args()

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
    converter_python = args.converter_python.resolve()
    if not converter_python.is_file():
        parser.error("converter Python not found; run scripts/install_converter.sh first")

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
            [str(converter_python), "-c", "import importlib.metadata as m; print(m.version('onenote-tool')); print(m.version('pyOneNote'))"],
            text=True,
        ).splitlines()
    except subprocess.CalledProcessError as exc:
        parser.error(f"cannot verify converter installation: {exc}")
    if versions != [VERSION, PARSER_VERSION]:
        parser.error(f"dependency version mismatch: required {VERSION}/{PARSER_VERSION}, found {versions}")

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
    findings.append({"severity": "required", "message": "Missing source-visible content cannot be cleared until manual source-to-output inspection is completed."})

    after = fixture.stat()
    final_original_hash = file_sha256(fixture)
    report = {
        "schema_version": 1,
        "run": {"id": run_id, "test_id": "JON-107-onenote-extraction", "started_at": datetime.now(timezone.utc).isoformat(), "private_directory": str(run_dir)},
        "input": {
            "original_filename": fixture.name,
            "size": before.st_size,
            "sha256": original_hash,
            "preserved_copy": str(source_copy.relative_to(run_dir)),
            "copy_sha256": copy_hash,
            "copy_matches": original_hash == copy_hash,
            "original_unchanged_during_run": before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns and original_hash == final_original_hash,
        },
        "converter": {
            "package": PACKAGE,
            "version": VERSION,
            "parser_dependency": f"pyOneNote=={PARSER_VERSION}",
            "repository": REPOSITORY,
            "commit": COMMIT,
            "installation_method": "pip install of locally cloned, detached, commit-verified source with cli extra",
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
        "converter_findings": inventory.get("failed_elements", {}),
        "pdf_inspection": pdf_records,
        "duplicates": duplicates,
        "written_baseline_comparison": baseline_comparison,
        "references": {
            "count": len(reference_records),
            "items": reference_records,
            "comparison_status": "manual_review_required" if references else "not_applicable_no_references",
            "comparison_instruction": "Compare every supplied source screenshot against extracted hierarchy, HTML/native text, images, attachments, and tables; record omissions/corruption in the private report before changing status.",
        },
        "assessment": {"status": "BLOCKED_NOT_VALIDATED", "findings": findings},
        "evidence": {"reference": "private run directory only", "redaction_status": "not_redacted_do_not_publish"},
    }
    report_path = run_dir / "evidence-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "evidence-report.md").write_text(markdown_report(report), encoding="utf-8")
    final_manifest = manifest(run_dir)
    (run_dir / "output-manifest.json").write_text(json.dumps(final_manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(run_dir, stat.S_IRWXU)

    print(f"Private run complete: {run_dir}")
    print("Assessment: BLOCKED_NOT_VALIDATED")
    return 0 if exit_status == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
