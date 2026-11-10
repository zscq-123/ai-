package com.zscq.mall.commerce.order.domain;

import java.time.Instant;
import java.util.UUID;

public record Shipment(
        UUID orderId,
        String orderNo,
        String carrierCode,
        String carrierName,
        String trackingNo,
        String status,
        String latestEvent,
        Instant shippedAt,
        Instant updatedAt) {
    public static Shipment record(
            PurchaseOrder order,
            Shipment existing,
            String carrierCode,
            String carrierName,
            String trackingNo,
            String status,
            String latestEvent) {
        Instant now = Instant.now();
        return new Shipment(
                order.id(),
                order.orderNo(),
                carrierCode,
                carrierName,
                trackingNo,
                status,
                latestEvent,
                existing == null ? now : existing.shippedAt(),
                now);
    }
}
