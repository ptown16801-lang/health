# OneNote extraction reliability: initial research

Research date: 2026-09-23. Scope: public technical sources and current repository
code; no private records or run evidence inspected, and no converter run performed.

## Current evidence and limits

The working-tree validation guide reports a public known-good tooling pass for its
declared semantic scope. This research does not independently verify that run.
Private-record fidelity and Android acceptance remain separate questions. The
current pin is `onenote-tool==0.1.5`, commit
`abd2065c28a2dcfd45edcc944d8be078c313dd02`.

The pinned upstream README describes lossy semantic extraction, recommends comparing
with OneNote-generated MHT, and cautions that protected sections and older notebooks
have limitations. Its capability percentages count supported content types, not
accuracy on a particular notebook. Therefore they cannot establish migration
completeness. [Pinned upstream README](https://raw.githubusercontent.com/vanarebane/onenote-tool/abd2065c28a2dcfd45edcc944d8be078c313dd02/README.md).

Microsoft describes OneNote files as hierarchical sections and pages containing
multiple content classes, including tables and images. This supports testing
relationships as well as extracted text. [MS-ONE specification](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-one/73d22548-a613-4350-8c23-07d15576be50).

## Findings from local code inspection

`scripts/converter_driver.py` retains section group paths, page order, subpage level,
HTML, native text, and recovered asset hashes. Its inventory does not record native
page or object identifiers. Positional paths locate this extraction, but should not
be assumed stable across later exports or reordered pages.

`scripts/validate_onenote.py` detects missing inventories, zero pages, reported failed
elements, protected-section limitations, count mismatches, PDF-check failures, and
selected missing text. However:

- Aggregate counts cannot detect swapped page associations or misplaced table cells.
- A PDF rendered from the converter's own HTML is downstream evidence; agreement
  between those two outputs cannot expose content omitted before rendering.
- `TOOLING_VALIDATION_PASS` is selected when no error finding exists and public-source
  or synthetic-generation metadata is supplied. The status alone does not establish
  that expectations cover every content class; warnings and required review findings
  can coexist with it.
- The OCR comparison normalizes away punctuation. It can assist text matching but
  cannot prove fidelity of signs, decimal separators, or comparison operators.

These are coverage limitations inferred from the code, not observed loss in a real
notebook.

## Proposed next validation matrix

Use an independently authored synthetic OneNote source and a separate expected
manifest. Do not derive the expected manifest from the candidate converter.

| Case | Required evidence |
| --- | --- |
| Multiple sections, duplicate page titles, subpages | Correct parent, order, and subpage depth for every page |
| Tables with repeated labels and blank cells | Exact row/column associations, including empty cells |
| Synthetic numeric strings such as `1.2`, `12`, `-1.2`, `<1.2` | Exact native-text checks; OCR mismatch remains reviewable |
| Images, embedded PDF, and general attachment | Expected asset bytes/hashes and correct owning page |
| Identical asset reused on different pages | Shared byte identity with every occurrence preserved |
| Same-day observations and conflicting assertions | Separate source assertions; no name/date-based merge |
| Deliberately omitted text or moved table cell in derived output | Validator rejects the affected expectation despite unchanged counts |

Microsoft's desktop Application interface documents `GetHierarchy` and
`GetPageContent`, including XML and optional binary content. These are candidates
for an independent reference capture where a compatible OneNote installation is
available. Availability here has not been checked. An application export also needs
source inspection; it is not automatically complete ground truth.
[Microsoft Application interface](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote).

## Provenance and decision rule

Retain original bytes, source hash, converter identity, extraction-local page/block
location, asset occurrence, and derivation type. Capture native identifiers when
available, but establish their scope before using them across exports. File-byte
identity is not clinical-event identity.

Apply the existing [normalization contract](record-normalization.md): group only by
evidenced identity, preserve conflicting assertions, and keep manual merges audited
and reversible. Test this separately from extraction fidelity.

The immediate next experiment is the synthetic relationship-and-table fixture above.
Report each content class as recovered, partial, missing, not present, or not assessed.
A broader pass requires independent expectations and relationship checks, followed
by source comparison for the actual records being migrated.
