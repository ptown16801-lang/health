# OneNote validation evidence

This repository contains non-sensitive tooling and documentation for controlled
OneNote extraction validation. It must not contain real medical records,
clinical content, identifying information, private screenshots, extracted
documents, OCR text, unredacted manifests, or execution logs.

Start with the [review checklist](docs/onenote-validation-review.md). Copy the
[redacted evidence template](templates/onenote-validation-evidence.redacted.md)
only after the corresponding private evidence packet has been reviewed.

The [record normalization contract](docs/record-normalization.md) defines the
conservative, provenance-preserving boundary for future source importers. Its
controlled synthetic repeat-lab fixture covers exact-file duplicates, same-day
repeats, conflicts, misleading lookalikes, and reversible manual merges.

Actual validation must run in access-controlled local or private storage. The
private evidence packet is the source of truth; a committed redacted summary is
only a review record and must not be sufficient to reconstruct source content.
