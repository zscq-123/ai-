package com.zscq.mall.commerce.order.application;

import com.zscq.mall.commerce.order.domain.OrderRepository;
import com.zscq.mall.commerce.order.domain.OrderStatus;
import com.zscq.mall.commerce.order.domain.PurchaseOrder;
import com.zscq.mall.commerce.order.domain.Shipment;
import com.zscq.mall.commerce.order.domain.ShipmentRepository;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

@Service
public class ShipmentService {
    private static final Set<OrderStatus> SHIPPABLE = Set.of(OrderStatus.PAID, OrderStatus.FULFILLING, OrderStatus.SHIPPED);
    private final OrderRepository orders;
    private final ShipmentRepository shipments;

    public ShipmentService(OrderRepository orders, ShipmentRepository shipments) {
        this.orders = orders;
        this.shipments = shipments;
    }

    @Transactional
    public Shipment record(
            UUID merchantId,
            String orderNo,
            String carrierCode,
            String carrierName,
            String trackingNo,
            String status,
            String latestEvent) {
        PurchaseOrder order = orders.findByOrderNo(orderNo)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Order not found"));
        if (!order.merchantId().equals(merchantId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Order does not belong to merchant");
        }
        if (!SHIPPABLE.contains(order.status())) {
            throw new IllegalStateException("Order is not ready for shipment");
        }
        Shipment existing = shipments.findByOrderId(order.id()).orElse(null);
        Shipment shipment = Shipment.record(
                order, existing, carrierCode, carrierName, trackingNo, status, latestEvent);
        orders.save(order.shipped());
        return shipments.save(shipment);
    }
}
