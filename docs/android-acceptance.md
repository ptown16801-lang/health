# Controlled Android acceptance

Run the integrated candidate against the committed synthetic, non-PHI fixtures:

```sh
python3 -m scripts.run_android_acceptance
./gradlew testDebugUnitTest assembleDebug
```

The Python gate ingests OneNote-derived and Jefferson fixtures, verifies visible
provenance, exercises cross-source search and chronological projection, and
checks duplicate, conflict, and repeat same-day behavior. It then exports the
complete controlled archive, re-imports it, and compares every file by path,
size, and SHA-256 digest.

The gate passes only when every reviewed event group is present and there are
zero false automatic merges. Its JSON output contains counts and statuses only;
temporary candidate data, exports, OCR output, and source contents are removed
when the run finishes. The Android checks compile the source browser/viewers and
exercise their ready, corrupt, unsupported, and offline source states.
