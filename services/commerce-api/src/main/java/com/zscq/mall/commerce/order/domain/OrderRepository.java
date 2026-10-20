package com.zscq.mall.commerce.order.domain;
import java.util.Optional;
public interface OrderRepository {
    PurchaseOrder save(PurchaseOrder order);
    Optional<PurchaseOrder> findByIdempotencyKey(String key);
    Optional<PurchaseOrder> findByOrderNo(String orderNo);
}
