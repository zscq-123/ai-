package com.zscq.mall.commerce.customer.infrastructure;

import com.zscq.mall.commerce.customer.domain.CustomerSession;
import com.zscq.mall.commerce.customer.domain.CustomerSessionRepository;
import java.time.Instant;
import java.util.Optional;
import org.springframework.stereotype.Repository;

@Repository
class CustomerSessionRepositoryAdapter implements CustomerSessionRepository {
    private final JpaCustomerSessionRepository repository;

    CustomerSessionRepositoryAdapter(JpaCustomerSessionRepository repository) {
        this.repository = repository;
    }

    @Override
    public CustomerSession save(CustomerSession session) {
        return repository.save(new CustomerSessionEntity(session)).toDomain();
    }

    @Override
    public Optional<CustomerSession> findByTokenHash(String tokenHash) {
        return repository.findByTokenHash(tokenHash).map(CustomerSessionEntity::toDomain);
    }

    @Override
    public void revokeByTokenHash(String tokenHash, Instant revokedAt) {
        repository.revokeByTokenHash(tokenHash, revokedAt);
    }
}
