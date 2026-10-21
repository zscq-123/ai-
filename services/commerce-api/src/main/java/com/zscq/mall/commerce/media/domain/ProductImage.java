package com.zscq.mall.commerce.media.domain;

import java.util.UUID;

public record ProductImage(UUID id, UUID merchantId, String storageKey, String contentType,
                           int width, int height, long sizeBytes) {
    public String url() { return "/api/public/media/product-images/" + id; }
}
