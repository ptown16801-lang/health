"""Import Jefferson/MyChart C-CDA exports without acquiring portal data."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable
from xml.etree import ElementTree

CCDA_NAMESPACE = "urn:hl7-org:v3"
MAX_ARCHIVE_FILES = 1_000
MAX_ENTRY_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_BYTES = 250 * 1024 * 1024


class ImportValidationError(ValueError):
    """The supplied export is not a supported, safe Jefferson source."""


@dataclass(frozen=True)
class SourceDocument:
    path: str
    content: bytes


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _archive_documents(source: Path, content: bytes) -> tuple[list[SourceDocument], bool]:
    buffered_source = io.BytesIO(content)
    if not zipfile.is_zipfile(buffered_source):
        return [SourceDocument(source.name, content)], False

    documents: list[SourceDocument] = []
    try:
        with zipfile.ZipFile(buffered_source) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            if len(members) > MAX_ARCHIVE_FILES:
                raise ImportValidationError("ZIP contains too many files")
            if sum(member.file_size for member in members) > MAX_ARCHIVE_BYTES:
                raise ImportValidationError("ZIP uncompressed size is too large")
            for member in members:
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ImportValidationError("ZIP contains an unsafe path")
                if member.file_size > MAX_ENTRY_BYTES:
                    raise ImportValidationError(f"ZIP entry is too large: {member.filename}")
                if member_path.suffix.lower() == ".xml":
                    documents.append(SourceDocument(member.filename, archive.read(member)))
    except zipfile.BadZipFile as error:
        raise ImportValidationError("invalid ZIP export") from error

    if not documents:
        raise ImportValidationError("ZIP contains no C-CDA XML documents")
    return documents, True


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None:
        return None
    value = " ".join("".join(element.itertext()).split())
    return value or None


def _attribute(root: ElementTree.Element, path: str, name: str) -> str | None:
    element = root.find(path)
    return element.get(name) if element is not None else None


def _parse_ccda(document: SourceDocument, artifact_sha256: str) -> list[dict[str, object]]:
    try:
        root = ElementTree.fromstring(document.content)
    except ElementTree.ParseError as error:
        raise ImportValidationError(f"invalid XML document: {document.path}") from error

    namespace = f"{{{CCDA_NAMESPACE}}}"
    if root.tag != f"{namespace}ClinicalDocument":
        raise ImportValidationError(f"not a C-CDA ClinicalDocument: {document.path}")

    document_sha256 = _sha256(document.content)
    path_sha256 = _sha256(document.path.encode())
    provenance = {
        "source": "jefferson",
        "format": "ccda",
        "artifact_sha256": artifact_sha256,
        "document_sha256": document_sha256,
        "document_path": document.path,
    }
    identifier_root = _attribute(root, f"{namespace}id", "root")
    identifier_extension = _attribute(root, f"{namespace}id", "extension")
    # Include the container and member path so two byte-identical documents in
    # distinct source positions do not silently collapse into the same record.
    record_id = f"jefferson:ccda:{artifact_sha256}:{document_sha256}:{path_sha256}"
    document_record: dict[str, object] = {
        "id": record_id,
        "kind": "clinical_document",
        "title": _text(root.find(f"{namespace}title")),
        "effective_time": _attribute(root, f"{namespace}effectiveTime", "value"),
        "document_identifier": {
            "root": identifier_root,
            "extension": identifier_extension,
        },
        "provenance": provenance,
    }
    records: list[dict[str, object]] = [document_record]

    section_path = (
        f".//{namespace}component/{namespace}structuredBody/"
        f"{namespace}component/{namespace}section"
    )
    for index, section in enumerate(root.findall(section_path)):
        code = section.find(f"{namespace}code")
        records.append(
            {
                "id": f"{record_id}:section:{index}",
                "kind": "clinical_section",
                "document_id": record_id,
                "position": index,
                "code": code.get("code") if code is not None else None,
                "code_system": code.get("codeSystem") if code is not None else None,
                "title": _text(section.find(f"{namespace}title")),
                "narrative": _text(section.find(f"{namespace}text")),
                "provenance": provenance,
            }
        )
    return records


def _json_lines(records: Iterable[dict[str, object]]) -> bytes:
    return b"".join(
        (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for record in records
    )


def import_jefferson(
    source: Path,
    output: Path,
    *,
    clock: Callable[[], datetime] = _now,
) -> dict[str, object]:
    """Import a standalone C-CDA document or ZIP while retaining source bytes."""
    source = Path(source)
    output = Path(output)
    content = source.read_bytes()
    artifact_sha256 = _sha256(content)
    documents, is_archive = _archive_documents(source, content)

    records: list[dict[str, object]] = []
    for document in documents:
        records.extend(_parse_ccda(document, artifact_sha256))

    artifact_path = output / "originals" / artifact_sha256
    normalized_path = output / "normalized" / f"{artifact_sha256}.ndjson"
    manifest_path = output / "manifests" / f"{artifact_sha256}.json"
    imported_at = clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest: dict[str, object] = {
        "schema_version": 1,
        "source": "jefferson",
        "format": "ccda_zip" if is_archive else "ccda",
        "artifact": {
            "sha256": artifact_sha256,
            "byte_size": len(content),
            "original_name": source.name,
            "stored_path": str(artifact_path.relative_to(output)),
        },
        "imported_at": imported_at,
        "documents": [
            {"path": item.path, "sha256": _sha256(item.content), "byte_size": len(item.content)}
            for item in documents
        ],
        "normalized": {
            "record_count": len(records),
            "stored_path": str(normalized_path.relative_to(output)),
        },
    }

    # Content-addressed paths make re-import idempotent. The original is written
    # independently and never rewritten by normalization.
    if artifact_path.exists() and _sha256(artifact_path.read_bytes()) != artifact_sha256:
        raise ImportValidationError("stored original does not match its content hash")
    if not artifact_path.exists():
        _atomic_write(artifact_path, content)
    _atomic_write(normalized_path, _json_lines(records))
    manifest_content = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    _atomic_write(manifest_path, manifest_content)
    return manifest
