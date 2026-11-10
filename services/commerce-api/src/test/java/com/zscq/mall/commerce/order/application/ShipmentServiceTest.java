package com.zscq.mall.commerce.order.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.order.domain.OrderLine;
import com.zscq.mall.commerce.order.domain.OrderRepository;
import com.zscq.mall.commerce.order.domain.OrderStatus;
import com.zscq.mall.commerce.order.domain.PurchaseOrder;
import com.zscq.mall.commerce.order.domain.Shipment;
import com.zscq.mall.commerce.order.domain.ShipmentRepository;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

class ShipmentServiceTest {
    @Test
    void merchantRecordsRealShipmentAndOrderBecomesShipped() {
        UUID merchantId = UUID.randomUUID();
        InMemoryOrders orders = new InMemoryOrders();
        PurchaseOrder order = paidOrder(merchantId);
        orders.save(order);
        InMemoryShipments shipments = new InMemoryShipments();
        ShipmentService service = new ShipmentService(orders, shipments);

        Shipment shipment = service.record(
                merchantId, order.orderNo(), "SF", "顺丰速运", "SF123", "IN_TRANSIT", "已揽收");

        assertThat(shipment.trackingNo()).isEqualTo("SF123");
        assertThat(orders.findByOrderNo(order.orderNo()).orElseThrow().status()).isEqualTo(OrderStatus.SHIPPED);
        assertThat(shipments.findByOrderId(order.id())).contains(shipment);
    }

    @Test
    void differentMerchantCannotWriteShipment() {
        InMemoryOrders orders = new InMemoryOrders();
        PurchaseOrder order = paidOrder(UUID.randomUUID());
        orders.save(order);
        ShipmentService service = new ShipmentService(orders, new InMemoryShipments());

        assertThatThrownBy(() -> service.record(
                UUID.randomUUID(), order.orderNo(), "SF", "顺丰速运", "SF123", "IN_TRANSIT", null))
                .isInstanceOf(ResponseStatusException.class);
    }

    private static PurchaseOrder paidOrder(UUID merchantId) {
        return PurchaseOrder.create(
                UUID.randomUUID(),
                merchantId,
                "key-1",
                List.of(new OrderLine(
                        UUID.randomUUID(), UUID.randomUUID(), "商品", "规格", new BigDecimal("10.00"), 1)))
                .paid();
    }

    private static final class InMemoryOrders implements OrderRepository {
        private final Map<String, PurchaseOrder> values = new HashMap<>();

        @Override public PurchaseOrder save(PurchaseOrder order) { values.put(order.orderNo(), order); return order; }
        @Override public Optional<PurchaseOrder> findByCustomerIdAndIdempotencyKey(UUID customerId, String key) { return Optional.empty(); }
        @Override public Optional<PurchaseOrder> findByOrderNo(String orderNo) { return Optional.ofNullable(values.get(orderNo)); }
    }

    private static final class InMemoryShipments implements ShipmentRepository {
        private final Map<UUID, Shipment> values = new HashMap<>();

        @Override public Shipment save(Shipment shipment) { values.put(shipment.orderId(), shipment); return shipment; }
        @Override public Optional<Shipment> findByOrderId(UUID orderId) { return Optional.ofNullable(values.get(orderId)); }
    }
}
