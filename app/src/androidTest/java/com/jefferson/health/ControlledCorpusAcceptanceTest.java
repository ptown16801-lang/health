package com.jefferson.health;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.app.Activity;
import android.app.Instrumentation;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.TextView;

import android.support.test.InstrumentationRegistry;
import android.support.test.rule.ActivityTestRule;
import android.support.test.runner.AndroidJUnit4;

import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.util.concurrent.atomic.AtomicReference;

@RunWith(AndroidJUnit4.class)
public final class ControlledCorpusAcceptanceTest {
    @Rule
    public final ActivityTestRule<MainActivity> activity =
            new ActivityTestRule<>(MainActivity.class);

    @Test
    public void browseIntegratedCorpusAndViewOneNoteEvidence() {
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        MainActivity current = activity.getActivity();
        AtomicReference<ListView> listReference = new AtomicReference<>();
        AtomicReference<ListAdapter> adapterReference = new AtomicReference<>();
        AtomicReference<Integer> positionReference = new AtomicReference<>();
        instrumentation.runOnMainSync(() -> {
            ListView list = find(current.getWindow().getDecorView(), ListView.class, null);
            assertNotNull(list);
            ListAdapter adapter = list.getAdapter();
            assertNotNull(adapter);
            int oneNotePdf = -1;
            boolean hasJefferson = false;
            for (int position = 0; position < adapter.getCount(); position++) {
                String label = adapter.getItem(position).toString();
                if (label.contains("OneNote") && label.contains(".pdf") && oneNotePdf < 0) {
                    oneNotePdf = position;
                }
                if (label.contains("Jefferson")) hasJefferson = true;
            }
            assertTrue("OneNote PDF evidence missing", oneNotePdf >= 0);
            assertTrue("Jefferson evidence missing", hasJefferson);
            listReference.set(list);
            adapterReference.set(adapter);
            positionReference.set(oneNotePdf);
        });

        Instrumentation.ActivityMonitor monitor = instrumentation.addMonitor(
                SourceViewerActivity.class.getName(), null, false);
        instrumentation.runOnMainSync(() -> {
            ListView list = listReference.get();
            ListAdapter adapter = adapterReference.get();
            int position = positionReference.get();
            list.performItemClick(null, position, adapter.getItemId(position));
        });
        Activity viewer = monitor.waitForActivityWithTimeout(5_000);
        assertNotNull("Source viewer did not open", viewer);
        instrumentation.waitForIdleSync();
        TextView provenance = find(
                viewer.getWindow().getDecorView(), TextView.class, "Source provenance");
        assertNotNull(provenance);
        assertTrue(provenance.getText().toString().contains("section-001-page-0001"));
        viewer.finish();
    }

    @Test
    public void exportAndReimportIntegratedCorpusByteForByte() {
        MainActivity current = activity.getActivity();
        InstrumentationRegistry.getInstrumentation().runOnMainSync(() -> {
            Button button = find(
                    current.getWindow().getDecorView(),
                    Button.class,
                    "Validate controlled corpus round trip");
            assertNotNull(button);
            button.performClick();
            TextView result = find(
                    current.getWindow().getDecorView(), TextView.class, "Round trip status");
            assertNotNull(result);
            assertTrue(result.getText().toString().contains("files restored byte-for-byte"));
        });
    }

    private static <T extends View> T find(View root, Class<T> type, String description) {
        if (type.isInstance(root)
                && (description == null || description.equals(root.getContentDescription()))) {
            return type.cast(root);
        }
        if (root instanceof ViewGroup group) {
            for (int position = 0; position < group.getChildCount(); position++) {
                T match = find(group.getChildAt(position), type, description);
                if (match != null) return match;
            }
        }
        return null;
    }
}
