package com.zscq.mall.commerce.order.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.order.domain.OrderRepository;
import com.zscq.mall.commerce.order.domain.PurchaseOrder;
import com.zscq.mall.commerce.order.domain.SkuPricingRepository;
import com.zscq.mall.commerce.order.domain.SkuSnapshot;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OrderServiceTest {
    @Test
    void scopesIdempotencyKeysToTheCustomer() {
        UUID merchantId = UUID.randomUUID();
        UUID skuId = UUID.randomUUID();
        UUID firstCustomer = UUID.randomUUID();
        UUID secondCustomer = UUID.randomUUID();
        InMemoryOrders orders = new InMemoryOrders();
        OrderService service = new OrderService(orders, pricing(Map.of(
                skuId, sku(skuId, merchantId))));

        PurchaseOrder first = service.create(firstCustomer, "checkout-1", List.of(new OrderService.Item(skuId, 1)));
        PurchaseOrder replay = service.create(firstCustomer, "checkout-1", List.of(new OrderService.Item(skuId, 1)));
        PurchaseOrder second = service.create(secondCustomer, "checkout-1", List.of(new OrderService.Item(skuId, 1)));

        assertThat(replay.id()).isEqualTo(first.id());
        assertThat(second.id()).isNotEqualTo(first.id());
        assertThat(second.customerId()).isEqualTo(secondCustomer);
    }

    @Test
    void rejectsItemsOwnedByDifferentMerchantsWithoutRepeatedLookups() {
        UUID firstSku = UUID.randomUUID();
        UUID secondSku = UUID.randomUUID();
        Map<UUID, Integer> calls = new HashMap<>();
        Map<UUID, SkuSnapshot> values = Map.of(
                firstSku, sku(firstSku, UUID.randomUUID()),
                secondSku, sku(secondSku, UUID.randomUUID()));
        SkuPricingRepository repository = new SkuPricingRepository() {
            public Optional<SkuSnapshot> find(UUID id) { return Optional.ofNullable(values.get(id)); }
            public Optional<SkuSnapshot> reserve(UUID id, int quantity) {
                calls.merge(id, 1, Integer::sum);
                return Optional.ofNullable(values.get(id)).filter(sku -> sku.stock() >= quantity);
            }
        };
        OrderService service = new OrderService(new InMemoryOrders(), repository);

        assertThatThrownBy(() -> service.create(UUID.randomUUID(), "checkout-2", List.of(
                new OrderService.Item(firstSku, 1), new OrderService.Item(secondSku, 1))))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("One order can only contain one merchant");
        assertThat(calls).containsEntry(firstSku, 1).containsEntry(secondSku, 1);
    }

    private static SkuPricingRepository pricing(Map<UUID, SkuSnapshot> values) {
        return new SkuPricingRepository() {
            public Optional<SkuSnapshot> find(UUID id) { return Optional.ofNullable(values.get(id)); }
            public Optional<SkuSnapshot> reserve(UUID id, int quantity) {
                return Optional.ofNullable(values.get(id)).filter(sku -> sku.stock() >= quantity);
            }
        };
    }

    private static SkuSnapshot sku(UUID skuId, UUID merchantId) {
        return new SkuSnapshot(skuId, merchantId, "Product", "SKU", new BigDecimal("10.00"), 5);
    }

    private static final class InMemoryOrders implements OrderRepository {
        private final Map<String, PurchaseOrder> orders = new HashMap<>();

        @Override
        public PurchaseOrder save(PurchaseOrder order) {
            orders.put(key(order.customerId(), order.idempotencyKey()), order);
            return order;
        }

        @Override
        public Optional<PurchaseOrder> findByCustomerIdAndIdempotencyKey(UUID customerId, String key) {
            return Optional.ofNullable(orders.get(key(customerId, key)));
        }

        @Override
        public Optional<PurchaseOrder> findByOrderNo(String orderNo) {
            return orders.values().stream().filter(order -> order.orderNo().equals(orderNo)).findFirst();
        }

        private static String key(UUID customerId, String idempotencyKey) {
            return customerId + ":" + idempotencyKey;
        }
    }
}
