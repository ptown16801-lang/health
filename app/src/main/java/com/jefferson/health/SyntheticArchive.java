package com.jefferson.health;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.pdf.PdfDocument;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

final class SyntheticArchive {
    private SyntheticArchive() {}

    static List<SourceRecord> create(File root) throws IOException {
        if (!root.exists() && !root.mkdirs()) throw new IOException("Cannot create synthetic archive");
        File pdf = new File(root, "synthetic-two-page-visual.pdf");
        File image = new File(root, "synthetic-chart.png");
        File text = new File(root, "synthetic-note.txt");
        File corrupt = new File(root, "synthetic-corrupt.pdf");
        File unsupported = new File(root, "synthetic-waveform.bin");
        writePdf(pdf);
        writeImage(image);
        write(text, "Synthetic non-medical archive note.\nOriginal source remains available.\n");
        write(corrupt, "%PDF-corrupt synthetic fixture\n");
        write(unsupported, "synthetic unsupported bytes\n");
        return List.of(
                new SourceRecord("SRC-PDF-001", "Multipage visual report", SourceRecord.Kind.PDF,
                        "sha256:synthetic-pdf-v1", 1, pdf, false, false),
                new SourceRecord("SRC-IMG-001", "Chart image", SourceRecord.Kind.IMAGE,
                        "sha256:synthetic-image-v1", null, image, false, false),
                new SourceRecord("SRC-TXT-001", "Structured source note", SourceRecord.Kind.TEXT,
                        "sha256:synthetic-text-v1", null, text, false, false),
                new SourceRecord("SRC-BAD-001", "Corrupt PDF", SourceRecord.Kind.PDF,
                        "sha256:synthetic-corrupt-v1", null, corrupt, true, false),
                new SourceRecord("SRC-UNSUPPORTED-001", "Unsupported waveform", SourceRecord.Kind.UNSUPPORTED,
                        "sha256:synthetic-bin-v1", null, unsupported, false, false),
                new SourceRecord("SRC-REMOTE-001", "Remote-only Drive original", SourceRecord.Kind.PDF,
                        "drive-version:synthetic-v1", 2, null, false, true));
    }

    private static void write(File file, String content) throws IOException {
        try (FileOutputStream output = new FileOutputStream(file)) {
            output.write(content.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void writeImage(File file) throws IOException {
        Bitmap bitmap = Bitmap.createBitmap(1000, 700, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        canvas.drawColor(Color.WHITE);
        paint.setColor(Color.rgb(27, 67, 104));
        paint.setTextSize(42);
        canvas.drawText("Synthetic chart — visual evidence", 55, 75, paint);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(6);
        canvas.drawLine(90, 580, 90, 135, paint);
        canvas.drawLine(90, 580, 930, 580, paint);
        paint.setColor(Color.rgb(184, 66, 53));
        canvas.drawLine(100, 500, 300, 360, paint);
        canvas.drawLine(300, 360, 500, 430, paint);
        canvas.drawLine(500, 430, 700, 210, paint);
        canvas.drawLine(700, 210, 900, 285, paint);
        try (FileOutputStream output = new FileOutputStream(file)) {
            if (!bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)) {
                throw new IOException("Could not write synthetic image");
            }
        } finally {
            bitmap.recycle();
        }
    }

    private static void writePdf(File file) throws IOException {
        PdfDocument document = new PdfDocument();
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        try {
            for (int pageNumber = 1; pageNumber <= 2; pageNumber++) {
                PdfDocument.PageInfo info = new PdfDocument.PageInfo.Builder(1200, 1600, pageNumber).create();
                PdfDocument.Page page = document.startPage(info);
                Canvas canvas = page.getCanvas();
                canvas.drawColor(Color.WHITE);
                paint.setColor(Color.BLACK);
                paint.setTextSize(44);
                canvas.drawText("Synthetic multipage report — page " + pageNumber, 70, 90, paint);
                paint.setStyle(Paint.Style.STROKE);
                paint.setStrokeWidth(4);
                if (pageNumber == 1) {
                    for (int row = 0; row <= 5; row++) canvas.drawLine(80, 220 + row * 120, 1120, 220 + row * 120, paint);
                    for (int column = 0; column <= 4; column++) canvas.drawLine(80 + column * 260, 220, 80 + column * 260, 820, paint);
                    paint.setStyle(Paint.Style.FILL);
                    paint.setTextSize(30);
                    canvas.drawText("Table cells remain visual and aligned", 95, 190, paint);
                } else {
                    paint.setColor(Color.rgb(34, 98, 66));
                    float previousX = 80;
                    float previousY = 800;
                    for (int i = 1; i < 18; i++) {
                        float x = 80 + i * 60;
                        float y = 800 + (float) Math.sin(i * 1.3) * 170;
                        canvas.drawLine(previousX, previousY, x, y, paint);
                        previousX = x;
                        previousY = y;
                    }
                    paint.setStyle(Paint.Style.FILL);
                    paint.setTextSize(30);
                    canvas.drawText("Synthetic waveform with preserved trace", 80, 1040, paint);
                }
                document.finishPage(page);
            }
            try (FileOutputStream output = new FileOutputStream(file)) {
                document.writeTo(output);
            }
        } finally {
            document.close();
        }
    }
}
