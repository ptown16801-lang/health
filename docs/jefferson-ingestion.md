# Jefferson source ingestion

The supported test path imports C-CDA (`ClinicalDocument`) XML, either as a
standalone file or as one or more `.xml` files in a ZIP download. The checked-in
fixture is synthetic and represents no real person. A source export from the
Jefferson patient portal has not been committed or used to claim compatibility
beyond this standards-based format.

Portal login, MFA, and download acquisition are intentionally out of scope.
Acquire an authorized export separately and run the importer only in approved
private local storage:

```sh
python -m health_ingest /private/download.zip /private/record
```

The output separates three concerns:

- `originals/<sha256>` contains the exact input bytes under a content-derived
  name. ZIP files stay zipped; standalone XML remains byte-for-byte unchanged.
- `manifests/<sha256>.json` records the original name, size and hash, each C-CDA
  member's archive path and hash, import time, and normalized output location.
- `normalized/<sha256>.ndjson` contains a clinical-document record and ordered
  section records. Every record links back to both the original artifact hash
  and the individual XML document hash/path.

Re-importing the same bytes uses the same paths, so it does not create another
source artifact. The importer rejects malformed/non-C-CDA XML, unsafe ZIP member
paths, empty archives, and bounded-size violations before writing output.

This repository must not receive importer output, real exports, manifest data,
or normalized records. Private-source validation should separately confirm the
actual Jefferson download container and C-CDA profile before expanding support.
