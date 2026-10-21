package com.zscq.mall.commerce.storedesign.domain;

import tools.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.UUID;

public record StoreDesign(
        UUID merchantId,
        StoreChannel channel,
        long draftVersion,
        Long publishedVersion,
        JsonNode draft,
        JsonNode published,
        Instant updatedAt,
        Instant publishedAt) {
}
