package com.jefferson.health;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import android.app.Activity;
import android.app.Instrumentation;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
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
    public void opensOneNotePdfAndProvesPageRendered() {
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        Activity viewer = openRecord(instrumentation, "OneNote", "searchable.pdf");

        assertNoViewerError(viewer);
        TextView provenance = find(
                viewer.getWindow().getDecorView(), TextView.class, "Source provenance");
        assertNotNull(provenance);
        assertTrue(provenance.getText().toString().contains("section-001-page-0001"));
        TextView page = find(viewer.getWindow().getDecorView(), TextView.class, "PDF page status");
        assertNotNull("PDF page status missing", page);
        assertTrue("PDF page was not rendered", page.getText().toString().startsWith("Page 1 of "));
        assertRenderedImage(viewer, "Rendered PDF page");
        close(viewer, instrumentation);
    }

    @Test
    public void opensOneNotePgmAndProvesImageRendered() {
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        Activity viewer = openRecord(instrumentation, "OneNote", "diagram.pgm");

        assertNoViewerError(viewer);
        ImageView image = assertRenderedImage(viewer, "Rendered source image");
        assertTrue("PGM width was not decoded", image.getDrawable().getIntrinsicWidth() == 2);
        assertTrue("PGM height was not decoded", image.getDrawable().getIntrinsicHeight() == 1);
        close(viewer, instrumentation);
    }

    @Test
    public void opensJeffersonEvidenceAndProvesContentRendered() {
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        Activity viewer = openRecord(instrumentation, "Jefferson", "Synthetic C-CDA source");

        assertNoViewerError(viewer);
        TextView text = find(
                viewer.getWindow().getDecorView(), TextView.class, "Rendered source text");
        assertNotNull("Jefferson source content missing", text);
        assertTrue("Jefferson source content was not rendered",
                text.getText().toString().contains("<title>Synthetic Patient Summary</title>"));
        close(viewer, instrumentation);
    }

    private Activity openRecord(Instrumentation instrumentation, String... labelParts) {
        MainActivity current = activity.getActivity();
        AtomicReference<ListView> listReference = new AtomicReference<>();
        AtomicReference<ListAdapter> adapterReference = new AtomicReference<>();
        AtomicReference<Integer> positionReference = new AtomicReference<>();
        instrumentation.runOnMainSync(() -> {
            ListView list = find(current.getWindow().getDecorView(), ListView.class, null);
            assertNotNull(list);
            ListAdapter adapter = list.getAdapter();
            assertNotNull(adapter);
            int match = -1;
            for (int position = 0; position < adapter.getCount(); position++) {
                String label = adapter.getItem(position).toString();
                boolean containsEveryPart = true;
                for (String part : labelParts) containsEveryPart &= label.contains(part);
                if (containsEveryPart) {
                    match = position;
                    break;
                }
            }
            assertTrue("Controlled corpus evidence missing", match >= 0);
            listReference.set(list);
            adapterReference.set(adapter);
            positionReference.set(match);
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
        instrumentation.removeMonitor(monitor);
        return viewer;
    }

    private static ImageView assertRenderedImage(Activity viewer, String description) {
        ImageView image = find(viewer.getWindow().getDecorView(), ImageView.class, description);
        assertNotNull("Rendered image view missing", image);
        assertNotNull("Rendered image drawable missing", image.getDrawable());
        assertTrue("Rendered image has no width", image.getDrawable().getIntrinsicWidth() > 0);
        assertTrue("Rendered image has no height", image.getDrawable().getIntrinsicHeight() > 0);
        return image;
    }

    private static void assertNoViewerError(Activity viewer) {
        assertNull("Viewer displayed an error state", find(
                viewer.getWindow().getDecorView(), TextView.class, "Source viewer error"));
    }

    private static void close(Activity viewer, Instrumentation instrumentation) {
        instrumentation.runOnMainSync(viewer::finish);
        instrumentation.waitForIdleSync();
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
