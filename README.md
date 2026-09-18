# Medical record ingestion and validation

This repository contains non-sensitive ingestion tooling and documentation for
controlled source validation. It must not contain real medical records or
clinical content, identifying information, private screenshots, extracted
documents, OCR text, unredacted manifests, or execution logs.

For a Jefferson C-CDA or ZIP export, see the
[Jefferson ingestion guide](docs/jefferson-ingestion.md). The importer is tested
with a synthetic, non-PHI fixture and keeps exact source bytes separate from
normalized document and section records.

For OneNote, start with the
[review checklist](docs/onenote-validation-review.md). Copy the [redacted
evidence template](templates/onenote-validation-evidence.redacted.md) only after
the corresponding private evidence packet has been reviewed.

Actual validation must run in access-controlled local or private storage. The
private evidence packet is the source of truth; a committed redacted summary is
only a review record and must not be sufficient to reconstruct source content.
