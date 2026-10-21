package com.zscq.mall.commerce.externalcatalog.domain;

import java.math.BigDecimal;

public record ExternalCatalogProduct(
        String sourcePlatform,
        String externalProductId,
        String externalSkuId,
        String sourceUrl,
        String name,
        String subtitle,
        String brand,
        String description,
        String sellerName,
        BigDecimal salePrice,
        BigDecimal marketPrice,
        String currency,
        int availableStock,
        long soldCount,
        BigDecimal rating,
        String imageUrl,
        String sourcePayload) {

    public ExternalCatalogProduct {
        if (sourcePlatform == null || sourcePlatform.isBlank()) throw new IllegalArgumentException("sourcePlatform is required");
        if (externalProductId == null || externalProductId.isBlank()) throw new IllegalArgumentException("externalProductId is required");
        if (sourceUrl == null || sourceUrl.isBlank()) throw new IllegalArgumentException("sourceUrl is required");
        if (name == null || name.isBlank()) throw new IllegalArgumentException("name is required");
        if (salePrice == null || salePrice.signum() < 0) throw new IllegalArgumentException("salePrice must be non-negative");
        if (availableStock < 0) throw new IllegalArgumentException("availableStock must be non-negative");
        if (soldCount < 0) throw new IllegalArgumentException("soldCount must be non-negative");
    }
}
