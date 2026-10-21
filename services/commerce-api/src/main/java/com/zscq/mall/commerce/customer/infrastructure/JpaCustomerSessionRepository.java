package com.zscq.mall.commerce.customer.infrastructure;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface JpaCustomerSessionRepository extends JpaRepository<CustomerSessionEntity, UUID> {
    Optional<CustomerSessionEntity> findByTokenHash(String tokenHash);

    @Modifying
    @Query("update CustomerSessionEntity s set s.revokedAt = :revokedAt where s.tokenHash = :tokenHash and s.revokedAt is null")
    void revokeByTokenHash(@Param("tokenHash") String tokenHash, @Param("revokedAt") Instant revokedAt);
}
