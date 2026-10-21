package com.zscq.mall.commerce.order.domain;
import java.util.Optional;
import java.util.UUID;
public interface OrderRepository {
    PurchaseOrder save(PurchaseOrder order);
    Optional<PurchaseOrder> findByCustomerIdAndIdempotencyKey(UUID customerId, String key);
    Optional<PurchaseOrder> findByOrderNo(String orderNo);
}
