package com.zscq.mall.commerce.customer.domain;

import java.time.Instant;
import java.util.UUID;

public record Customer(
        UUID id,
        String email,
        String displayName,
        String passwordHash,
        CustomerStatus status,
        Instant createdAt,
        Instant updatedAt,
        Instant lastLoginAt) {

    public static Customer register(String email, String displayName, String passwordHash, Instant now) {
        return new Customer(UUID.randomUUID(), email, displayName, passwordHash,
                CustomerStatus.ACTIVE, now, now, null);
    }

    public Customer recordLogin(Instant now) {
        return new Customer(id, email, displayName, passwordHash, status, createdAt, now, now);
    }
}
