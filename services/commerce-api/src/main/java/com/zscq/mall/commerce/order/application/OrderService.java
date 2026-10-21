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
        if (customerId == null) throw new SecurityException("Customer identity required");
        if (items == null || items.isEmpty()) throw new IllegalArgumentException("Order must contain items");
        return orders.findByCustomerIdAndIdempotencyKey(customerId, key).orElseGet(() -> {
            List<PricedItem> pricedItems = items.stream().map(item -> {
                if (item.quantity() <= 0) throw new IllegalArgumentException("Quantity must be positive");
                SkuSnapshot sku = pricing.reserve(item.skuId(), item.quantity())
                        .orElseThrow(() -> new IllegalStateException("SKU not found or insufficient stock"));
                return new PricedItem(sku, item.quantity());
            }).toList();
            UUID merchant = pricedItems.getFirst().sku().merchantId();
            if (pricedItems.stream().anyMatch(item -> !item.sku().merchantId().equals(merchant))) {
                throw new IllegalArgumentException("One order can only contain one merchant");
            }
            List<OrderLine> lines = pricedItems.stream()
                    .map(item -> new OrderLine(UUID.randomUUID(), item.sku().skuId(), item.sku().productName(),
                            item.sku().skuTitle(), item.sku().price(), item.quantity()))
                    .toList();
            return orders.save(PurchaseOrder.create(customerId, merchant, key, lines));
        });
    }
    @Transactional
    public PurchaseOrder markPaid(String orderNo) { PurchaseOrder order=orders.findByOrderNo(orderNo).orElseThrow(); return orders.save(order.paid()); }
    public record Item(UUID skuId, int quantity) {}
    private record PricedItem(SkuSnapshot sku, int quantity) {}
}
