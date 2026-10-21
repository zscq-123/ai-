package com.zscq.mall.commerce.customer.domain;

import java.time.Instant;
import java.util.Optional;

public interface CustomerSessionRepository {
    CustomerSession save(CustomerSession session);
    Optional<CustomerSession> findByTokenHash(String tokenHash);
    void revokeByTokenHash(String tokenHash, Instant revokedAt);
}
