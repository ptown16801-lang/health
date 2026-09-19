package com.jefferson.health;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

final class ArchiveRoundTrip {
    static final String SCHEMA = "health.local-archive/v1";
    private static final String MANIFEST = "archive-manifest.json";

    record FileState(long size, String sha256) {}

    private ArchiveRoundTrip() {}

    static Map<String, FileState> snapshot(File root) throws IOException {
        Map<String, FileState> result = new LinkedHashMap<>();
        List<File> files = new ArrayList<>();
        collectFiles(root, files);
        files.sort(Comparator.comparing(file -> relative(root, file)));
        for (File file : files) {
            result.put(relative(root, file), new FileState(file.length(), sha256(file)));
        }
        return result;
    }

    static int validate(File source, File workingDirectory) throws IOException {
        if (!workingDirectory.isDirectory() && !workingDirectory.mkdirs()) {
            throw new IOException("Cannot create round-trip workspace");
        }
        File archive = new File(workingDirectory, "controlled-export.zip");
        File restored = new File(workingDirectory, "controlled-restored");
        deleteTree(archive);
        deleteTree(restored);
        Map<String, FileState> before = snapshot(source);
        exportArchive(source, archive, before);
        importArchive(archive, restored);
        Map<String, FileState> after = snapshot(restored);
        if (!before.equals(after)) throw new IOException("Export/re-import changed corpus bytes");
        return before.size();
    }

    private static void exportArchive(File source, File destination,
                                      Map<String, FileState> files) throws IOException {
        JSONObject metadata = new JSONObject();
        try {
            for (Map.Entry<String, FileState> item : files.entrySet()) {
                metadata.put(item.getKey(), new JSONObject()
                        .put("sha256", item.getValue().sha256())
                        .put("size", item.getValue().size()));
            }
            JSONObject manifest = new JSONObject().put("schema", SCHEMA).put("files", metadata);
            try (ZipOutputStream output = new ZipOutputStream(new FileOutputStream(destination))) {
                writeEntry(output, MANIFEST,
                        (manifest.toString(2) + "\n").getBytes(StandardCharsets.UTF_8));
                for (String relative : files.keySet()) {
                    output.putNextEntry(new ZipEntry("files/" + relative));
                    try (FileInputStream input = new FileInputStream(new File(source, relative))) {
                        copy(input, output);
                    }
                    output.closeEntry();
                }
            }
        } catch (JSONException error) {
            throw new IOException("Cannot create archive manifest", error);
        }
    }

    private static void importArchive(File archive, File destination) throws IOException {
        if (!destination.mkdirs()) throw new IOException("Cannot create restore directory");
        try (ZipFile zip = new ZipFile(archive)) {
            ZipEntry manifestEntry = zip.getEntry(MANIFEST);
            if (manifestEntry == null) throw new IOException("Archive manifest is missing");
            JSONObject manifest;
            try (InputStream input = zip.getInputStream(manifestEntry)) {
                manifest = new JSONObject(new String(readAll(input), StandardCharsets.UTF_8));
            } catch (JSONException error) {
                throw new IOException("Archive manifest is invalid", error);
            }
            if (!SCHEMA.equals(manifest.optString("schema"))) throw new IOException("Archive schema is unsupported");
            JSONObject files = manifest.optJSONObject("files");
            if (files == null) throw new IOException("Archive file index is missing");
            for (Iterator<String> paths = files.keys(); paths.hasNext(); ) {
                String relative = paths.next();
                File target = safeDestination(destination, relative);
                ZipEntry entry = zip.getEntry("files/" + relative);
                if (entry == null || entry.isDirectory()) throw new IOException("Archive file is missing: " + relative);
                target.getParentFile().mkdirs();
                try (InputStream input = zip.getInputStream(entry);
                     FileOutputStream output = new FileOutputStream(target)) {
                    copy(input, output);
                }
                JSONObject expected = files.optJSONObject(relative);
                if (expected == null || expected.optLong("size", -1) != target.length()
                        || !expected.optString("sha256").equals(sha256(target))) {
                    throw new IOException("Archive integrity check failed: " + relative);
                }
            }
        }
    }

    private static File safeDestination(File root, String relative) throws IOException {
        File result = new File(root, relative).getCanonicalFile();
        if (!result.getPath().startsWith(root.getCanonicalPath() + File.separator)) {
            throw new IOException("Archive path is unsafe");
        }
        return result;
    }

    private static void collectFiles(File value, List<File> files) {
        File[] children = value.listFiles();
        if (children == null) return;
        for (File child : children) {
            if (child.isDirectory()) collectFiles(child, files);
            else if (child.isFile()) files.add(child);
        }
    }

    private static String relative(File root, File file) {
        return root.toPath().relativize(file.toPath()).toString().replace(File.separatorChar, '/');
    }

    private static String sha256(File file) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = new FileInputStream(file)) {
                byte[] buffer = new byte[8192];
                for (int read; (read = input.read(buffer)) >= 0; ) digest.update(buffer, 0, read);
            }
            StringBuilder result = new StringBuilder();
            for (byte value : digest.digest()) result.append(String.format("%02x", value));
            return result.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new AssertionError(error);
        }
    }

    private static byte[] readAll(InputStream input) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        copy(input, output);
        return output.toByteArray();
    }

    private static void copy(InputStream input, java.io.OutputStream output) throws IOException {
        byte[] buffer = new byte[8192];
        for (int read; (read = input.read(buffer)) >= 0; ) output.write(buffer, 0, read);
    }

    private static void writeEntry(ZipOutputStream output, String name, byte[] content) throws IOException {
        output.putNextEntry(new ZipEntry(name));
        output.write(content);
        output.closeEntry();
    }

    private static void deleteTree(File value) throws IOException {
        if (!value.exists()) return;
        if (value.isDirectory()) {
            File[] children = value.listFiles();
            if (children != null) for (File child : children) deleteTree(child);
        }
        if (!value.delete()) throw new IOException("Cannot clear round-trip output");
    }
}
