# Record normalization contract

`scripts/normalize_records.py` turns source assertions into reviewable events
without using clinical similarity as evidence that two records are duplicates.
The input and output are JSON so importers and the future local Android store can
share the same boundary.

Every source requires its SHA-256 digest and at least one location. Byte-identical
source copies share one evidence object, but that object retains every source ID
and location. Every assertion remains present in the normalized output.

Automatic event grouping is limited to either:

* the same explicit, namespaced `event_identity` established by source evidence;
* the same file hash and `source_record_key`; or
* no grouping at all when neither identity is available.

Test name, value, unit, and observation date are payload, never identity. When
assertions for one evidenced event disagree, the event contains every assertion
and an explicit per-field conflict. Consumers must not choose a winner implicitly.

Manual merges require a reviewer and rationale. Each creates an audit entry with
the input events, output event, and an undo snapshot. An undo records its own
reviewer and rationale and restores the exact prior event groups. The snapshot is
part of this initial interchange design; a persistent store should translate it
to an append-only decision and inverse-decision transaction.

Run the controlled non-PHI fixture with:

```sh
python3 scripts/normalize_records.py fixtures/repeat-labs.synthetic.json
python3 -m unittest discover -s tests -p 'test_*.py'
```
