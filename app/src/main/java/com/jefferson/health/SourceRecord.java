package com.jefferson.health;

import java.io.File;

public record SourceRecord(
        String id,
        String title,
        Kind kind,
        String sourceVersion,
        Integer page,
        File localFile,
        boolean corrupt,
        boolean remoteOnly) {

    public enum Kind { PDF, IMAGE, TEXT, UNSUPPORTED }
    public enum OpenState { READY, CORRUPT, OFFLINE, UNSUPPORTED }

    public OpenState openState() {
        if (remoteOnly) return OpenState.OFFLINE;
        if (corrupt || localFile == null || !localFile.isFile()) return OpenState.CORRUPT;
        if (kind == Kind.UNSUPPORTED) return OpenState.UNSUPPORTED;
        return OpenState.READY;
    }

    public String provenanceLabel() {
        String pageLabel = page == null ? "all pages" : "page " + page;
        return id + " · " + sourceVersion + " · " + pageLabel;
    }
}
