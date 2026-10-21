package com.zscq.mall.commerce.media;

import com.zscq.mall.commerce.media.application.ImageSanitizer;
import com.zscq.mall.commerce.media.domain.ProductImage;
import com.zscq.mall.commerce.media.domain.ProductImageRepository;
import com.zscq.mall.commerce.media.infrastructure.LocalImageStorage;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Public boundary for merchant-owned product media. */
@Service
public class MediaAssets {
    private static final String PUBLIC_PREFIX = "/api/public/media/product-images/";
    private final ProductImageRepository repository;
    private final ImageSanitizer sanitizer;
    private final LocalImageStorage storage;

    public MediaAssets(ProductImageRepository repository, ImageSanitizer sanitizer, LocalImageStorage storage) {
        this.repository = repository;
        this.sanitizer = sanitizer;
        this.storage = storage;
    }

    public void requireActiveMerchant(UUID merchantId) {
        if (!repository.activeMerchantExists(merchantId)) throw new NoSuchElementException("Active merchant not found");
    }

    @Transactional
    public UploadedImage upload(UUID merchantId, byte[] bytes) {
        requireActiveMerchant(merchantId);
        var image = sanitizer.sanitize(bytes);
        UUID id = UUID.randomUUID();
        String key = id + "." + image.extension();
        storage.write(key, image.bytes());
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCompletion(int status) {
                    if (status != STATUS_COMMITTED) storage.remove(key);
                }
            });
        }
        var entity = new ProductImage(id, merchantId, key, image.contentType(), image.width(), image.height(), image.bytes().length);
        try { repository.save(entity); }
        catch (RuntimeException exception) { storage.remove(key); throw exception; }
        return new UploadedImage(id, entity.url(), entity.contentType(), entity.width(), entity.height(), entity.sizeBytes());
    }

    @Transactional(readOnly = true)
    public StoredImage read(UUID id) {
        ProductImage image = repository.find(id).orElseThrow(() -> new NoSuchElementException("Product image not found"));
        Path path = storage.path(image.storageKey());
        if (!Files.isRegularFile(path)) throw new NoSuchElementException("Product image not found");
        return new StoredImage(path, image.contentType(), image.sizeBytes());
    }

    @Transactional(readOnly = true)
    public List<String> validateProductImages(UUID merchantId, List<String> urls, List<String> previous) {
        if (urls == null) return previous;
        if (urls.size() > 9) throw new IllegalArgumentException("每个商品最多上传 9 张图片");
        if (new HashSet<>(urls).size() != urls.size()) throw new IllegalArgumentException("商品图片不能重复");
        for (String url : urls) {
            if (url == null || url.isBlank()) throw new IllegalArgumentException("商品图片地址不能为空");
            if (url.startsWith(PUBLIC_PREFIX)) {
                UUID id;
                try { id = UUID.fromString(url.substring(PUBLIC_PREFIX.length())); }
                catch (IllegalArgumentException exception) { throw new IllegalArgumentException("图片地址无效"); }
                ProductImage image = repository.find(id).orElseThrow(() -> new IllegalArgumentException("请先上传商品图片"));
                if (!image.merchantId().equals(merchantId)) throw new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.FORBIDDEN, "图片不属于当前店铺");
                if (!image.url().equals(url)) throw new IllegalArgumentException("图片地址无效");
            } else if (!previous.contains(url)) {
                throw new IllegalArgumentException("请使用本店上传的商品图片");
            }
        }
        return List.copyOf(urls);
    }

    public record UploadedImage(UUID id, String url, String contentType, int width, int height, long sizeBytes) {}
    public record StoredImage(Path path, String contentType, long sizeBytes) {}
}
