package com.zscq.mall.commerce.customer.infrastructure;

import com.zscq.mall.commerce.customer.domain.Customer;
import com.zscq.mall.commerce.customer.domain.CustomerStatus;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "customers")
class CustomerEntity {
    @Id UUID id;
    String email;
    String displayName;
    String passwordHash;
    @Enumerated(EnumType.STRING) CustomerStatus status;
    Instant createdAt;
    Instant updatedAt;
    Instant lastLoginAt;

    protected CustomerEntity() {}

    CustomerEntity(Customer customer) {
        id = customer.id();
        email = customer.email();
        displayName = customer.displayName();
        passwordHash = customer.passwordHash();
        status = customer.status();
        createdAt = customer.createdAt();
        updatedAt = customer.updatedAt();
        lastLoginAt = customer.lastLoginAt();
    }

    Customer toDomain() {
        return new Customer(id, email, displayName, passwordHash, status, createdAt, updatedAt, lastLoginAt);
    }
}
