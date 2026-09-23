# JON-107 controlled OneNote converter validation

## Current status

The public, known-good tooling test has passed for its declared semantic conversion
scope. It does not validate private records or prove Android behavior. Public and
synthetic validation can continue without private file access; private inputs are a
later record-specific gate only when the immediate criterion requires them.

The pinned candidate is:

- package: `onenote-tool==0.1.5`
- parser dependency: `pyOneNote==0.0.2` (the converter itself requires this
  exact private-internals-compatible version)
- semantic PDF renderer: `weasyprint==70.0`
- repository: `https://github.com/vanarebane/onenote-tool.git`
- commit/tag: `abd2065c28a2dcfd45edcc944d8be078c313dd02` / `0.1.5`
- installation: `pip install` from a locally cloned, detached, commit-verified source
  tree with the `cli` extra
- invocation: the pinned environment's Python runs `scripts/converter_driver.py`,
  which calls only `onenote-tool`'s documented parsing/conversion APIs

The upstream project describes itself as alpha and lossy by design. Its reports of
unsupported/failed elements are validation findings, not ignorable noise.
It produces structured objects and semantic HTML, not a pixel-perfect renderer. The
CLI `--dump-dir` output is for inspection and must not be treated as a faithful page
layout export. Validate semantic content and recovered raw assets.

## PHI boundary

All real OneNote/PDF fixtures and everything derived from them are protected health
information. Keep them in local/private storage with access restricted to the owner.
Never place or paste any of the following in Git, commits, pull requests, issues,
public URLs, cloud build logs, screenshots, or generated repository artifacts:

- `.one`, `.onepkg`, PDF/MHT exports, screenshots, or source inventories;
- extracted images, documents, attachments, native text, or OCR text;
- manifests or reports containing sensitive filenames, page/section titles, paths,
  hashes, hierarchy, or content; or
- converter stdout/stderr, warnings, debug output, or run logs.

The repository `.gitignore` protects the conventional locations and sensitive file
extensions. It is defense in depth, not authorization to use Git as storage. Before
any commit, inspect `git status --short` and do not force-add ignored material.

## Private setup

Use an encrypted/private workstation or volume. From the repository root:

```bash
umask 077
mkdir -p .private/fixtures .private/references .private/runs
chmod 700 .private .private/fixtures .private/references .private/runs
./scripts/install_converter.sh
```

The installer places both the source checkout and virtual environment under
`.private/tools/`, verifies the exact commit and installed version, and does not read
fixtures. Python 3.10+ with `venv` support is required. `.onepkg` conversion also
requires local `cabextract` on Linux/macOS; use `onenote-tool doctor` inside the
private environment to confirm it. PDF checks require local `pdfinfo` and
`pdftotext` (Poppler). None of these tools uploads content.

The implemented path uses free, locally runnable dependencies and requires no paid
subscription or billable service. This describes the current harness, not a blanket
restriction on other private no-subscription tooling that may later be appropriate.
The upstream documented CLI checks are available after installation:

```bash
.private/tools/venv/bin/onenote-tool doctor
.private/tools/venv/bin/onenote-tool inspect /private/path/section.one
.private/tools/venv/bin/onenote-tool convert /private/path/notebook.onepkg --dump-dir /private/path/out
```

The harness records `doctor` separately, then uses the same pinned package APIs in a
subprocess because the stock inspection CLI does not write recovered attachment
bytes needed for integrity evidence.

`onenote-tool` does not natively emit PDF. The harness explicitly builds a semantic
inspection HTML document from its parsed sections/pages/blocks, renders that HTML
with pinned WeasyPrint, and verifies the resulting PDF with Poppler. This is a lossy
semantic conversion for content inspection, not a claim of faithful OneNote layout.

Place exactly one smallest representative fixture at a time in
`.private/fixtures/`. Prefer a synthetic fixture first for operational smoke testing,
then a privately reviewed representative fixture covering hierarchy, native text,
images, embedded PDFs/files, and a table. Reference screenshots, when legitimately
available, go in `.private/references/`.

## Run

For a `.onepkg`:

```bash
.private/tools/venv/bin/python scripts/validate_onenote.py \
  .private/fixtures/representative.onepkg \
  --reference .private/references/page-1.png
```

For a single `.one` section, omit `--reference` if no private screenshot exists:

```bash
.private/tools/venv/bin/python scripts/validate_onenote.py \
  .private/fixtures/representative.one
```

For an authorized public/non-medical tooling smoke test, record its immutable source
and license:

```bash
.private/tools/venv/bin/python scripts/validate_onenote.py \
  .private/fixtures/public-test.one \
  --fixture-source-url https://example.invalid/repository/blob/COMMIT/public-test.one \
  --fixture-license Apache-2.0 \
  --expected-count pages=1 \
  --expected-text 'public known-good text'
```

Such a run is labeled `tooling_harness_only`. It cannot verify a private fixture,
private written baseline, or clear the medical-migration converter block.
Repeat `--expected-count` for non-sensitive upstream-declared expectations among
`sections`, `pages`, `images`, `attachments`, and `tables`.
Repeat `--expected-text` for public source-visible strings asserted by the fixture's
upstream tests. A tooling pass requires those strings in both parsed native text and
the Poppler-extracted rendered PDF text, plus a structurally valid PDF.

The pinned Apache Tika fixture can be acquired automatically with hash verification:

```bash
python scripts/acquire_public_fixture.py
```

The command records the immutable upstream commit/path, Apache-2.0 license, expected
SHA-256, and upstream-asserted one-page/two-string baseline. The downloaded file is
written only below the ignored `.private/` tree.

To compare recovered images against written ground truth without representing it as
a screenshot, create a **private, ignored** JSON file and pass `--text-baseline`:

```json
{
  "expected_image_count": 2,
  "expected_rows": [
    {"id": "private-row-a", "tokens": ["private", "expected", "tokens-a"]},
    {"id": "private-row-b", "tokens": ["private", "expected", "tokens-b"]}
  ],
  "must_remain_distinct": [["private-row-a", "private-row-b"]]
}
```

```bash
.private/tools/venv/bin/python scripts/validate_onenote.py \
  .private/fixtures/representative.one \
  --text-baseline .private/references/written-baseline.json
```

That option runs local Tesseract as comparison evidence and keeps its OCR text only
inside the private run. Each `must_remain_distinct` group requires the named rows to
match separate, non-overlapping OCR regions; one region cannot satisfy multiple
same-day observations. OCR mismatch requires manual review; it does not alter the
raw extracted image or prove the source is wrong.

Each invocation creates a unique mode-`0700` directory under `.private/runs/` and
never changes or overwrites the source fixture. It contains the preserved source
copy, converter output, raw logs, direct PDF text, a full hash manifest, and detailed
JSON/Markdown reports. Every item in that directory is sensitive and ignored by Git.
The harness refuses Git-tracked input and refuses an in-repository output location
outside `.private/`. It rejects symlinks, wrong OneNote/CAB signatures, and inputs
over 5 GiB by default; change the size ceiling explicitly only after checking storage.
It also requires a clean worktree unless the development-only override is given.

OCR is deliberately not run by default. `pdftotext` checks directly extractable text
only. If a PDF or screenshot is image-only, perform OCR separately as an optional,
local comparison and retain the original beside it; never treat OCR as the source or
let disagreement overwrite native/structured content.

For the first private fixture test, use the issue's written text as the comparison
baseline. It is not a transferred screenshot, and the report must not describe it as
one. Keep any local transcription/checklist in `.private/references/`, compare both
recovered images and the distinct same-day rows, and publish only redacted
counts/status. If the Drive link returns a login/HTML page instead of the binary,
stop and request private access or local placement; never treat that HTML as a
fixture.

## What to inspect privately

Review `evidence-report.md`, `evidence-report.json`, the converter logs, and actual
extracted files. Record pass/fail and concrete notes for all of these:

- input filename, size, SHA-256, preserved-copy equality, and unchanged source;
- pinned converter identity, installation method, exact command, exit status,
  stdout/stderr, warnings, and full output manifest;
- actual notebook group/section/page hierarchy and native text;
- actual images, general embedded documents/attachments, and tables;
- each recovered PDF's integrity and directly extractable text (without OCR);
- byte-identical outputs and whether each is a duplicate or separate provenance;
- corruption, unsupported elements, warnings, empty/zero-page results, silent
  failures, and source-visible omissions; and
- every supplied screenshot against extracted hierarchy, text, images, attachments,
  and tables. No screenshots means comparison is explicitly not applicable—not pass.

Do not infer completeness from a zero exit status. A human must compare the source
and any references with the outputs. Preserve both conflicting assertions and never
deduplicate medical events from name/date alone.
Any `ElementReport.failed` count, parser failure, or protected-section limitation is
a validation failure/explicit limitation even when the process exits zero.

## Redacted checkpoint workflow

Only a content-free redacted checkpoint may leave private storage. Generate it from
the private JSON report, inspect it manually for disclosure, and copy only the safe
counts/status needed for project tracking:

```bash
.private/tools/venv/bin/python scripts/redact_report.py \
  .private/runs/RUN_ID/evidence-report.json \
  --output /private/outside-repository/JON-107-redacted-checkpoint.md
```

The redactor intentionally excludes input and output filenames, paths, hashes,
titles, extracted text, logs, warnings, and hierarchy. Do not save its output in this
repository. Use [the tracked template](evidence/JON-107-redacted-summary-template.md)
as a reviewer checklist, not as run evidence.

## Go/no-go

This converter test does not itself pass Android acceptance. Report public/synthetic
tooling scope independently from later private-record validation. A missing private
fixture is not a project blocker while an Android or generic harness criterion can be
tested with public/synthetic data. Document limitations without claiming that
unsupported material was recovered.
