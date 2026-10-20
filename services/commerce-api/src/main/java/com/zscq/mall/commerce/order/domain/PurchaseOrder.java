package com.zscq.mall.commerce.order.domain;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record PurchaseOrder(UUID id, String orderNo, UUID customerId, UUID merchantId, OrderStatus status,
                            BigDecimal totalAmount, String idempotencyKey, List<OrderLine> lines,
                            Instant createdAt, Instant paidAt, Instant completedAt) {
    public static PurchaseOrder create(UUID customerId, UUID merchantId, String key, List<OrderLine> lines) {
        if (lines.isEmpty()) throw new IllegalArgumentException("Order requires at least one item");
        BigDecimal total = lines.stream().map(OrderLine::lineAmount).reduce(BigDecimal.ZERO, BigDecimal::add);
        String no = "NO" + Instant.now().toEpochMilli() + UUID.randomUUID().toString().substring(0, 6).toUpperCase();
        return new PurchaseOrder(UUID.randomUUID(), no, customerId, merchantId, OrderStatus.PENDING_PAYMENT, total, key, List.copyOf(lines), Instant.now(), null, null);
    }
    public PurchaseOrder paid() {
        if (status != OrderStatus.PENDING_PAYMENT) return this;
        return new PurchaseOrder(id, orderNo, customerId, merchantId, OrderStatus.PAID, totalAmount, idempotencyKey, lines, createdAt, Instant.now(), null);
    }
}
