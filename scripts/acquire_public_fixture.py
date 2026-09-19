#!/usr/bin/env python3
"""Download the pinned public OneNote fixture used by JON-107 tooling tests."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen


COMMIT = "63e22d08ef249cc73a6d02da7bc199fc3623a607"
PATH = "tika-parsers/tika-parsers-standard/tika-parsers-standard-modules/tika-parser-microsoft-module/src/test/resources/test-documents/testOneNote2016.one"
URL = f"https://raw.githubusercontent.com/apache/tika/{COMMIT}/{PATH}"
SHA256 = "fcfc3c2e65482dc6f70f6a613b058e908f67db2ebb16a343bc2367e02bbb471c"
LICENSE = "Apache-2.0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verified_bytes(data: bytes) -> bytes:
    actual = sha256(data)
    if actual != SHA256:
        raise ValueError(f"fixture SHA-256 mismatch: expected {SHA256}, got {actual}")
    return data


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=Path(".private/fixtures/apache-tika-testOneNote2016.one"),
    )
    args = parser.parse_args()
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with urlopen(URL, timeout=30) as response:  # noqa: S310 - immutable allowlisted URL
        data = verified_bytes(response.read())
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        stream.write(data)
        temporary = Path(stream.name)
    temporary.replace(destination)
    destination.chmod(0o600)
    print(f"Downloaded verified public fixture to {destination}")
    print(f"Source: {URL}")
    print(f"License: {LICENSE}; SHA-256: {SHA256}")
    print("Expected baseline: 1 page; title 'So good'; body 'This is one note 2016.'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
