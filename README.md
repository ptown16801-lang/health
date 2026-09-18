# OneNote validation evidence and harness

This repository contains non-sensitive tooling and documentation for controlled
OneNote extraction validation. It must not contain real medical records, clinical
content, identifying information, private screenshots, extracted documents, OCR
text, unredacted manifests, or execution logs.

The JON-107 harness pins `onenote-tool`, preserves a private source copy, records
hashes and converter provenance, extracts semantic content and attachments, checks
recovered PDFs without OCR, detects byte-identical outputs, and produces a private
evidence report. The converter remains unverified until the controlled private test
and manual comparison are completed.

Start with the [harness instructions](docs/JON-107-validation.md) and the
[review checklist](docs/onenote-validation-review.md). Copy the
[redacted evidence template](templates/onenote-validation-evidence.redacted.md)
only after the corresponding private evidence packet has been reviewed.
The [synthetic Strand pilot](docs/JON-107-strand-pilot.md) prepares the
zero-false-merge gate without using private records.

The first [Android/local-first source-browser slice](docs/JON-107-android-architecture.md)
builds a debug APK and generates synthetic PDF/image/text sources on-device. Build
and run its JVM tests with `./gradlew testDebugUnitTest assembleDebug` using Java 17
and Android SDK 35. It is an implementation baseline, not a medical-data migration.

Actual validation must run in access-controlled private storage. The
private evidence packet is the source of truth; a committed redacted summary is
only a review record and must not be sufficient to reconstruct source content.
