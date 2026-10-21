package com.zscq.mall.commerce.storedesign.domain;

import tools.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.UUID;

public record PublishedStoreDesign(
        UUID merchantId,
        String storeName,
        StoreChannel channel,
        long version,
        JsonNode config,
        Instant publishedAt) {
}
