#!/usr/bin/env python3
"""Verify pinned, non-PHI dependency state for the local harness."""

from __future__ import annotations

import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    specification = json.loads((ROOT / "config/dependencies.json").read_text())
    failures: list[str] = []

    minimum = tuple(map(int, specification["python"]["minimum"].split(".")))
    actual_python = sys.version_info[:2]
    if actual_python < minimum:
        failures.append(
            f"Python {minimum[0]}.{minimum[1]}+ required; found "
            f"{actual_python[0]}.{actual_python[1]}"
        )
    else:
        print(f"OK Python {sys.version.split()[0]}")

    for package in specification["packages"]:
        try:
            actual = importlib.metadata.version(package["name"])
        except importlib.metadata.PackageNotFoundError:
            failures.append(f"missing Python package: {package['name']}=={package['version']}")
            continue
        if actual != package["version"]:
            failures.append(
                f"wrong version: {package['name']} expected {package['version']}, found {actual}"
            )
        else:
            print(f"OK {package['name']} {actual} ({package['license']})")

    converter = shutil.which("onenote-tool")
    if converter is None:
        failures.append("missing converter command: onenote-tool")
    else:
        result = subprocess.run(
            [converter, "--help"], capture_output=True, text=True, timeout=15, check=False
        )
        if result.returncode != 0:
            failures.append(f"onenote-tool --help exited {result.returncode}")
        else:
            print("OK onenote-tool command starts locally")

    for tool in specification["optional_tools"]:
        executable = shutil.which(tool["command"])
        if executable is None:
            print(f"OPTIONAL MISSING {tool['name']} {tool['version']}")
            continue
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
        match = re.search(r"\d+\.\d+\.\d+", result.stdout + result.stderr)
        actual = match.group(0) if match else "unknown"
        status = "OK" if actual == tool["version"] else "OPTIONAL VERSION MISMATCH"
        print(f"{status} {tool['name']} {actual} (expected {tool['version']})")

    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print("PASS required dependency preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
