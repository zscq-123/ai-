package com.zscq.mall.commerce.customer.domain;

import java.time.Instant;
import java.util.UUID;

public record CustomerSession(
        UUID id,
        UUID customerId,
        String tokenHash,
        Instant expiresAt,
        Instant createdAt,
        Instant revokedAt) {

    public static CustomerSession create(UUID customerId, String tokenHash, Instant now, Instant expiresAt) {
        return new CustomerSession(UUID.randomUUID(), customerId, tokenHash, expiresAt, now, null);
    }

    public boolean isActiveAt(Instant now) {
        return revokedAt == null && expiresAt.isAfter(now);
    }
}
