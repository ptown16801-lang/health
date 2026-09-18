# Dependency verification for OneNote validation

Verified on 2026-09-18 using public package metadata, upstream source repositories, and a clean local Python environment. This is a dependency-readiness result, not a validation result for any OneNote fixture.

## Decision

The required workflow can run locally without a paid service, subscription, account, or billable API. The selected baseline is suitable for building the controlled harness:

| Workflow part | Selected dependency | Exact pin | License | Installation | Paid requirement for used feature |
| --- | --- | --- | --- | --- | --- |
| OneNote extraction | [`onenote-tool`](https://github.com/vanarebane/onenote-tool) | PyPI 0.1.5; tag commit `abd2065c28a2dcfd45edcc944d8be078c313dd02` | MIT | Pinned Python lock | None |
| Parser used by converter | [`pyOneNote`](https://github.com/DissectMalware/pyOneNote) | PyPI 0.0.2 | Apache-2.0 | Transitive pinned Python package | None |
| PDF integrity and directly extractable text | [`pypdf`](https://github.com/py-pdf/pypdf) | PyPI 6.19.0 | BSD-3-Clause | Pinned Python lock | None |
| Image verification | [Pillow](https://github.com/python-pillow/Pillow) | PyPI 12.3.0 | MIT-CMU | Converter's pinned transitive set | None |
| Hashing, manifests, command capture, reporting | Python standard library | Python 3.12.11 tested; converter supports 3.10+ | PSF-2.0 | Local Python installation | None |
| Optional OCR comparison | [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | 5.5.1 | Apache-2.0 | Local OS package or upstream release | None |

`requirements.lock` pins the complete Python resolution, including CLI dependencies. `config/dependencies.json` records each resolved package, source, version, and license so the preflight can reject drift.

## Evidence and limitations

- PyPI metadata for `onenote-tool` 0.1.5 declares Python 3.10+, MIT, `pyOneNote==0.0.2`, Pillow 10+, and cryptography 44+. The upstream `0.1.5` tag resolves to the commit recorded above.
- The converter explicitly pins `pyOneNote==0.0.2` because it patches private parser internals. This is reproducible but raises maintenance and silent-breakage risk; never loosen that pin without rerunning controlled fixtures.
- `onenote-tool` labels itself alpha and promises best-effort parsing. A successful install or zero exit status cannot establish extraction completeness. The harness must still inventory hierarchy, native text, images, attachments, tables, warnings, and hashes, and compare them with the supplied source baseline.
- `pypdf` checks whether PDFs can be parsed and extracts an existing text layer without OCR. It cannot prove visual fidelity or that the source contained no omitted object.
- Tesseract is optional and must never replace direct text extraction. OCR output is derived, may be wrong, and must remain separate from originals and structured observations.
- No cloud OCR, hosted converter, Microsoft 365 subscription, Adobe subscription, or paid PDF SDK is required or recommended for the used workflow. Tools with commercial offerings were not excluded when their required local feature was free; none offered a necessary advantage over this pinned baseline.

## Installation and recorded command

Create the environment in access-controlled local/private storage:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.lock
.venv/bin/python scripts/preflight.py
```

The controlled extraction harness should record the exact command it actually invokes. For version 0.1.5, the converter entry point is `onenote-tool`; do not substitute another converter if it fails. Confirm supported options with:

```sh
.venv/bin/onenote-tool --help
```

Install Tesseract 5.5.1 only when an OCR comparison is specifically requested. Verify the local binary with `tesseract --version`; a different installed version is reported by the preflight and must be recorded in evidence or replaced with the pin before comparison.

## Data boundary

Dependency checks use public metadata and synthetic/no fixture inputs only. Real fixture names, medical files, extracted documents, screenshots, OCR text, manifests, and logs must stay in private execution storage and must not be committed, attached to a pull request, pasted into an issue, or uploaded to a public URL. `.gitignore` provides a backstop, not authorization to place sensitive material inside the repository working tree.

## Conclusion

**Dependency readiness: confirmed.** The selected components cover extraction, PDF inspection/direct text, image checks, reporting, and optional OCR with free local execution and no subscription. This does **not** clear the OneNote conversion blocker: no real fixture was handled here, and a controlled fixture run with source-to-output review remains required.
