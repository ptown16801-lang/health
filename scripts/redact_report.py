#!/usr/bin/env python3
"""Create a filename/content/hash-free checkpoint from a private report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_report", type=Path)
    parser.add_argument("--output", type=Path, help="Write redacted Markdown here; defaults to stdout")
    args = parser.parse_args()
    report = json.loads(args.private_report.read_text(encoding="utf-8"))
    converter = report["converter"]
    totals = report.get("content", {}).get("totals", {})
    severities: dict[str, int] = {}
    for finding in report.get("assessment", {}).get("findings", []):
        severity = finding.get("severity", "unknown")
        severities[severity] = severities.get(severity, 0) + 1
    baseline = report.get("written_baseline_comparison") or {}

    lines = [
        "# JON-107 redacted execution checkpoint",
        "",
        f"- Test ID: `{report['run']['test_id']}`",
        f"- Assessment: **{report['assessment']['status']}**",
        f"- Converter: `{converter['package']}=={converter['version']}` at commit `{converter['commit']}`",
        f"- Converter exit status: `{report['execution']['exit_status']}`",
        f"- Command digest: `{report['execution']['command_sha256']}`",
        f"- Reference screenshots supplied: `{report['references']['count'] > 0}`",
        f"- Manual comparison status: `{report['references']['comparison_status']}`",
        f"- Recovered sections/pages: `{totals.get('sections', 0)}` / `{totals.get('pages', 0)}`",
        f"- Recovered images/attachments/tables: `{totals.get('images', 0)}` / `{totals.get('attachments', 0)}` / `{totals.get('tables', 0)}`",
        f"- Recovered PDFs inspected: `{len(report.get('pdf_inspection', []))}`",
        f"- Byte-identical derived groups: `{len(report.get('duplicates', []))}`",
        f"- Written baseline used (not screenshots): `{bool(baseline)}`",
        f"- Expected/observed images: `{baseline.get('expected_image_count', 'not reported')}` / `{baseline.get('observed_image_count', 'not reported')}`",
        f"- Written-baseline rows matched: `{sum(1 for row in baseline.get('expected_rows', []) if row.get('matched_in_single_three_line_window'))}` / `{len(baseline.get('expected_rows', []))}`",
        f"- Finding counts by severity: `{json.dumps(severities, sort_keys=True)}`",
        "- Redaction status: `redacted_by_allowlist; manual disclosure review still required`",
        "",
        "This checkpoint intentionally omits filenames, paths, hashes, extracted text, hierarchy titles, logs, and medical content.",
        "It is not evidence that converter validation passed; the JON-107 blocker remains until private fixture review is complete.",
        "",
    ]
    rendered = "\n".join(lines)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
