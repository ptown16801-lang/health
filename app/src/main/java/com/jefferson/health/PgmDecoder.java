package com.jefferson.health;

import java.io.EOFException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

final class PgmDecoder {
    record Pixels(int width, int height, int[] argb) {}

    private PgmDecoder() {}

    static Pixels decode(byte[] content) throws IOException {
        Cursor cursor = new Cursor(content);
        String magic = cursor.token("magic number");
        if (!"P2".equals(magic) && !"P5".equals(magic)) {
            throw new IOException("Unsupported PGM encoding");
        }
        int width = positive(cursor.token("width"), "width");
        int height = positive(cursor.token("height"), "height");
        int maximum = positive(cursor.token("maximum value"), "maximum value");
        if (maximum > 65_535) throw new IOException("PGM maximum value is out of range");
        long count = (long) width * height;
        if (count > Integer.MAX_VALUE) throw new IOException("PGM dimensions are too large");

        int[] pixels = new int[(int) count];
        if ("P2".equals(magic)) {
            for (int index = 0; index < pixels.length; index++) {
                pixels[index] = argb(sample(cursor.token("pixel"), maximum));
            }
        } else {
            cursor.consumeRasterSeparator();
            int bytesPerSample = maximum < 256 ? 1 : 2;
            for (int index = 0; index < pixels.length; index++) {
                int value = cursor.unsignedByte();
                if (bytesPerSample == 2) value = (value << 8) | cursor.unsignedByte();
                if (value > maximum) throw new IOException("PGM pixel exceeds maximum value");
                pixels[index] = argb(scale(value, maximum));
            }
        }
        return new Pixels(width, height, pixels);
    }

    private static int positive(String value, String label) throws IOException {
        try {
            int parsed = Integer.parseInt(value);
            if (parsed <= 0) throw new IOException("PGM " + label + " must be positive");
            return parsed;
        } catch (NumberFormatException error) {
            throw new IOException("PGM " + label + " is invalid", error);
        }
    }

    private static int sample(String value, int maximum) throws IOException {
        final int parsed;
        try {
            parsed = Integer.parseInt(value);
        } catch (NumberFormatException error) {
            throw new IOException("PGM pixel is invalid", error);
        }
        if (parsed < 0 || parsed > maximum) throw new IOException("PGM pixel is out of range");
        return scale(parsed, maximum);
    }

    private static int scale(int value, int maximum) {
        return (int) Math.round(value * 255.0 / maximum);
    }

    private static int argb(int gray) {
        return 0xff000000 | (gray << 16) | (gray << 8) | gray;
    }

    private static final class Cursor {
        private final byte[] content;
        private int position;

        Cursor(byte[] content) {
            this.content = content;
        }

        String token(String label) throws IOException {
            skipWhitespaceAndComments();
            int start = position;
            while (position < content.length && !whitespace(content[position])
                    && content[position] != '#') {
                position++;
            }
            if (start == position) throw new EOFException("PGM " + label + " is missing");
            return new String(content, start, position - start, StandardCharsets.US_ASCII);
        }

        void consumeRasterSeparator() throws IOException {
            if (position >= content.length || !whitespace(content[position])) {
                throw new IOException("PGM raster separator is missing");
            }
            byte first = content[position++];
            if (first == '\r' && position < content.length && content[position] == '\n') position++;
        }

        int unsignedByte() throws IOException {
            if (position >= content.length) throw new EOFException("PGM raster is truncated");
            return content[position++] & 0xff;
        }

        private void skipWhitespaceAndComments() {
            while (position < content.length) {
                if (whitespace(content[position])) {
                    position++;
                } else if (content[position] == '#') {
                    while (position < content.length && content[position] != '\n'
                            && content[position] != '\r') position++;
                } else {
                    return;
                }
            }
        }

        private static boolean whitespace(byte value) {
            return value == ' ' || value == '\t' || value == '\n' || value == '\r'
                    || value == '\f';
        }
    }
}
