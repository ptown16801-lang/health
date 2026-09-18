#!/usr/bin/env python3
"""Verify a normalized result from the synthetic JON-107 Strand pilot."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def verify(spec: dict, result: dict) -> list[str]:
    failures: list[str] = []
    expected_ids = {item["id"] for item in spec["assertions"]}
    observed = [assertion_id for event in result.get("events", []) for assertion_id in event.get("source_assertion_ids", [])]
    counts = Counter(observed)

    missing = sorted(expected_ids - set(observed))
    repeated = sorted(assertion_id for assertion_id, count in counts.items() if count != 1)
    unexpected = sorted(set(observed) - expected_ids)
    if missing:
        failures.append(f"missing source assertions: {', '.join(missing)}")
    if repeated:
        failures.append(f"source assertions mapped more or less than once: {', '.join(repeated)}")
    if unexpected:
        failures.append(f"unexpected source assertions: {', '.join(unexpected)}")

    event_by_assertion = {}
    for event in result.get("events", []):
        if not event.get("provenance_visible"):
            failures.append(f"event {event.get('id', '(unnamed)')} lacks visible-provenance attestation")
        for assertion_id in event.get("source_assertion_ids", []):
            event_by_assertion[assertion_id] = event.get("id")
    for left, right in spec.get("must_remain_separate", []):
        if event_by_assertion.get(left) is not None and event_by_assertion.get(left) == event_by_assertion.get(right):
            failures.append(f"false merge: {left} and {right} share event {event_by_assertion[left]}")

    undo = result.get("incorrect_merge_undo", {})
    if undo.get("pair") != spec.get("intentional_incorrect_merge_pair"):
        failures.append("undo evidence references the wrong test pair")
    if not undo.get("merge_attempted") or not undo.get("undo_succeeded"):
        failures.append("intentional incorrect merge/undo was not successfully attested")

    reimported = result.get("round_trip", {}).get("reimported_assertion_ids", [])
    if set(reimported) != expected_ids or len(reimported) != len(expected_ids):
        failures.append("round-trip assertion set is incomplete or duplicated")
    manual = result.get("manual_review", {})
    for check in ("timeline_usable", "search_usable", "export_inspected"):
        if not manual.get(check):
            failures.append(f"manual review not attested: {check}")
    if not result.get("workspace_is_synthetic_only"):
        failures.append("workspace is not attested as synthetic-only")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    failures = verify(spec, result)
    if failures:
        print("STRAND_SYNTHETIC_GATE_FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("STRAND_SYNTHETIC_GATE_PASS")
    print("Zero forbidden merges detected; private medical validation remains separate and blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

