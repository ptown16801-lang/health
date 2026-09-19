package com.jefferson.health;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

import java.io.File;
import java.io.IOException;
import java.util.EnumMap;
import java.util.List;

public final class MainActivity extends Activity {
    private List<SourceRecord> records;
    private File corpusRoot;
    private TextView roundTripStatus;
    private TestSettings settings;
    private Button roundTrip;
    private ListView list;
    private boolean refreshingControls;
    private final EnumMap<TestSettings.Control, Switch> controls =
            new EnumMap<>(TestSettings.Control.class);

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        settings = new TestSettings(this);
        settings.applyCapturePolicy(getWindow());
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);

        TextView heading = new TextView(this);
        heading.setText("Jefferson local source archive");
        heading.setTextSize(24);
        root.addView(heading);
        TextView scope = new TextView(this);
        scope.setText("Integrated OneNote + Jefferson synthetic non-PHI corpus · works offline");
        root.addView(scope);

        ScrollView settingsScroll = new ScrollView(this);
        LinearLayout settingsPanel = new LinearLayout(this);
        settingsPanel.setOrientation(LinearLayout.VERTICAL);
        for (TestSettings.Control control : TestSettings.Control.values()) {
            Switch toggle = new Switch(this);
            toggle.setText(control.label);
            toggle.setContentDescription(control.label);
            toggle.setMinHeight(Math.round(48 * getResources().getDisplayMetrics().density));
            toggle.setChecked(settings.enabled(control));
            toggle.setOnCheckedChangeListener((button, checked) -> {
                if (!refreshingControls) {
                    settings.set(control, checked);
                    refreshControls();
                }
            });
            controls.put(control, toggle);
            settingsPanel.addView(toggle);
        }
        TextView gateHelp = new TextView(this);
        gateHelp.setText("Unlock uses your device screen lock; biometric options depend on Android "
                + "and enrollment. Without a screen lock, the gate keeps records closed.");
        settingsPanel.addView(gateHelp);
        Button allOff = new Button(this);
        allOff.setText("Turn all controls off");
        allOff.setOnClickListener(ignored -> {
            settings.turnAllOff();
            refreshControls();
        });
        settingsPanel.addView(allOff);

        roundTrip = new Button(this);
        roundTrip.setText("Validate export / re-import");
        roundTrip.setContentDescription("Validate controlled corpus round trip");
        roundTrip.setOnClickListener(ignored -> validateRoundTrip());
        settingsPanel.addView(roundTrip);
        roundTripStatus = new TextView(this);
        roundTripStatus.setContentDescription("Round trip status");
        settingsPanel.addView(roundTripStatus);
        settingsScroll.addView(settingsPanel);
        root.addView(settingsScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        list = new ListView(this);
        root.addView(list, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(root);

        try {
            ControlledCorpus.Loaded corpus = ControlledCorpus.load(this);
            corpusRoot = corpus.root();
            records = corpus.records();
            refreshControls();
            list.setOnItemClickListener((parent, view, position, id) -> open(records.get(position)));
        } catch (IOException error) {
            showState("Archive unavailable", error.getMessage());
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshControls();
    }

    private void refreshControls() {
        settings.applyCapturePolicy(getWindow());
        refreshingControls = true;
        for (TestSettings.Control control : TestSettings.Control.values()) {
            controls.get(control).setChecked(settings.enabled(control));
        }
        refreshingControls = false;
        boolean validation = settings.enabled(TestSettings.Control.ALLOW_VALIDATION);
        roundTrip.setEnabled(validation);
        roundTrip.setVisibility(validation ? View.VISIBLE : View.GONE);
        roundTripStatus.setVisibility(validation ? View.VISIBLE : View.GONE);
        if (!validation) roundTripStatus.setText("");
        if (records != null) {
            boolean details = settings.enabled(TestSettings.Control.SHOW_DETAILS);
            String[] labels = records.stream()
                    .map(record -> record.title() + (details ? "\n" + record.provenanceLabel() : "")
                            + " · " + record.openState().name().toLowerCase(java.util.Locale.ROOT))
                    .toArray(String[]::new);
            list.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, labels));
        }
    }

    private void validateRoundTrip() {
        if (!settings.enabled(TestSettings.Control.ALLOW_VALIDATION)) return;
        if (corpusRoot == null) {
            showState("Round trip unavailable", "The controlled corpus has not loaded.");
            return;
        }
        try {
            int files = ArchiveRoundTrip.validate(corpusRoot, new File(getCacheDir(), "round-trip"));
            roundTripStatus.setText("Round trip passed · " + files + " files restored byte-for-byte");
            showState("Round trip passed", files + " corpus files restored byte-for-byte.");
        } catch (IOException error) {
            roundTripStatus.setText("Round trip failed · " + error.getMessage());
            showState("Round trip failed", error.getMessage());
        }
    }

    private void open(SourceRecord record) {
        Intent intent = new Intent(this, SourceViewerActivity.class);
        intent.putExtra("openState", record.openState().name());
        if (record.localFile() != null) {
            intent.putExtra("path", record.localFile().getAbsolutePath());
        }
        intent.putExtra("kind", record.kind().name());
        intent.putExtra("title", record.title());
        intent.putExtra("provenance", record.provenanceLabel());
        startActivity(intent);
    }

    private void showState(String title, String message) {
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle(title).setMessage(message)
                .setPositiveButton(android.R.string.ok, null).create();
        settings.applyCapturePolicy(dialog.getWindow());
        dialog.show();
    }
}
