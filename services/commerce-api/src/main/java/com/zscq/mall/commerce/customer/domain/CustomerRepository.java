package com.zscq.mall.commerce.customer.domain;

import java.util.Optional;
import java.util.UUID;

public interface CustomerRepository {
    Customer save(Customer customer);
    Optional<Customer> findByEmail(String email);
    Optional<Customer> findById(UUID id);
    boolean existsByEmail(String email);
}
