from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from health_ingest.jefferson import ImportValidationError, import_jefferson


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import a Jefferson C-CDA download")
    parser.add_argument("source", type=Path, help="C-CDA XML file or ZIP download")
    parser.add_argument("output", type=Path, help="private local record directory")
    args = parser.parse_args(argv)

    try:
        result = import_jefferson(args.source, args.output)
    except (ImportValidationError, OSError) as error:
        parser.exit(2, f"error: {error}\n")

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0
