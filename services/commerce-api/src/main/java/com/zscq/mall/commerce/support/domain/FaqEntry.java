package com.zscq.mall.commerce.support.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record FaqEntry(
        UUID id,
        UUID merchantId,
        String question,
        String answer,
        List<String> keywords,
        FaqStatus status,
        int displayOrder,
        Instant createdAt,
        Instant updatedAt,
        Instant publishedAt) {

    public record Draft(String question, String answer, List<String> keywords, int displayOrder) { }
}
