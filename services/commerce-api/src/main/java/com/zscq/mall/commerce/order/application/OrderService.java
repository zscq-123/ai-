package com.zscq.mall.commerce.order.application;
import com.zscq.mall.commerce.order.domain.*;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {
    private final OrderRepository orders; private final SkuPricingRepository pricing;
    public OrderService(OrderRepository orders, SkuPricingRepository pricing) { this.orders=orders; this.pricing=pricing; }
    @Transactional
    public PurchaseOrder create(UUID customerId, String key, List<Item> items) {
        return orders.findByIdempotencyKey(key).orElseGet(() -> {
            List<OrderLine> lines = items.stream().map(item -> {
                SkuSnapshot sku = pricing.find(item.skuId()).orElseThrow(() -> new IllegalArgumentException("SKU not found"));
                if (sku.stock() < item.quantity()) throw new IllegalStateException("Insufficient stock");
                return new OrderLine(UUID.randomUUID(), sku.skuId(), sku.productName(), sku.skuTitle(), sku.price(), item.quantity());
            }).toList();
            UUID merchant = pricing.find(items.getFirst().skuId()).orElseThrow().merchantId();
            if (lines.stream().anyMatch(line -> !pricing.find(line.skuId()).orElseThrow().merchantId().equals(merchant))) throw new IllegalArgumentException("One order can only contain one merchant");
            return orders.save(PurchaseOrder.create(customerId, merchant, key, lines));
        });
    }
    @Transactional
    public PurchaseOrder markPaid(String orderNo) { PurchaseOrder order=orders.findByOrderNo(orderNo).orElseThrow(); return orders.save(order.paid()); }
    public record Item(UUID skuId, int quantity) {}
}
