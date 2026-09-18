#!/usr/bin/env python3
"""Run the controlled non-PHI Android-candidate acceptance gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from health_ingest.archive import export_archive, import_archive, snapshot
from health_ingest.jefferson import import_jefferson
from scripts.ingest_onenote import ingest as ingest_onenote
from scripts.normalize_records import normalize


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = datetime(2026, 9, 18, tzinfo=timezone.utc)


def _event_groups(result: dict) -> set[frozenset[str]]:
    return {
        frozenset(assertion["id"] for assertion in event["assertions"])
        for event in result["events"]
    }


def run_acceptance(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    candidate = workspace / "candidate"
    candidate.mkdir()

    synthetic_one = workspace / "Synthetic Acceptance.one"
    synthetic_one.write_bytes(b"synthetic-non-phi-onenote-container\n")
    one_output = candidate / "onenote"
    one_manifest = ingest_onenote(
        synthetic_one,
        ROOT / "fixtures/onenote-derived-synthetic",
        one_output,
        pdf_text=lambda path: "Synthetic selectable PDF evidence" if path.name == "searchable.pdf" else "",
        ocr=lambda path, _media_type: f"Synthetic OCR evidence for {path.name}",
    )

    jefferson_output = candidate / "jefferson"
    jefferson_manifest = import_jefferson(
        ROOT / "tests/data/jefferson-synthetic-ccda.xml",
        jefferson_output,
        clock=lambda: FIXED_TIME,
    )

    repeat_fixture = json.loads(
        (ROOT / "fixtures/repeat-labs.synthetic.json").read_text(encoding="utf-8")
    )
    normalized = normalize(repeat_fixture)
    (candidate / "records.json").write_text(
        json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    expected_groups = {
        frozenset(assertion_ids)
        for assertion_ids in repeat_fixture["expected_event_assertions"]
    }
    actual_groups = _event_groups(normalized)
    false_merges = sorted(
        sorted(group) for group in actual_groups if group not in expected_groups and len(group) > 1
    )
    if actual_groups != expected_groups:
        raise AssertionError("controlled repeat-lab grouping differs from the reviewed expectation")

    observations = sorted(
        (
            assertion["payload"]["observed_at"],
            assertion["id"],
        )
        for event in normalized["events"]
        for assertion in event["assertions"]
    )
    repeat_ids = [item[1] for item in observations if item[1].startswith("repeat-")]
    if repeat_ids != ["repeat-morning", "repeat-afternoon"]:
        raise AssertionError("same-day timeline observations were collapsed or misordered")

    search_entries = []
    for item in one_manifest["searchable_text"]:
        text = (one_output / item["text_path"]).read_text(encoding="utf-8")
        if "synthetic" in text.casefold():
            search_entries.append({"source": "onenote", "id": item["occurrence_id"]})
    normalized_path = jefferson_output / jefferson_manifest["normalized"]["stored_path"]
    for line in normalized_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        searchable = " ".join(str(record.get(field) or "") for field in ("title", "narrative"))
        if "synthetic" in searchable.casefold():
            search_entries.append({"source": "jefferson", "id": record["id"]})
    if {entry["source"] for entry in search_entries} != {"onenote", "jefferson"}:
        raise AssertionError("cross-source synthetic search did not return both sources")

    visual_assets = [
        item for item in one_manifest["assets"]
        if item["media_type"] == "application/pdf" or item["media_type"].startswith("image/")
    ]
    if not visual_assets or not all((one_output / item["bundle_path"]).is_file() for item in visual_assets):
        raise AssertionError("visual evidence assets are unavailable for source browsing")

    before = snapshot(candidate)
    exported = workspace / "controlled-export.zip"
    restored = workspace / "restored"
    export_archive(candidate, exported)
    import_archive(exported, restored)
    after = snapshot(restored)
    if before != after:
        raise AssertionError("export/re-import changed candidate bytes")

    return {
        "classification": "synthetic_non_phi",
        "gate": "pass",
        "false_automatic_merges": len(false_merges),
        "coverage": {
            "source_and_visual_browsing": {"status": "pass", "visual_assets": len(visual_assets)},
            "onenote_ingestion": {"status": "pass", "occurrences": len(one_manifest["occurrences"])},
            "jefferson_ingestion": {
                "status": "pass",
                "records": jefferson_manifest["normalized"]["record_count"],
            },
            "provenance": {"status": "pass", "evidence_items": len(normalized["evidence"])},
            "duplicates_conflicts_and_repeats": {"status": "pass", "events": len(normalized["events"])},
            "search": {"status": "pass", "matching_records": len(search_entries)},
            "timeline": {"status": "pass", "observations": len(observations)},
            "export_round_trip": {"status": "pass", "files": len(before)},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the JSON gate report here")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        report = run_acceptance(Path(directory))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
