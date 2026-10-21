package com.zscq.mall.commerce.customer.application;

import com.zscq.mall.commerce.customer.domain.Customer;
import java.util.UUID;

public record AuthenticatedCustomer(UUID id, String email, String displayName) {
    static AuthenticatedCustomer from(Customer customer) {
        return new AuthenticatedCustomer(customer.id(), customer.email(), customer.displayName());
    }
}
