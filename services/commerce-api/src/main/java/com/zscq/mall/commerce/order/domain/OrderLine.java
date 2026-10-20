package com.zscq.mall.commerce.order.domain;
import java.math.BigDecimal;
import java.util.UUID;
public record OrderLine(UUID id, UUID skuId, String productName, String skuTitle, BigDecimal unitPrice, int quantity) {
    public OrderLine { if (quantity < 1) throw new IllegalArgumentException("Quantity must be positive"); }
    public BigDecimal lineAmount() { return unitPrice.multiply(BigDecimal.valueOf(quantity)); }
}
