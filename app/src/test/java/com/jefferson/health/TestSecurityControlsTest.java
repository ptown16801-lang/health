package com.jefferson.health;

import static org.junit.Assert.*;
import static org.robolectric.Shadows.shadowOf;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.hardware.biometrics.BiometricManager;
import android.hardware.biometrics.BiometricPrompt;
import android.os.CancellationSignal;
import android.os.Build;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.ListView;
import android.widget.Switch;
import android.widget.TextView;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.shadow.api.Shadow;
import org.robolectric.shadows.ShadowBiometricManager;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.Implementation;
import org.robolectric.annotation.Implements;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Map;
import java.util.concurrent.Executor;

@RunWith(org.robolectric.RobolectricTestRunner.class)
@Config(sdk = {28, 35})
public final class TestSecurityControlsTest {
    private Context context;
    private TestSettings settings;
    private ActivityController<MainActivity> home;
    private ActivityController<SourceViewerActivity> viewer;

    @Before
    public void setUp() {
        context = RuntimeEnvironment.getApplication();
        context.getSharedPreferences("test-security-controls", Context.MODE_PRIVATE).edit().clear().commit();
        settings = new TestSettings(context);
        shadowOf(context.getSystemService(KeyguardManager.class)).setIsDeviceSecure(false);
        if (Build.VERSION.SDK_INT >= 29) {
            Shadow.<ShadowBiometricManager>extract(context.getSystemService(BiometricManager.class)).setCanAuthenticate(false);
        }
    }

    @After
    public void tearDown() {
        if (viewer != null) viewer.pause().stop().destroy();
        if (home != null) home.pause().stop().destroy();
        settings.turnAllOff();
    }

    @Test
    public void freshInstallHasEveryControlOffAndCannotInvokeHiddenValidation() {
        MainActivity activity = launchHome();
        for (TestSettings.Control control : TestSettings.Control.values()) {
            assertFalse(settings.enabled(control));
            assertFalse(toggle(activity, control).isChecked());
        }
        assertFalse(secure(activity));
        Button validation = find(activity, Button.class, "Validate controlled corpus round trip");
        assertEquals(View.GONE, validation.getVisibility());
        assertFalse(validation.isEnabled());
        // Even a programmatic click must not bypass the access control.
        validation.performClick();
        assertFalse(new File(activity.getCacheDir(), "round-trip/controlled-export.zip").exists());
        assertEquals("", find(activity, TextView.class, "Round trip status").getText().toString());
        assertFalse(firstLabel(activity).contains("sha256:"));
    }

    @Test
    public void individualControlsPersistAcrossHomeRecreationAndMasterReset() {
        MainActivity activity = launchHome();
        for (TestSettings.Control control : TestSettings.Control.values()) {
            toggle(activity, control).setChecked(true);
            assertTrue(new TestSettings(context).enabled(control));
            for (TestSettings.Control other : TestSettings.Control.values()) {
                if (other != control) assertFalse(settings.enabled(other));
            }
            home.recreate();
            activity = home.get();
            assertTrue(toggle(activity, control).isChecked());
            toggle(activity, control).setChecked(false);
        }
        for (TestSettings.Control control : TestSettings.Control.values()) {
            toggle(activity, control).setChecked(true);
        }
        assertTrue(secure(activity));
        assertTrue(firstLabel(activity).contains("sha256:"));
        assertEquals(View.VISIBLE, find(activity, Button.class,
                "Validate controlled corpus round trip").getVisibility());
        findButton(activity, "Turn all controls off").performClick();
        home.recreate();
        for (TestSettings.Control control : TestSettings.Control.values()) {
            assertFalse(new TestSettings(context).enabled(control));
            assertFalse(toggle(home.get(), control).isChecked());
        }
        assertFalse(secure(home.get()));
        assertFalse(firstLabel(home.get()).contains("sha256:"));
    }

    @Test
    public void captureAndDetailsApplyToViewerAndResetWithoutAlteringSource() throws Exception {
        File source = syntheticText();
        byte[] original = Files.readAllBytes(source.toPath());
        settings.set(TestSettings.Control.BLOCK_CAPTURE, true);
        settings.set(TestSettings.Control.SHOW_DETAILS, true);
        SourceViewerActivity activity = launchViewer(source);
        assertTrue(secure(activity));
        assertNotNull(find(activity, TextView.class, "Source provenance"));
        assertNotNull(find(activity, TextView.class, "Rendered source text"));
        viewer.pause().stop();
        settings.turnAllOff();
        viewer.restart().start().resume().visible();
        assertFalse(secure(activity));
        assertNull(find(activity, TextView.class, "Source provenance"));
        assertNotNull(find(activity, TextView.class, "Rendered source text"));
        assertArrayEquals(original, Files.readAllBytes(source.toPath()));
    }

    @Test
    public void directViewerLaunchStaysLockedWithoutDeviceCredentialsAndAfterRecreation() throws Exception {
        settings.set(TestSettings.Control.REQUIRE_UNLOCK, true);
        SourceViewerActivity activity = launchViewer(syntheticText());
        assertLocked(activity);
        viewer.recreate();
        assertLocked(viewer.get());
        findButton(viewer.get(), "Unlock record").performClick();
        assertLocked(viewer.get());
    }

    @Test
    public void deviceCredentialSuccessOpensRecordAndBackgroundingRequiresNewUnlock() throws Exception {
        settings.set(TestSettings.Control.REQUIRE_UNLOCK, true);
        shadowOf(context.getSystemService(KeyguardManager.class)).setIsDeviceSecure(true);
        SourceViewerActivity activity = launchViewer(syntheticText());
        assertLocked(activity);
        var request = shadowOf(activity).getNextStartedActivityForResult();
        assertNotNull("Must request system credentials", request);
        assertEquals("android.app.action.CONFIRM_DEVICE_CREDENTIAL", request.intent.getAction());
        viewer.pause().stop(); // The system credential activity covers the viewer.
        activity.onActivityResult(request.requestCode, Activity.RESULT_OK, null);
        viewer.restart().start().resume().visible();
        assertNotNull(find(activity, TextView.class, "Rendered source text"));
        viewer.pause().stop();
        assertLocked(activity);
        viewer.restart().start().resume().visible();
        assertLocked(activity);
        assertNotNull(shadowOf(activity).getNextStartedActivityForResult());
    }

    @Test
    public void canceledOrUnsolicitedCredentialResultNeverRevealsRecord() throws Exception {
        settings.set(TestSettings.Control.REQUIRE_UNLOCK, true);
        SourceViewerActivity activity = launchViewer(syntheticText());
        activity.onActivityResult(1, Activity.RESULT_OK, null);
        assertLocked(activity);
        shadowOf(context.getSystemService(KeyguardManager.class)).setIsDeviceSecure(true);
        findButton(activity, "Unlock record").performClick();
        var request = shadowOf(activity).getNextStartedActivityForResult();
        assertNotNull(request);
        activity.onActivityResult(request.requestCode, Activity.RESULT_CANCELED, null);
        assertTrue(activity.isFinishing());
        assertLocked(activity);
    }

    @Test
    public void credentialRequestSurvivesRecreationButUnlockGrantDoesNot() throws Exception {
        settings.set(TestSettings.Control.REQUIRE_UNLOCK, true);
        shadowOf(context.getSystemService(KeyguardManager.class)).setIsDeviceSecure(true);
        SourceViewerActivity activity = launchViewer(syntheticText());
        var request = shadowOf(activity).getNextStartedActivityForResult();
        assertNotNull(request);
        viewer.recreate();
        activity = viewer.get();
        assertLocked(activity);
        assertNull("Do not duplicate a pending system prompt",
                shadowOf(activity).getNextStartedActivityForResult());
        activity.onActivityResult(request.requestCode, Activity.RESULT_OK, null);
        viewer.pause().resume().visible();
        assertNotNull(find(activity, TextView.class, "Rendered source text"));
        viewer.recreate();
        assertLocked(viewer.get());
    }

    @Test
    public void enabledValidationStillChecksCompleteArchiveAndResetRevokesAccess() throws Exception {
        MainActivity activity = launchHome();
        File root = ControlledCorpus.load(activity).root();
        Map<String, ArchiveRoundTrip.FileState> before = ArchiveRoundTrip.snapshot(root);
        toggle(activity, TestSettings.Control.ALLOW_VALIDATION).setChecked(true);
        find(activity, Button.class, "Validate controlled corpus round trip").performClick();
        TextView status = find(activity, TextView.class, "Round trip status");
        assertTrue(status.getText().toString().contains("files restored byte-for-byte"));
        assertEquals(before, ArchiveRoundTrip.snapshot(root));
        assertEquals(before, ArchiveRoundTrip.snapshot(
                new File(activity.getCacheDir(), "round-trip/controlled-restored")));
        findButton(activity, "Turn all controls off").performClick();
        assertEquals("", status.getText().toString());
        assertEquals(View.GONE, status.getVisibility());
        find(activity, Button.class, "Validate controlled corpus round trip").performClick();
        assertEquals("", status.getText().toString());
    }

    @Test
    @Config(sdk = 35, shadows = PromptShadow.class)
    public void biometricFailureStaysLockedAndSuccessRendersOnlyUntilBackgrounded() throws Exception {
        settings.set(TestSettings.Control.REQUIRE_UNLOCK, true);
        shadowOf(context.getSystemService(KeyguardManager.class)).setIsDeviceSecure(true);
        Shadow.<ShadowBiometricManager>extract(context.getSystemService(BiometricManager.class)).setCanAuthenticate(true);
        SourceViewerActivity activity = launchViewer(syntheticText());
        assertLocked(activity);
        assertNotNull(PromptShadow.callback);
        PromptShadow.callback.onAuthenticationFailed();
        assertLocked(activity);
        PromptShadow.callback.onAuthenticationSucceeded(null);
        assertNotNull(find(activity, TextView.class, "Rendered source text"));
        viewer.pause().stop();
        assertLocked(activity);
        viewer.restart().start().resume().visible();
        assertLocked(activity);
    }

    @Test
    @Config(sdk = 35, shadows = PromptShadow.class)
    public void biometricCancellationAndStaleSuccessCannotUnlockButLockoutOffersPin() throws Exception {
        settings.set(TestSettings.Control.REQUIRE_UNLOCK, true);
        shadowOf(context.getSystemService(KeyguardManager.class)).setIsDeviceSecure(true);
        Shadow.<ShadowBiometricManager>extract(context.getSystemService(BiometricManager.class)).setCanAuthenticate(true);
        SourceViewerActivity activity = launchViewer(syntheticText());
        BiometricPrompt.AuthenticationCallback canceled = PromptShadow.callback;
        canceled.onAuthenticationError(BiometricPrompt.BIOMETRIC_ERROR_USER_CANCELED, "Canceled");
        assertLocked(activity);
        assertNull(shadowOf(activity).getNextStartedActivityForResult());
        canceled.onAuthenticationSucceeded(null);
        assertLocked(activity);
        findButton(activity, "Unlock record").performClick();
        BiometricPrompt.AuthenticationCallback backgrounded = PromptShadow.callback;
        CancellationSignal cancellation = PromptShadow.cancellation;
        viewer.pause().stop();
        assertTrue(cancellation.isCanceled());
        backgrounded.onAuthenticationSucceeded(null);
        assertLocked(activity);
        viewer.restart().start().resume().visible();
        PromptShadow.callback.onAuthenticationError(BiometricPrompt.BIOMETRIC_ERROR_LOCKOUT, "Locked out");
        assertLocked(activity);
        assertNotNull("Lockout must offer device credentials",
                shadowOf(activity).getNextStartedActivityForResult());
    }

    /** Replace only the OS authentication dialog; exercise the real activity callbacks. */
    @Implements(value = BiometricPrompt.class, minSdk = 29)
    public static class PromptShadow {
        static BiometricPrompt.AuthenticationCallback callback;
        static CancellationSignal cancellation;

        @Implementation
        protected void authenticate(CancellationSignal signal, Executor executor,
                                    BiometricPrompt.AuthenticationCallback result) {
            cancellation = signal;
            callback = result;
        }
    }

    private MainActivity launchHome() {
        home = Robolectric.buildActivity(MainActivity.class).setup();
        return home.get();
    }

    private File syntheticText() throws Exception {
        File file = new File(context.getCacheDir(), "security-controls.synthetic.txt");
        Files.write(file.toPath(), "Synthetic record content".getBytes(StandardCharsets.UTF_8));
        return file;
    }

    private SourceViewerActivity launchViewer(File file) {
        Intent intent = new Intent(context, SourceViewerActivity.class)
                .putExtra("path", file.getAbsolutePath())
                .putExtra("kind", "TEXT")
                .putExtra("title", "Synthetic record")
                .putExtra("provenance", "synthetic · sha256:test · page 1");
        viewer = Robolectric.buildActivity(SourceViewerActivity.class, intent).setup();
        return viewer.get();
    }

    private static void assertLocked(Activity activity) {
        assertNotNull(find(activity, TextView.class, "Record locked"));
        assertNull(find(activity, TextView.class, "Rendered source text"));
        assertNull(find(activity, TextView.class, "Source provenance"));
        assertNull(find(activity, TextView.class, "Source title"));
    }

    private static boolean secure(Activity activity) {
        return (activity.getWindow().getAttributes().flags & WindowManager.LayoutParams.FLAG_SECURE) != 0;
    }

    private static Switch toggle(Activity activity, TestSettings.Control control) {
        return find(activity, Switch.class, control.label);
    }

    private static String firstLabel(Activity activity) {
        return find(activity, ListView.class, null).getAdapter().getItem(0).toString();
    }

    private static Button findButton(Activity activity, String label) {
        Button button = findByText(activity.getWindow().getDecorView(), label);
        assertNotNull("Missing button: " + label, button);
        return button;
    }

    private static Button findByText(View root, String label) {
        if (root instanceof Button button && label.contentEquals(button.getText())) return button;
        if (root instanceof ViewGroup group) {
            for (int i = 0; i < group.getChildCount(); i++) {
                Button result = findByText(group.getChildAt(i), label);
                if (result != null) return result;
            }
        }
        return null;
    }

    private static <T extends View> T find(Activity activity, Class<T> type, String description) {
        return find(activity.getWindow().getDecorView(), type, description);
    }

    private static <T extends View> T find(View root, Class<T> type, String description) {
        if (type.isInstance(root)
                && (description == null || description.equals(root.getContentDescription()))) {
            return type.cast(root);
        }
        if (root instanceof ViewGroup group) {
            for (int i = 0; i < group.getChildCount(); i++) {
                T result = find(group.getChildAt(i), type, description);
                if (result != null) return result;
            }
        }
        return null;
    }
}
