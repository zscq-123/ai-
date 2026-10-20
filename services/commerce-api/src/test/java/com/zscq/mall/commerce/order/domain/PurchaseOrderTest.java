package com.zscq.mall.commerce.order.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.Test;

class PurchaseOrderTest {
    @Test
    void createsAnImmutablePriceSnapshotAndCalculatesTotal() {
        var line = new OrderLine(UUID.randomUUID(), UUID.randomUUID(), "办公显示器", "27 英寸",
                new BigDecimal("1999.00"), 2);

        var order = PurchaseOrder.create(UUID.randomUUID(), UUID.randomUUID(), "idem-1", List.of(line));

        assertEquals(OrderStatus.PENDING_PAYMENT, order.status());
        assertEquals(new BigDecimal("3998.00"), order.totalAmount());
        assertThrows(UnsupportedOperationException.class, () -> order.lines().add(line));
    }

    @Test
    void paymentTransitionIsIdempotent() {
        var line = new OrderLine(UUID.randomUUID(), UUID.randomUUID(), "键盘", "青轴",
                new BigDecimal("399.00"), 1);
        var pending = PurchaseOrder.create(UUID.randomUUID(), UUID.randomUUID(), "idem-2", List.of(line));

        var paid = pending.paid();

        assertEquals(OrderStatus.PAID, paid.status());
        assertEquals(paid, paid.paid());
    }

    @Test
    void rejectsEmptyOrder() {
        assertThrows(IllegalArgumentException.class,
                () -> PurchaseOrder.create(UUID.randomUUID(), UUID.randomUUID(), "idem-3", List.of()));
    }
}
