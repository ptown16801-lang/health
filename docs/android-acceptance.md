# Controlled Android acceptance

Run the integrated candidate against the committed synthetic, non-PHI fixtures:

```sh
python3 -m scripts.run_android_acceptance
./gradlew testDebugUnitTest connectedDebugAndroidTest assembleDebug
```

The Python gate ingests OneNote-derived and Jefferson fixtures, verifies visible
provenance, exercises cross-source search and chronological projection, and
checks duplicate, conflict, and repeat same-day behavior. It then exports the
complete controlled archive, re-imports it, and compares every file by path,
size, and SHA-256 digest.

The Android build generates its packaged `controlled-corpus` assets through the
same OneNote, Jefferson, and normalization functions invoked by the Python gate.
The instrumentation tests browse that packaged corpus, open OneNote PDF and PGM
visual evidence with visible provenance, render the original synthetic Jefferson
C-CDA with its source hash, and invoke the on-device compatible export and
re-import flow before comparing every restored file by path, size, and SHA-256.
They also verify that an undecodable controlled image reports an error while its
original bytes remain unchanged.

The gate passes only when every reviewed event group is present and there are
zero false automatic merges. Its JSON output contains counts and statuses only;
temporary candidate data, exports, OCR output, and source contents are removed
when the run finishes. `connectedDebugAndroidTest` requires a connected Android
device or running emulator; JVM tests and APK assembly do not substitute for it.
