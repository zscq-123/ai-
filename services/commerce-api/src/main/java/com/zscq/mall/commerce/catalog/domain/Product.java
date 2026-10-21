package com.zscq.mall.commerce.catalog.domain;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record Product(UUID id, UUID merchantId, UUID categoryId, String name, String subtitle,
                      String brand, String description, BigDecimal weightKg,
                      ProductStatus status, UUID skuId, String skuCode, String skuTitle,
                      BigDecimal salePrice, BigDecimal marketPrice, int availableStock,
                      long version, Instant createdAt, Instant updatedAt) {
    public static Product draft(UUID merchantId, UUID categoryId, String name, String subtitle,
                                String brand, String description, BigDecimal weightKg,
                                String skuCode, String skuTitle, BigDecimal salePrice,
                                BigDecimal marketPrice, int stock) {
        Instant now = Instant.now();
        return new Product(UUID.randomUUID(), merchantId, categoryId, name, subtitle, brand, description, weightKg, ProductStatus.DRAFT,
                UUID.randomUUID(), skuCode, skuTitle, salePrice, marketPrice, stock, 0L, now, now);
    }

    public Product revise(UUID newCategoryId, String newName, String newSubtitle, String newBrand,
                          String newDescription, BigDecimal newWeightKg, String newSkuCode,
                          String newSkuTitle, BigDecimal newSalePrice, BigDecimal newMarketPrice, int newStock) {
        return new Product(id, merchantId, newCategoryId, newName, newSubtitle, newBrand, newDescription,
                newWeightKg, status, skuId,
                newSkuCode, newSkuTitle, newSalePrice, newMarketPrice, newStock, version, createdAt, Instant.now());
    }
}
