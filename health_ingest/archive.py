"""Portable, integrity-checked export archives for local health data."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


SCHEMA = "health.local-archive/v1"
MANIFEST_PATH = "archive-manifest.json"
MAX_FILES = 10_000
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_BYTES = 500 * 1024 * 1024


class ArchiveValidationError(ValueError):
    """The archive cannot be restored without losing integrity or safety."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def snapshot(root: Path) -> dict[str, dict[str, object]]:
    """Return a content-only snapshot suitable for round-trip comparison."""

    root = Path(root)
    return {
        path.relative_to(root).as_posix(): {
            "sha256": _sha256(path.read_bytes()),
            "size": path.stat().st_size,
        }
        for path in _files(root)
    }


def export_archive(source: Path, destination: Path) -> dict[str, object]:
    """Export every source file to a portable ZIP with an integrity manifest."""

    source = Path(source)
    destination = Path(destination)
    if not source.is_dir():
        raise ArchiveValidationError("export source must be a directory")
    if destination.exists():
        raise FileExistsError(f"export already exists: {destination}")
    files = snapshot(source)
    if len(files) > MAX_FILES:
        raise ArchiveValidationError("export contains too many files")
    if any(item["size"] > MAX_FILE_BYTES for item in files.values()):
        raise ArchiveValidationError("export contains an oversized file")
    if sum(int(item["size"]) for item in files.values()) > MAX_ARCHIVE_BYTES:
        raise ArchiveValidationError("export is too large")
    manifest: dict[str, object] = {"schema": SCHEMA, "files": files}
    rendered = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_PATH, rendered)
            for relative in files:
                archive.write(source / relative, f"files/{relative}")
        os.replace(temporary_path, destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return manifest


def import_archive(source: Path, destination: Path) -> dict[str, object]:
    """Validate and restore an exported archive without partial output."""

    source = Path(source)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"import destination already exists: {destination}")
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as error:
        raise ArchiveValidationError("invalid export archive") from error

    with archive:
        members = archive.infolist()
        if len(members) > MAX_FILES + 1:
            raise ArchiveValidationError("archive contains too many files")
        names = [member.filename for member in members if not member.is_dir()]
        if len(names) != len(set(names)) or MANIFEST_PATH not in names:
            raise ArchiveValidationError("archive manifest is missing or paths are duplicated")
        if any(member.file_size > MAX_FILE_BYTES for member in members):
            raise ArchiveValidationError("archive contains an oversized file")
        if sum(member.file_size for member in members) > MAX_ARCHIVE_BYTES:
            raise ArchiveValidationError("archive is too large")
        try:
            manifest = json.loads(archive.read(MANIFEST_PATH))
        except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ArchiveValidationError("archive manifest is invalid") from error
        if manifest.get("schema") != SCHEMA or not isinstance(manifest.get("files"), dict):
            raise ArchiveValidationError("archive schema is unsupported")
        for relative, expected in manifest["files"].items():
            if not isinstance(relative, str) or not isinstance(expected, dict):
                raise ArchiveValidationError("archive manifest file metadata is invalid")
            if not isinstance(expected.get("size"), int) or not isinstance(
                expected.get("sha256"), str
            ):
                raise ArchiveValidationError("archive manifest file metadata is invalid")
        expected_names = {f"files/{path}" for path in manifest["files"]}
        if set(names) != expected_names | {MANIFEST_PATH}:
            raise ArchiveValidationError("archive contents do not match its manifest")

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
        try:
            for relative, expected in manifest["files"].items():
                safe_path = PurePosixPath(relative)
                if safe_path.is_absolute() or ".." in safe_path.parts or not safe_path.parts:
                    raise ArchiveValidationError("archive contains an unsafe path")
                content = archive.read(f"files/{relative}")
                if len(content) != expected.get("size") or _sha256(content) != expected.get("sha256"):
                    raise ArchiveValidationError(f"archive integrity check failed: {relative}")
                output = temporary.joinpath(*safe_path.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(content)
            temporary.rename(destination)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
    return manifest
