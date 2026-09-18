# JON-107 Android/local-first architecture

The Android application is the working record and source viewer. Original files are
immutable inputs outside the normalized fact model; every derived fact points to a
source ID, source version, and page/region when known. A failed OCR, normalization,
or duplicate-review step must not prevent opening a supported original.

The first vertical slice in `app/` uses app-private local files and Android framework
APIs only. It generates a non-medical multipage PDF, a chart image, and a text record,
then exposes them through one archive list. `PdfRenderer` opens the seekable local PDF
with page and zoom controls. Images and text render in-app. Corrupt, unsupported, and
remote-only/offline entries have explicit states and retain provenance rather than
falling back to lossy extracted text.

The next layers remain deliberately separate:

- Room-backed source, assertion, event, provenance, conflict, and undo records;
- Storage Access Framework and authenticated Drive ingestion into an app-private,
  versioned cache, with pagination, resumable retries, deletion/change semantics,
  and explicit remote-only state;
- content-aware importers and OCR workers that always preserve originals;
- controlled duplicate review where only allowlisted same-event assertions may be
  linked, never automatically collapsed by date/test name; and
- portable export plus re-import comparison of complete assertion/provenance data.

Host-side OneNote extraction remains reusable preparation tooling. It is not an
Android runtime dependency and its successful synthetic/public tests do not prove the
Android application. Google Drive is an external source/archive/backup destination,
not the local database. No server, account, tenant, Docker, PostgreSQL, or FastAPI
runtime is part of the phone architecture.

## First-slice acceptance

- Reproducible debug APK build with Java 17, compile/target SDK 35, and min SDK 26.
- Archive list includes PDF, image, text, corrupt, unsupported, and offline examples.
- Both synthetic PDF pages remain visually viewable with page/zoom controls.
- Every entry shows source ID/version/page provenance.
- No fixture or output contains medical or identifying data.
