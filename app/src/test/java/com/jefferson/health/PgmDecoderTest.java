package com.jefferson.health;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

public final class PgmDecoderTest {
    @Test
    public void decodesAsciiGraymapUsedByControlledCorpus() throws IOException {
        PgmDecoder.Pixels result = PgmDecoder.decode(
                "P2\n# synthetic\n2 1\n255\n0 255\n".getBytes(StandardCharsets.US_ASCII));

        assertEquals(2, result.width());
        assertEquals(1, result.height());
        assertArrayEquals(new int[]{0xff000000, 0xffffffff}, result.argb());
    }

    @Test
    public void decodesBinaryGraymap() throws IOException {
        byte[] header = "P5\n2 1\n255\n".getBytes(StandardCharsets.US_ASCII);
        byte[] content = new byte[header.length + 2];
        System.arraycopy(header, 0, content, 0, header.length);
        content[header.length] = 0;
        content[header.length + 1] = (byte) 255;

        PgmDecoder.Pixels result = PgmDecoder.decode(content);

        assertArrayEquals(new int[]{0xff000000, 0xffffffff}, result.argb());
    }

    @Test
    public void rejectsTruncatedGraymap() {
        assertThrows(IOException.class, () -> PgmDecoder.decode(
                "P2\n2 1\n255\n0\n".getBytes(StandardCharsets.US_ASCII)));
    }
}
