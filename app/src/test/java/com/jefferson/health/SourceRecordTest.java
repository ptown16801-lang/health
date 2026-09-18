package com.jefferson.health;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import org.junit.Test;

public final class SourceRecordTest {
    @Test
    public void remoteOnlySourceIsExplicitlyOffline() {
        SourceRecord record = new SourceRecord("S1", "remote", SourceRecord.Kind.PDF,
                "drive:v1", 3, null, false, true);
        assertEquals(SourceRecord.OpenState.OFFLINE, record.openState());
        assertTrue(record.provenanceLabel().contains("page 3"));
    }

    @Test
    public void unsupportedLocalSourceRemainsUnsupported() throws IOException {
        File file = File.createTempFile("synthetic", ".bin");
        try {
            SourceRecord record = new SourceRecord("S2", "binary", SourceRecord.Kind.UNSUPPORTED,
                    "sha256:test", null, file, false, false);
            assertEquals(SourceRecord.OpenState.UNSUPPORTED, record.openState());
        } finally {
            assertTrue(file.delete());
        }
    }

    @Test
    public void corruptFlagWinsForKnownFormat() throws IOException {
        File file = File.createTempFile("synthetic", ".pdf");
        try {
            SourceRecord record = new SourceRecord("S3", "bad", SourceRecord.Kind.PDF,
                    "sha256:test", null, file, true, false);
            assertEquals(SourceRecord.OpenState.CORRUPT, record.openState());
        } finally {
            assertTrue(file.delete());
        }
    }
}
