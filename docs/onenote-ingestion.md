# OneNote-derived ingestion

`scripts/ingest_onenote.py` turns the private output from
`scripts/converter_driver.py` into a local bundle for the Android record
workflow. The bundle is deliberately file-and-JSON based so the Android layer
can copy it into app-private storage and index `search/*.txt` without depending
on the Python converter at runtime.

```sh
python3 scripts/ingest_onenote.py \
  /private/source/notebook.one \
  /private/run/extracted \
  /private/android-import/notebook
```

The destination must be new. `manifest.json` retains the source container hash,
original name, notebook/section/page identity, source filenames, native-text
identity, and every asset occurrence. Untouched source and recovered embedded bytes live under
content-addressed `originals/` paths. Repeated bytes share storage, but their
separate provenance occurrences are never collapsed.

Native OneNote text and text attachments are indexed directly. PDFs are checked
with `pdftotext`; a PDF with direct text is indexed without OCR. Raster images
and PDFs with no direct text are the only OCR candidates. Without
`--ocr-command`, those occurrences remain explicitly marked as requiring OCR.
An optional local OCR adapter accepts a file path and writes derived text to
standard output:

```sh
python3 scripts/ingest_onenote.py SOURCE EXTRACTED OUTPUT \
  --ocr-command /private/bin/local-ocr
```

OCR output is derived search text and never replaces an original asset. The
synthetic fixture in `fixtures/onenote-derived-synthetic/` contains native text,
an image, a text attachment, a searchable PDF, and an image-only PDF; it contains
no PHI.
