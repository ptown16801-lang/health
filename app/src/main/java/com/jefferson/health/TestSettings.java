package com.jefferson.health;

import android.content.Context;
import android.content.SharedPreferences;
import android.view.Window;
import android.view.WindowManager;

/** Optional test-APK controls. Fixed archive/privacy protections do not live here. */
final class TestSettings {
    enum Control {
        BLOCK_CAPTURE("Block screen capture"),
        REQUIRE_UNLOCK("Require biometric / device PIN to open records"),
        SHOW_DETAILS("Show provenance / details"),
        ALLOW_VALIDATION("Enable export / re-import validation");

        final String label;

        Control(String label) { this.label = label; }
    }

    private final SharedPreferences preferences;

    TestSettings(Context context) {
        preferences = context.getSharedPreferences("test-security-controls", Context.MODE_PRIVATE);
    }

    boolean enabled(Control control) {
        return preferences.getBoolean(control.name(), false);
    }

    void set(Control control, boolean enabled) {
        preferences.edit().putBoolean(control.name(), enabled).apply();
    }

    void turnAllOff() {
        SharedPreferences.Editor editor = preferences.edit();
        for (Control control : Control.values()) editor.putBoolean(control.name(), false);
        editor.apply();
    }

    void applyCapturePolicy(Window window) {
        if (enabled(Control.BLOCK_CAPTURE)) {
            window.addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
        }
    }
}
