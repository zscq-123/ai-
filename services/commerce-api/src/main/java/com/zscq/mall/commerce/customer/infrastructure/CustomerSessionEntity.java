package com.zscq.mall.commerce.customer.infrastructure;

import com.zscq.mall.commerce.customer.domain.CustomerSession;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "customer_sessions")
class CustomerSessionEntity {
    @Id UUID id;
    UUID customerId;
    String tokenHash;
    Instant expiresAt;
    Instant createdAt;
    Instant revokedAt;

    protected CustomerSessionEntity() {}

    CustomerSessionEntity(CustomerSession session) {
        id = session.id();
        customerId = session.customerId();
        tokenHash = session.tokenHash();
        expiresAt = session.expiresAt();
        createdAt = session.createdAt();
        revokedAt = session.revokedAt();
    }

    CustomerSession toDomain() {
        return new CustomerSession(id, customerId, tokenHash, expiresAt, createdAt, revokedAt);
    }
}
