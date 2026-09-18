# JON-107 synthetic Strand acceptance pilot

This is non-PHI preparation for the controlled Strand test. It is not evidence that
Strand has been configured, that private records were imported, or that the medical
migration is validated/deployed.

Use [the synthetic repeat-lab specification](../templates/strand-repeat-labs.synthetic.json)
as the smallest duplicate-safety test. All people, identifiers, values, timestamps,
and source records in it are invented. The cases cover:

- an exact cross-source duplicate that may remain separate or be linked with both
  source assertions visible;
- same-day different values and repeat collections that must remain separate;
- the same value with different specimen/panel context;
- the same analyte in different panels; and
- an OCR-versus-structured disagreement that must preserve both assertions.

## Controlled procedure

1. Use a dedicated, empty Strand test workspace. Confirm deletion/export controls
   before adding anything. Do not use real records at this stage.
2. Enter or import every synthetic assertion using a supported Strand workflow.
   Record the exact product/version, import format, configuration, review mode, and
   whether any automatic merge occurs. This repository does not assume an
   undocumented Strand import format.
3. Inspect the timeline/search result and provenance for every assertion. Capture no
   screenshots containing real data; the synthetic test may use a written receipt.
4. Review the exact duplicate. Keeping both is acceptable. Linking them is acceptable
   only if both source assertions remain visible.
5. Intentionally merge the declared conflict pair, undo it, and verify the final
   export keeps them separate.
6. Export the test record, re-import it into another empty test workspace, and map
   each source assertion to the resulting normalized event.
7. Express that mapping in the shape shown by
   `templates/strand-review-result.example.json`, then run:

   ```bash
   python3 scripts/verify_strand_pilot.py \
     templates/strand-repeat-labs.synthetic.json \
     /private/path/strand-review-result.json
   ```

The verifier requires strict booleans and unique event IDs, permits only explicitly
reviewable same-event groups, checks exact source/version provenance, requires
ordered merge/undo operation receipts, and compares full round-trip assertion
content. It does not inspect an application directly or replace human
timeline/search review.

## Go/no-go

The hard gate is zero false automatic merges. Any grouping not explicitly declared
reviewable is a no-go. A missed duplicate is acceptable for this gate if review
remains possible. Do not proceed to private medical imports until the synthetic
Android gate passes. Private OneNote validation is a separate record-specific check;
it does not block generic Android work.

Record unresolved manual items using
[the acquisition queue template](../templates/manual-acquisition-queue.csv), keeping
the populated file in private storage because real filenames/dates can be PHI.
