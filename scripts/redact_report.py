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
    origin = report.get("input", {}).get("origin", {})
    public_input_hash = (
        report.get("input", {}).get("sha256")
        if report.get("scope") == "tooling_harness_only" and origin.get("source_url")
        else "withheld"
    )
    expected_content = report.get("expected_content", {})
    semantic_pdf = report.get("semantic_pdf") or {}
    manifest_path = args.private_report.parent / "output-manifest.json"
    manifest_count = len(json.loads(manifest_path.read_text(encoding="utf-8"))) if manifest_path.exists() else "not reported"

    lines = [
        "# JON-107 redacted execution checkpoint",
        "",
        f"- Test ID: `{report['run']['test_id']}`",
        f"- Scope: `{report.get('scope', 'not reported')}`",
        f"- Assessment: **{report['assessment']['status']}**",
        f"- Converter: `{converter['package']}=={converter['version']}` at commit `{converter['commit']}`",
        f"- Parser dependency: `{converter.get('parser_dependency', 'not reported')}`",
        f"- PDF renderer: `{converter.get('semantic_pdf_renderer', 'not reported')}`",
        f"- Tool versions: `{json.dumps(report.get('tool_versions', {}), sort_keys=True)}`",
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
        f"- Declared expected counts: `{json.dumps(expected_content, sort_keys=True)}`",
        f"- Conversion path: `{semantic_pdf.get('path', 'not reported')}`",
        f"- Rendered PDF pass: `{semantic_pdf.get('pass', False)}`",
        f"- Rendered PDF SHA-256: `{semantic_pdf.get('output_pdf_sha256') if report.get('scope') == 'tooling_harness_only' else 'withheld'}`",
        f"- Rendered PDF expected text matches: `{sum(1 for item in semantic_pdf.get('expected_text_results', []) if item.get('native_text_match') and item.get('pdf_text_match'))}` / `{len(semantic_pdf.get('expected_text_results', []))}`",
        f"- Private output manifest entries: `{manifest_count}`",
        f"- Public fixture source: `{origin.get('source_url') or 'not reported'}`",
        f"- Fixture license: `{origin.get('license') or 'not reported'}`",
        f"- Public fixture input SHA-256: `{public_input_hash}`",
        f"- Synthetic generation method: `{origin.get('synthetic_generation_method') or 'not used'}`",
        "- Redaction status: `redacted_by_allowlist; manual disclosure review still required`",
        "",
        "This checkpoint intentionally omits filenames, paths, private hashes, extracted text, hierarchy titles, logs, and medical content.",
        "A tooling-only pass does not verify the private medical fixture or baseline; the medical-migration blocker remains.",
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
