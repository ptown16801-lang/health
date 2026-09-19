# Downloadable debug APKs

The **Publish debug APK** workflow publishes a GitHub prerelease containing a
debug-signed APK and its `.sha256` checksum. Release assets remain available after
the temporary Actions artifacts expire. The repository's visibility and GitHub
access rules also apply to downloads. APK binaries are never committed.

To publish explicitly:

1. Once the workflow is on the default branch, open **Actions → Publish debug
   APK → Run workflow**, select the desired branch, and run it.
2. Alternatively, push a branch whose tip commit message includes
   `[publish-debug-apk]`. This also works before the workflow is on the default
   branch. Ordinary pushes skip publishing; pull requests do not trigger it.

Only use the marker when you intend to publish that commit. Each successful run
creates a separate prerelease tagged `debug-<run-id>-<attempt>`, pointing to the
exact built commit. Rerunning the workflow creates a new prerelease instead of
overwriting a previous APK. An upload failure can leave an unpublished draft;
rerun the workflow to publish a new release.

The workflow uses Java 17, Python 3.11, Android SDK 35, and the checked-in Gradle
wrapper. Before publishing, it runs the existing JVM tests and Android lint and
builds both the debug APK and the instrumentation APK. Existing Android device
tests remain available via `./gradlew connectedDebugAndroidTest`; this publication
workflow does not run an emulator. Reports are retained as Actions artifacts for
seven days. Only the publishing job receives `contents: write`, using the built-in
`GITHUB_TOKEN`; no additional release secret is needed. Repository/organization
Actions policies must permit that token to create releases and the pinned actions
used by the workflow.

Open the successful run's summary for the exact release and direct download
links, or open the repository's **Releases** page. Download
`jefferson-health-<12-character-commit>-debug.apk` and its `.sha256` sidecar into
the same directory, then verify with:

```sh
sha256sum --check jefferson-health-*-debug.apk.sha256
```

These builds contain packaged synthetic fixtures and are for testing. A fresh
runner may use a different debug signing key from a previously installed APK;
Android may require uninstalling the old test app before installing the new one.
Uninstalling removes that app's local data. A prerelease does not install the APK
on any device or merge its source branch.
