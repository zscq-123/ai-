package com.zscq.mall.commerce.order.domain;
import java.util.Optional;
import java.util.UUID;
public interface SkuPricingRepository { Optional<SkuSnapshot> find(UUID skuId); }
