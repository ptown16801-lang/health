#!/usr/bin/env python3
"""Verify a normalized result from the synthetic JON-107 acceptance pilot."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def is_true(value: object) -> bool:
    return value is True


def pair_key(values: list[str]) -> frozenset[str]:
    return frozenset(values)


def verify(spec: dict, result: dict) -> list[str]:
    failures: list[str] = []
    assertions = spec.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        return ["spec assertions must be a non-empty list"]
    if spec.get("classification") != "synthetic_non_phi":
        failures.append("spec is not classified synthetic_non_phi")

    assertion_by_id = {
        item.get("id"): item for item in assertions
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
    }
    expected_ids = set(assertion_by_id)
    if len(assertion_by_id) != len(assertions):
        failures.append("spec assertion IDs must be unique non-empty strings")

    events = result.get("events")
    if not isinstance(events, list) or not events:
        events = []
        failures.append("events must be a non-empty list")

    event_ids: list[str] = []
    observed: list[str] = []
    event_by_assertion: dict[str, str] = {}
    allowed_groups = {
        pair_key(group) for group in spec.get("reviewable_same_event", [])
        if isinstance(group, list) and len(group) > 1
    }
    for event in events:
        if not isinstance(event, dict):
            failures.append("every event must be an object")
            continue
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id.strip():
            failures.append("every event needs a non-empty string ID")
            event_id = "(invalid)"
        else:
            event_ids.append(event_id)

        source_ids = event.get("source_assertion_ids")
        if not isinstance(source_ids, list) or not source_ids or any(
            not isinstance(item, str) or not item for item in source_ids
        ):
            failures.append(f"event {event_id} needs non-empty string source assertion IDs")
            source_ids = []
        observed.extend(source_ids)
        for assertion_id in source_ids:
            event_by_assertion[assertion_id] = event_id

        if len(source_ids) > 1 and pair_key(source_ids) not in allowed_groups:
            failures.append(f"unapproved merge: event {event_id} groups {', '.join(source_ids)}")

        expected_provenance = [
            {
                "assertion_id": assertion_id,
                "source": assertion_by_id[assertion_id]["source"],
                "source_version": assertion_by_id[assertion_id]["source_version"],
            }
            for assertion_id in source_ids if assertion_id in assertion_by_id
        ]
        if event.get("provenance") != expected_provenance:
            failures.append(f"event {event_id} provenance does not exactly match its source assertions")

    if len(event_ids) != len(set(event_ids)):
        failures.append("event IDs must be unique")

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

    for left, right in spec.get("must_remain_separate", []):
        if event_by_assertion.get(left) == event_by_assertion.get(right):
            failures.append(f"false merge: {left} and {right} share event {event_by_assertion.get(left)}")

    undo = result.get("incorrect_merge_undo")
    expected_pair = spec.get("intentional_incorrect_merge_pair")
    if not isinstance(undo, dict) or undo.get("pair") != expected_pair:
        failures.append("undo evidence references the wrong test pair")
    else:
        operations = undo.get("operations")
        if not isinstance(operations, list) or [
            item.get("action") for item in operations if isinstance(item, dict)
        ] != ["merge", "undo"]:
            failures.append("undo evidence must contain ordered merge and undo operations")
        elif any(
            not isinstance(item.get("operation_id"), str) or not item["operation_id"].strip()
            or item.get("source_assertion_ids") != expected_pair
            for item in operations
        ):
            failures.append("undo operations need durable IDs and the exact test pair")
        final_mapping = undo.get("final_event_ids_by_assertion")
        if not isinstance(final_mapping, dict) or any(
            final_mapping.get(assertion_id) != event_by_assertion.get(assertion_id)
            for assertion_id in expected_pair
        ) or len({final_mapping.get(assertion_id) for assertion_id in expected_pair}) != 2:
            failures.append("undo final mapping does not prove the pair was restored separately")

    round_trip = result.get("round_trip")
    if not isinstance(round_trip, dict) or round_trip.get("schema_version") != 1:
        failures.append("round-trip schema version is missing or unsupported")
    elif round_trip.get("reimported_assertions") != assertions:
        failures.append("round-trip assertion content, order, or provenance changed")

    manual = result.get("manual_review")
    if not isinstance(manual, dict):
        manual = {}
    for check in ("timeline_usable", "search_usable", "export_inspected"):
        if not is_true(manual.get(check)):
            failures.append(f"manual review not attested with boolean true: {check}")
    if not is_true(result.get("workspace_is_synthetic_only")):
        failures.append("workspace is not attested with boolean true as synthetic-only")
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
        print("SYNTHETIC_ACCEPTANCE_GATE_FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("SYNTHETIC_ACCEPTANCE_GATE_PASS")
    print("Zero false automatic merges detected; this is synthetic acceptance evidence only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
