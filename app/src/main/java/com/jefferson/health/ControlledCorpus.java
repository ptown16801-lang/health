package com.jefferson.health;

import android.content.Context;
import android.content.res.AssetManager;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

final class ControlledCorpus {
    static final String ASSET_ROOT = "controlled-corpus";

    record Loaded(File root, List<SourceRecord> records) {}

    private ControlledCorpus() {}

    static Loaded load(Context context) throws IOException {
        File root = new File(context.getFilesDir(), "controlled-corpus-v1");
        replaceFromAssets(context.getAssets(), root);
        try {
            File indexFile = new File(root, "android-index.json");
            byte[] content = new byte[(int) indexFile.length()];
            try (InputStream input = new FileInputStream(indexFile)) {
                int offset = 0;
                while (offset < content.length) {
                    int read = input.read(content, offset, content.length - offset);
                    if (read < 0) break;
                    offset += read;
                }
            }
            JSONObject index = new JSONObject(new String(content, StandardCharsets.UTF_8));
            if (!"health.android-controlled/v1".equals(index.getString("schema"))) {
                throw new IOException("Unsupported controlled corpus schema");
            }
            JSONArray items = index.getJSONArray("records");
            List<SourceRecord> records = new ArrayList<>();
            for (int position = 0; position < items.length(); position++) {
                JSONObject item = items.getJSONObject(position);
                records.add(new SourceRecord(
                        item.getString("id"),
                        item.getString("title"),
                        SourceRecord.Kind.valueOf(item.getString("kind")),
                        item.getString("source_version"),
                        item.isNull("page") ? null : item.getInt("page"),
                        resolveInside(root, item.getString("path")),
                        false,
                        false));
            }
            return new Loaded(root, List.copyOf(records));
        } catch (JSONException error) {
            throw new IOException("Controlled corpus index is invalid", error);
        }
    }

    private static File resolveInside(File root, String relative) throws IOException {
        File result = new File(root, relative).getCanonicalFile();
        String prefix = root.getCanonicalPath() + File.separator;
        if (!result.getPath().startsWith(prefix) || !result.isFile()) {
            throw new IOException("Controlled corpus path is invalid: " + relative);
        }
        return result;
    }

    private static void replaceFromAssets(AssetManager assets, File root) throws IOException {
        deleteTree(root);
        if (!root.mkdirs()) throw new IOException("Cannot create controlled corpus directory");
        copyAssetTree(assets, ASSET_ROOT, root);
    }

    private static void copyAssetTree(AssetManager assets, String assetPath, File destination)
            throws IOException {
        String[] children = assets.list(assetPath);
        if (children == null) throw new IOException("Cannot list application assets");
        if (children.length == 0) {
            destination.getParentFile().mkdirs();
            try (InputStream input = assets.open(assetPath);
                 FileOutputStream output = new FileOutputStream(destination)) {
                copy(input, output);
            }
            return;
        }
        if (!destination.isDirectory() && !destination.mkdirs()) {
            throw new IOException("Cannot create corpus directory");
        }
        for (String child : children) {
            copyAssetTree(assets, assetPath + "/" + child, new File(destination, child));
        }
    }

    private static void copy(InputStream input, FileOutputStream output) throws IOException {
        byte[] buffer = new byte[8192];
        for (int read; (read = input.read(buffer)) >= 0; ) output.write(buffer, 0, read);
    }

    private static void deleteTree(File value) throws IOException {
        if (!value.exists()) return;
        File[] children = value.listFiles();
        if (children != null) {
            for (File child : children) deleteTree(child);
        }
        if (!value.delete()) throw new IOException("Cannot replace stale controlled corpus");
    }
}
