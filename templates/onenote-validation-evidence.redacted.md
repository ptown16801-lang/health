# Redacted OneNote extraction evidence

> This document must contain no PHI, clinical content, identifying information,
> private filenames/paths, screenshots, logs, OCR text, or unredacted manifest
> entries. Exact evidence remains in the access-controlled private packet.

## Review record

| Field | Redacted value |
| --- | --- |
| Private run ID | `<non-identifying ID>` |
| Review scope | `<content classes assessed; no source details>` |
| Input container type | `<.one or .onepkg>` |
| Input identity | `exact filename verified privately` |
| Input size | `verified privately` |
| Input SHA-256 | `<verified privately, or approved exact hash>` |
| Original unchanged | `<yes/no; pre/post SHA-256 compared privately>` |
| Isolated output | `<yes/no; private location verified>` |
| Ground truth available | `<yes/no/partial; describe type only>` |

## Reproducibility

| Field | Redacted value |
| --- | --- |
| Converter package/repository | `<public package or repository identity>` |
| Converter version/commit | `<exact non-sensitive version>` |
| Installation method | `<non-sensitive method and package source>` |
| Converter executable identity | `<verified privately or approved hash>` |
| Command | `<canonical command with private paths/values replaced>` |
| Supporting tools/versions | `<PDF, text, integrity, and optional OCR tools>` |
| Paid subscription required | `no` |

The literal executed command, relevant environment, timestamps, stdout, and
stderr are retained only in the private packet.

## Execution result

| Check | Result |
| --- | --- |
| Exit status | `<numeric status>` |
| Warnings/errors | `<none, or finding IDs>` |
| Silent-failure checks | `<pass/fail/not assessed; finding IDs>` |
| Private logs retained | `<yes/no>` |

## Output inventory

Do not paste filenames or manifest rows. Report aggregate counts only after
confirming they cannot identify a person or reveal clinical content.

| Output class | Count | Integrity result | Notes/finding IDs |
| --- | ---: | --- | --- |
| Hierarchy records | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |
| Native text artifacts | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |
| Images | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |
| PDFs | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |
| Other attachments | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |
| Tables | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |
| Other | `<count>` | `<pass/fail/not assessed>` | `<redacted>` |

| Manifest/integrity check | Result |
| --- | --- |
| Full relative-path/size/SHA-256 manifest retained privately | `<yes/no>` |
| PDF structure checks | `<pass/fail/not present/not assessed>` |
| Direct PDF text checks (without OCR) | `<pass/fail/not present/not assessed>` |
| Image/attachment readability checks | `<pass/fail/not present/not assessed>` |
| Zero-byte/truncated/unparseable output check | `<pass/fail; finding IDs>` |
| Exact duplicate hash review | `<pass/fail; aggregate count or finding IDs>` |

## Source comparison and coverage

Allowed states: `recovered`, `partial`, `missing`, `not present`, `not assessed`.

| Content class | State | Comparison basis | Finding IDs |
| --- | --- | --- | --- |
| Page/section hierarchy | `<state>` | `<source/reference/none>` | `<IDs or none>` |
| Native text | `<state>` | `<source/reference/none>` | `<IDs or none>` |
| Images | `<state>` | `<source/reference/none>` | `<IDs or none>` |
| Embedded PDFs/documents | `<state>` | `<source/reference/none>` | `<IDs or none>` |
| General attachments | `<state>` | `<source/reference/none>` | `<IDs or none>` |
| Tables | `<state>` | `<source/reference/none>` | `<IDs or none>` |
| Distinct same-day/source observations | `<state>` | `<source/reference/none>` | `<IDs or none>` |

Reference screenshots supplied and inspected: `<yes/no>`. Do not answer `yes`
based on a written description alone.

Optional OCR comparison performed: `<yes/no>`. If yes, record only aggregate
agreement/findings here; derived OCR text remains private and does not replace
the original or directly extracted text.

## Findings

Do not include content excerpts, sensitive filenames, paths, or clinical facts.

| ID | Severity | Content class | Redacted finding | Private evidence pointer | Disposition |
| --- | --- | --- | --- | --- | --- |
| `<F-001>` | `<critical/high/medium/low>` | `<class>` | `<non-sensitive statement>` | `<private ID>` | `<open/accepted/resolved>` |

## Decision

Decision: `<PASS / FAIL / BLOCKED>`

Rationale: `<concise non-sensitive rationale tied to checks and finding IDs>`

Limitations / not assessed: `<explicit list; no sensitive detail>`

Required follow-up: `<actions or none>`

Private reviewer approval recorded: `<yes/no>`

Redaction/privacy review completed: `<yes/no>`
