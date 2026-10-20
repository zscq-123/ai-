package com.zscq.mall.commerce.catalog.domain;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record Product(UUID id, UUID merchantId, UUID categoryId, String name, String subtitle,
                      ProductStatus status, UUID skuId, String skuCode, String skuTitle,
                      BigDecimal salePrice, BigDecimal marketPrice, int availableStock,
                      Instant createdAt, Instant updatedAt) {
    public static Product draft(UUID merchantId, UUID categoryId, String name, String subtitle,
                                String skuCode, String skuTitle, BigDecimal salePrice,
                                BigDecimal marketPrice, int stock) {
        Instant now = Instant.now();
        return new Product(UUID.randomUUID(), merchantId, categoryId, name, subtitle, ProductStatus.DRAFT,
                UUID.randomUUID(), skuCode, skuTitle, salePrice, marketPrice, stock, now, now);
    }
}
