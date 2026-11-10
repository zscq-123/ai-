package com.zscq.mall.commerce.support.domain;

import java.util.UUID;

public record SupportToolQuery(
        String message,
        UUID customerId,
        UUID merchantId,
        UUID productId,
        UUID skuId) {}
