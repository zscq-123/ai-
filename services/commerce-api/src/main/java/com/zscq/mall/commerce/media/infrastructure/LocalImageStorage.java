package com.zscq.mall.commerce.media.infrastructure;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class LocalImageStorage {
    private final Path root;

    public LocalImageStorage(@Value("${commerce.media.storage-path:./data/product-images}") String root) {
        this.root = Path.of(root).toAbsolutePath().normalize();
    }

    public void write(String key, byte[] bytes) {
        try {
            Files.createDirectories(root);
            Files.write(path(key), bytes, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        } catch (IOException exception) {
            throw new UncheckedIOException("Unable to save product image", exception);
        }
    }

    public void remove(String key) {
        try { Files.deleteIfExists(path(key)); }
        catch (IOException exception) { throw new UncheckedIOException(exception); }
    }

    public Path path(String key) {
        if (!key.matches("[0-9a-f-]{36}\\.(jpg|png)")) throw new IllegalArgumentException("Invalid image storage key");
        Path file = root.resolve(key).normalize();
        if (!file.startsWith(root)) throw new IllegalArgumentException("Invalid image path");
        return file;
    }
}
