package com.zscq.mall.commerce.order.domain;
import java.math.BigDecimal;
import java.util.UUID;
public record SkuSnapshot(UUID skuId, UUID merchantId, String productName, String skuTitle, BigDecimal price, int stock) {}
