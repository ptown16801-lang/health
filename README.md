# Medical record ingestion and validation

This repository contains non-sensitive ingestion tooling and documentation for
controlled source validation. It must not contain real medical records or clinical
content, identifying information, private screenshots, extracted documents, OCR
text, unredacted manifests, or execution logs.

The JON-107 harness pins `onenote-tool`, preserves a private source copy, records
hashes and converter provenance, extracts semantic content and attachments, checks
recovered PDFs without OCR, detects byte-identical outputs, and produces a private
evidence report. The converter remains unverified until the controlled private test
and manual comparison are completed.

For a Jefferson C-CDA or ZIP export, see the
[Jefferson ingestion guide](docs/jefferson-ingestion.md). The importer is tested
with a synthetic, non-PHI fixture and keeps exact source bytes separate from
normalized document and section records.

For OneNote, start with the [harness instructions](docs/JON-107-validation.md) and
the [review checklist](docs/onenote-validation-review.md). Copy the
[redacted evidence template](templates/onenote-validation-evidence.redacted.md)
only after the corresponding private evidence packet has been reviewed.
The [synthetic Strand pilot](docs/JON-107-strand-pilot.md) prepares the
zero-false-merge gate without using private records.

The first [Android/local-first source-browser slice](docs/JON-107-android-architecture.md)
builds a debug APK and generates synthetic PDF/image/text sources on-device. Build
and run its JVM tests with `./gradlew testDebugUnitTest assembleDebug` using Java 17
and Android SDK 35. It is an implementation baseline, not a medical-data migration.

The [OneNote ingestion workflow](docs/onenote-ingestion.md) packages recovered
native text, images, and original embedded documents for local Android import
while retaining source provenance and limiting OCR to image-based content.

The [record normalization contract](docs/record-normalization.md) defines the
conservative, provenance-preserving boundary for future source importers. Its
controlled synthetic repeat-lab fixture covers exact-file duplicates, same-day
repeats, conflicts, misleading lookalikes, and reversible manual merges.

The [test APK controls](docs/test-apk-controls.md) add optional screen-capture
blocking, record unlock, provenance visibility, and validation access. All four
start off, persist locally, and can be reset together from the home screen.

The [controlled Android acceptance gate](docs/android-acceptance.md) runs the
integrated candidate across both ingestion paths, the zero-false-merge fixture,
cross-source search and timeline projections, and an integrity-checked export
and re-import.

Actual validation must run in access-controlled local or private storage. The
private evidence packet is the source of truth; a committed redacted summary is
only a review record and must not be sufficient to reconstruct source content.
