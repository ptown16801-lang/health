package com.jefferson.health;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.pdf.PdfRenderer;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

public final class SourceViewerActivity extends Activity {
    private PdfRenderer renderer;
    private ParcelFileDescriptor descriptor;
    private ImageView image;
    private TextView pageLabel;
    private int pageIndex;
    private float zoom = 1f;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 24, 24, 24);
        TextView title = new TextView(this);
        title.setText(getIntent().getStringExtra("title"));
        title.setContentDescription("Source title");
        title.setTextSize(22);
        root.addView(title);
        TextView provenance = new TextView(this);
        provenance.setText("View source · " + getIntent().getStringExtra("provenance"));
        provenance.setContentDescription("Source provenance");
        root.addView(provenance);

        File file = new File(getIntent().getStringExtra("path"));
        SourceRecord.Kind kind = SourceRecord.Kind.valueOf(getIntent().getStringExtra("kind"));
        try {
            if (kind == SourceRecord.Kind.PDF) showPdf(root, file);
            else if (kind == SourceRecord.Kind.IMAGE) showImage(root, file);
            else showText(root, file);
        } catch (IOException | RuntimeException error) {
            TextView failure = new TextView(this);
            failure.setText("Corrupt or unreadable source. Original preserved.\n" + error.getClass().getSimpleName());
            root.addView(failure);
        }
        setContentView(root);
    }

    private void showPdf(LinearLayout root, File file) throws IOException {
        descriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
        renderer = new PdfRenderer(descriptor);
        LinearLayout controls = new LinearLayout(this);
        Button previous = button("Previous", ignored -> { if (pageIndex > 0) { pageIndex--; renderPage(); } });
        Button next = button("Next", ignored -> { if (pageIndex + 1 < renderer.getPageCount()) { pageIndex++; renderPage(); } });
        Button zoomOut = button("−", ignored -> { zoom = Math.max(0.5f, zoom - 0.25f); renderPage(); });
        Button zoomIn = button("+", ignored -> { zoom = Math.min(3f, zoom + 0.25f); renderPage(); });
        controls.addView(previous); controls.addView(next); controls.addView(zoomOut); controls.addView(zoomIn);
        root.addView(controls);
        pageLabel = new TextView(this);
        pageLabel.setContentDescription("PDF page status");
        root.addView(pageLabel);
        image = new ImageView(this);
        image.setAdjustViewBounds(true);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(image, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        renderPage();
    }

    private Button button(String label, android.view.View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(listener);
        return button;
    }

    private void renderPage() {
        try (PdfRenderer.Page page = renderer.openPage(pageIndex)) {
            int width = Math.max(1, Math.round(page.getWidth() * zoom));
            int height = Math.max(1, Math.round(page.getHeight() * zoom));
            Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            bitmap.eraseColor(Color.WHITE);
            page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
            image.setImageBitmap(bitmap);
            pageLabel.setText("Page " + (pageIndex + 1) + " of " + renderer.getPageCount()
                    + " · zoom " + Math.round(zoom * 100) + "%");
        }
    }

    private void showImage(LinearLayout root, File file) {
        image = new ImageView(this);
        image.setAdjustViewBounds(true);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        image.setImageBitmap(BitmapFactory.decodeFile(file.getAbsolutePath()));
        root.addView(image, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
    }

    private void showText(LinearLayout root, File file) throws IOException {
        TextView text = new TextView(this);
        try (FileInputStream input = new FileInputStream(file)) {
            byte[] content = new byte[(int) file.length()];
            int read = input.read(content);
            text.setText(new String(content, 0, Math.max(0, read), StandardCharsets.UTF_8));
        }
        text.setTextSize(18);
        root.addView(text);
    }

    @Override
    protected void onDestroy() {
        if (renderer != null) renderer.close();
        if (descriptor != null) {
            try { descriptor.close(); } catch (IOException ignored) { }
        }
        super.onDestroy();
    }
}
