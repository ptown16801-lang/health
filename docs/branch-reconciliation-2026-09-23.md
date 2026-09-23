# Health branch reconciliation (JON-142)

Current baseline is main at d885c397ccf30d1f67a255891710ea74cf0ffd10.
The conflict audit found old open PRs whose work is already incorporated or
superseded. Do not merge their old snapshots back over current behavior.

| Historical PR | Published head | Current disposition |
| --- | --- | --- |
| #1 dependencies | e95453e450d37eaa79990e64fbcf8c12faf75476 | requirements, preflight and tests match main; main correctly requires Python 3.11+ rather than the older 3.10 claim |
| #2 converter harness | a80225b8767bf896844ed9abbb5d4a808737b1b8 | Harness exists in main with later public/synthetic scope separation, failure exit status, stricter repeat-lab/provenance/round-trip validation and native-text inventory |
| #6 ingestion | 55e287e19d72e17f6da9eac03075a7b657e5105c | All ingestion source, tests, fixtures and ingestion documentation match main byte-for-byte; differences are cumulative README/ignore additions |
| #8 APK controls | 594ba6306ef9ac5d3928aeb0cec7d775cc0daf60 | Every changed path matches main; this head is already an ancestor of main |

This candidate retains the newer main files. It carries forward the existing
local renderer upgrade to WeasyPrint 70.0 consistently in the converter pin,
installer, validator and evidence templates. The original working directory's
edits were copied into this isolated review branch and left intact. The separate
OneNote reliability research remains a proposal, not conversion acceptance.

Validation on Python 3.12.3: all 37 unit tests passed. The controlled synthetic
acceptance runner passed with zero false automatic merges and a byte-preserving
15-file round trip. Installer shell syntax passed. Actual installed WeasyPrint
70.0 rendered a newly authored synthetic table; Poppler extracted the distinct
tokens `-1.2`, `12`, and `<1.2` unchanged. This is renderer smoke coverage, not
source-to-output OneNote fidelity or a new Android instrumentation run.

JON-113 and JON-121 remain completed. JON-122 remains deferred until final
deployment. No private records were accessed, migrated or uploaded. Existing
Android runtime acceptance evidence is preserved; it was not rerun here.
