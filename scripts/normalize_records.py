#!/usr/bin/env python3
"""Normalize imported assertions without guessing that similar records are duplicates."""

from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


class NormalizationError(ValueError):
    """Raised when an input cannot retain unambiguous provenance."""


@dataclass(frozen=True, order=True)
class EventIdentity:
    """A strong, namespaced identity supplied by underlying evidence."""

    kind: str
    namespace: str
    value: str

    @classmethod
    def from_json(cls, raw: dict[str, Any] | None) -> EventIdentity | None:
        if raw is None:
            return None
        values = tuple(str(raw.get(field, "")).strip() for field in ("kind", "namespace", "value"))
        if not all(values):
            raise NormalizationError("event_identity requires non-empty kind, namespace, and value")
        return cls(*values)

    def as_json(self) -> dict[str, str]:
        return {"kind": self.kind, "namespace": self.namespace, "value": self.value}


def _stable_id(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:16]}"


def _require_unique(items: Iterable[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            raise NormalizationError(f"{label} requires a non-empty id")
        if item_id in result:
            raise NormalizationError(f"duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def _normalize_sources(raw_sources: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    sources = _require_unique(raw_sources, "source")
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_to_evidence: dict[str, dict[str, Any]] = {}
    evidence: list[dict[str, Any]] = []

    for source_id, source in sources.items():
        digest = str(source.get("sha256", "")).lower().strip()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise NormalizationError(f"source {source_id} requires a valid lowercase SHA-256 digest")
        locations = source.get("locations")
        if not isinstance(locations, list) or not locations:
            raise NormalizationError(f"source {source_id} requires at least one provenance location")
        by_hash[digest].append(source)

    for digest, copies in sorted(by_hash.items()):
        locations: list[dict[str, Any]] = []
        seen_locations: set[str] = set()
        for copy in copies:
            for location in copy["locations"]:
                if not isinstance(location, dict) or not location:
                    raise NormalizationError(f"source {copy['id']} has an invalid provenance location")
                key = json.dumps(location, sort_keys=True, separators=(",", ":"))
                if key not in seen_locations:
                    locations.append(deepcopy(location))
                    seen_locations.add(key)
        normalized = {
            "id": _stable_id("evidence", digest),
            "sha256": digest,
            "source_ids": sorted(str(copy["id"]) for copy in copies),
            "locations": locations,
        }
        evidence.append(normalized)
        for copy in copies:
            source_to_evidence[str(copy["id"])] = normalized
    return source_to_evidence, evidence


def _assertion_payload(assertion: dict[str, Any]) -> dict[str, Any]:
    ignored = {"id", "source_id", "source_record_key", "event_identity"}
    return {key: deepcopy(value) for key, value in assertion.items() if key not in ignored}


def _group_key(assertion: dict[str, Any], evidence: dict[str, Any]) -> tuple[str, ...]:
    identity = EventIdentity.from_json(assertion.get("event_identity"))
    if identity is not None:
        return ("identity", identity.kind, identity.namespace, identity.value)
    record_key = str(assertion.get("source_record_key", "")).strip()
    if record_key:
        return ("file-record", evidence["sha256"], record_key)
    # Deliberately unique. Clinical similarity is never evidence of event identity.
    return ("assertion", str(assertion["id"]))


def _conflicts(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for assertion in assertions:
        for field, value in assertion["payload"].items():
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
            values[field][encoded].append(assertion["id"])
    conflicts: list[dict[str, Any]] = []
    for field, variants in sorted(values.items()):
        if len(variants) > 1:
            conflicts.append(
                {
                    "field": field,
                    "assertions": [
                        {"value": json.loads(value), "assertion_ids": sorted(ids)}
                        for value, ids in sorted(variants.items())
                    ],
                }
            )
    return conflicts


def normalize(document: dict[str, Any]) -> dict[str, Any]:
    """Return a lossless normalization of sources and their clinical assertions."""

    source_to_evidence, evidence = _normalize_sources(document.get("sources", []))
    raw_assertions = _require_unique(document.get("assertions", []), "assertion")
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)

    for assertion_id, assertion in raw_assertions.items():
        source_id = str(assertion.get("source_id", "")).strip()
        if source_id not in source_to_evidence:
            raise NormalizationError(f"assertion {assertion_id} references unknown source {source_id!r}")
        evidence_item = source_to_evidence[source_id]
        identity = EventIdentity.from_json(assertion.get("event_identity"))
        normalized = {
            "id": assertion_id,
            "source_id": source_id,
            "evidence_id": evidence_item["id"],
            "source_record_key": assertion.get("source_record_key"),
            "event_identity": identity.as_json() if identity else None,
            "payload": _assertion_payload(assertion),
        }
        groups[_group_key(assertion, evidence_item)].append(normalized)

    events: list[dict[str, Any]] = []
    for key, assertions in sorted(groups.items()):
        assertions.sort(key=lambda item: item["id"])
        reason = {
            "identity": "explicit_event_identity",
            "file-record": "exact_file_and_record_key",
            "assertion": "unlinked_assertion",
        }[key[0]]
        event = {
            "id": _stable_id("event", key),
            "automatic_grouping_reason": reason,
            "assertions": assertions,
            "conflicts": _conflicts(assertions),
        }
        events.append(event)

    return {
        "schema_version": 1,
        "evidence": evidence,
        "events": events,
        "manual_decisions": [],
    }


def merge_events(result: dict[str, Any], event_ids: list[str], *, reviewer: str, rationale: str) -> str:
    """Apply an auditable manual merge and return the reversible decision id."""

    requested = sorted(set(event_ids))
    if len(requested) < 2 or not reviewer.strip() or not rationale.strip():
        raise NormalizationError("manual merge requires two events, reviewer, and rationale")
    matching = [event for event in result["events"] if event["id"] in requested]
    if sorted(event["id"] for event in matching) != requested:
        raise NormalizationError("manual merge references an unknown event")
    decision_id = _stable_id("decision", [requested, reviewer, rationale, len(result["manual_decisions"])])
    assertions = sorted(
        [deepcopy(assertion) for event in matching for assertion in event["assertions"]],
        key=lambda item: item["id"],
    )
    merged = {
        "id": _stable_id("event", ["manual", decision_id]),
        "automatic_grouping_reason": "manual_decision",
        "assertions": assertions,
        "conflicts": _conflicts(assertions),
    }
    positions = [result["events"].index(event) for event in matching]
    decision = {
        "id": decision_id,
        "action": "merge",
        "status": "applied",
        "reviewer": reviewer,
        "rationale": rationale,
        "input_event_ids": requested,
        "output_event_id": merged["id"],
        "undo_snapshot": {"position": min(positions), "events": deepcopy(matching)},
    }
    result["events"] = [event for event in result["events"] if event["id"] not in requested]
    result["events"].insert(min(positions), merged)
    result["manual_decisions"].append(decision)
    return decision_id


def undo_merge(result: dict[str, Any], decision_id: str, *, reviewer: str, rationale: str) -> None:
    """Undo an applied manual merge while retaining its complete audit entry."""

    if not reviewer.strip() or not rationale.strip():
        raise NormalizationError("undo requires reviewer and rationale")
    decision = next((item for item in result["manual_decisions"] if item["id"] == decision_id), None)
    if decision is None or decision["status"] != "applied":
        raise NormalizationError("manual merge decision is unknown or no longer applied")
    merged = next((event for event in result["events"] if event["id"] == decision["output_event_id"]), None)
    if merged is None:
        raise NormalizationError("manual merge output has changed and cannot be safely undone")
    result["events"].remove(merged)
    snapshot = decision["undo_snapshot"]
    for offset, event in enumerate(snapshot["events"]):
        result["events"].insert(snapshot["position"] + offset, deepcopy(event))
    decision["status"] = "undone"
    decision["undo"] = {"reviewer": reviewer, "rationale": rationale}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="synthetic or authorized JSON input")
    parser.add_argument("-o", "--output", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args()
    result = normalize(json.loads(args.input.read_text(encoding="utf-8")))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
