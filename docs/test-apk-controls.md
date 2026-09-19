# Test APK controls

The home screen has four independent switches. All are **off on a fresh install**;
choices persist in app-private preferences across activity recreation and app
restarts. Upgrading an existing installation without these settings also starts
with every switch off. **Turn all controls off** resets and persists all four
choices in one action.

| Control | When on | When off |
| --- | --- | --- |
| Block screen capture | Android's secure-window flag protects both the home screen and record viewer (screenshots, non-secure display capture, and task previews). | Normal Android capture behavior. |
| Require biometric / device PIN to open records | Every viewer entry requires system authentication before rendering any record or its details. Enrolled biometrics on Android 10+ offer device credentials as a fallback; Android 8–9 use device credentials. Cancellation does not open the record. Without a configured device screen lock, records stay closed. | Records open directly. |
| Show provenance / details | Show source IDs, versions/hashes, page references, and rendering error details. | Hide this optional metadata in the list and viewer; keep titles, availability states, source content, and basic failure messages visible. |
| Enable export / re-import validation | Expose the existing controlled-corpus validation action and results. | Hide the action/results and reject invocation of the action. |

The gate uses Android's enrolled biometrics or device PIN, pattern, or password;
the app never collects or stores credentials. It relocks when an opened viewer
is backgrounded or recreated, and also guards internal direct viewer
launches. The home screen remains accessible so the gate can be turned off.
These are optional test controls, not an access policy for production medical data.

Visibility changes never remove provenance from records or archives. Validation
still uses the complete archive and compares paths, sizes, and SHA-256 digests.
App-private storage, disabled backups, no network permission, preservation of
original bytes, path checks, and fixed integrity protections remain unchanged.
Only packaged synthetic, non-PHI records are used by this APK and its tests.

Build and verify with Java 17 and Android SDK 35:

```sh
./gradlew testDebugUnitTest assembleDebug assembleDebugAndroidTest
./gradlew connectedDebugAndroidTest
```

The debug APK is `app/build/outputs/apk/debug/app-debug.apk`. JVM activity tests
cover defaults, independent changes, persistence/recreation, reset, secure-window
flags, hidden metadata, validation access, unchanged archive bytes, and device
credential success/cancellation/relocking on API 28 and 35. Biometric callback
tests on API 35 cover success, failure, cancellation, stale results, and lockout
fallback using a simulated system prompt. The device acceptance tests explicitly
enable details and validation, then reset settings afterward.
Use an enrolled device to additionally check biometric success, cancellation,
lockout/PIN fallback, and capture behavior on that device.
