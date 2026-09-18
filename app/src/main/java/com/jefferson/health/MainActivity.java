package com.jefferson.health;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;

import java.io.File;
import java.io.IOException;
import java.util.List;

public final class MainActivity extends Activity {
    private List<SourceRecord> records;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);

        TextView heading = new TextView(this);
        heading.setText("Jefferson local source archive");
        heading.setTextSize(24);
        root.addView(heading);
        TextView scope = new TextView(this);
        scope.setText("Generated synthetic non-PHI fixtures · works offline");
        root.addView(scope);

        ListView list = new ListView(this);
        root.addView(list, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(root);

        try {
            records = SyntheticArchive.create(new File(getFilesDir(), "synthetic-archive-v1"));
            String[] labels = records.stream()
                    .map(record -> record.title() + "\n" + record.provenanceLabel()
                            + " · " + record.openState().name().toLowerCase())
                    .toArray(String[]::new);
            list.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, labels));
            list.setOnItemClickListener((parent, view, position, id) -> open(records.get(position)));
        } catch (IOException error) {
            showState("Archive unavailable", error.getMessage());
        }
    }

    private void open(SourceRecord record) {
        if (record.openState() != SourceRecord.OpenState.READY) {
            String detail = switch (record.openState()) {
                case CORRUPT -> "The original is corrupt or missing. It was not replaced with extracted text.";
                case OFFLINE -> "This Drive-backed original is remote-only and unavailable while offline.";
                case UNSUPPORTED -> "This source format is unsupported. The original remains preserved.";
                default -> "Source cannot be opened.";
            };
            showState(record.openState().name(), detail + "\n\n" + record.provenanceLabel());
            return;
        }
        Intent intent = new Intent(this, SourceViewerActivity.class);
        intent.putExtra("path", record.localFile().getAbsolutePath());
        intent.putExtra("kind", record.kind().name());
        intent.putExtra("title", record.title());
        intent.putExtra("provenance", record.provenanceLabel());
        startActivity(intent);
    }

    private void showState(String title, String message) {
        new AlertDialog.Builder(this).setTitle(title).setMessage(message)
                .setPositiveButton(android.R.string.ok, null).show();
    }
}
