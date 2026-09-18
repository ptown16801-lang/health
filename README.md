# OneNote validation evidence and dependencies

This repository contains non-sensitive tooling and documentation for controlled OneNote extraction validation. It must not contain real medical records, clinical content, identifying information, private screenshots, extracted documents, OCR text, unredacted manifests, or execution logs.

Start with the [review checklist](docs/onenote-validation-review.md). Copy the [redacted evidence template](templates/onenote-validation-evidence.redacted.md) only after the corresponding private evidence packet has been reviewed.

The [dependency decision](docs/dependency-verification.md) records the pinned local baseline: Python 3.12, `onenote-tool[cli]` 0.1.5, `pypdf` 6.19.0, supporting packages, and optional Tesseract 5.5.1. None of the used features requires a paid service, subscription, account, or billable API.

## Install and verify

Use a dedicated virtual environment on a private execution machine:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.lock
.venv/bin/python scripts/preflight.py
```

The preflight reports dependency versions only. It does not inspect fixtures, paths, filenames, or validation output.

Actual validation must run in access-controlled local or private storage. The private evidence packet is the source of truth; a committed redacted summary is only a review record and must not be sufficient to reconstruct source content.
