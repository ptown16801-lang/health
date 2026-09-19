#!/usr/bin/env python3
"""Materialize the integrated controlled corpus as Android application assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from scripts.run_android_acceptance import build_controlled_candidate


def _kind(media_type: str) -> str:
    if media_type == "application/pdf":
        return "PDF"
    if media_type.startswith("image/"):
        return "IMAGE"
    return "TEXT"


def build_android_corpus(output: Path) -> None:
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        controlled = build_controlled_candidate(Path(directory))
        records: list[dict[str, object]] = []

        assets = {item["sha256"]: item for item in controlled.one_manifest["assets"]}
        search = {item["occurrence_id"]: item for item in controlled.one_manifest["searchable_text"]}
        for occurrence in controlled.one_manifest["occurrences"]:
            provenance = occurrence["provenance"]
            if "asset_sha256" in occurrence:
                asset = assets[occurrence["asset_sha256"]]
                path = f"onenote/{asset['bundle_path']}"
                media_type = asset["media_type"]
                source_version = f"sha256:{asset['sha256']}"
            elif occurrence["id"] in search:
                item = search[occurrence["id"]]
                path = f"onenote/{item['text_path']}"
                media_type = "text/plain"
                source_version = f"sha256:{item['sha256']}"
            else:
                continue
            records.append({
                "id": occurrence["id"],
                "title": (
                    f"OneNote · {provenance['page_title']} · "
                    f"{occurrence.get('source_filename', occurrence['kind'])}"
                ),
                "kind": _kind(media_type),
                "source_version": source_version,
                "page": provenance["page_index"],
                "path": path,
            })

        artifact = controlled.jefferson_manifest["artifact"]
        records.append({
            "id": "jefferson-controlled-ccda",
            "title": "Jefferson · Synthetic C-CDA source",
            "kind": "TEXT",
            "source_version": f"sha256:{artifact['sha256']}",
            "page": None,
            "path": f"jefferson/{artifact['stored_path']}",
        })
        normalized = controlled.jefferson_manifest["normalized"]
        records.append({
            "id": "jefferson-controlled-normalized",
            "title": "Jefferson · Normalized synthetic records",
            "kind": "TEXT",
            "source_version": f"records:{normalized['record_count']}",
            "page": None,
            "path": f"jefferson/{normalized['stored_path']}",
        })
        records.append({
            "id": "controlled-repeat-labs",
            "title": "Timeline · Repeats and conflicts",
            "kind": "TEXT",
            "source_version": "health.normalized/v1",
            "page": None,
            "path": "records.json",
        })
        (controlled.root / "android-index.json").write_text(
            json.dumps({"schema": "health.android-controlled/v1", "records": records}, indent=2) + "\n",
            encoding="utf-8",
        )
        shutil.copytree(controlled.root, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_android_corpus(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
