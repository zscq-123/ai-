package com.zscq.mall.commerce.customer.infrastructure;

import com.zscq.mall.commerce.customer.domain.Customer;
import com.zscq.mall.commerce.customer.domain.CustomerRepository;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
class CustomerRepositoryAdapter implements CustomerRepository {
    private final JpaCustomerRepository repository;

    CustomerRepositoryAdapter(JpaCustomerRepository repository) {
        this.repository = repository;
    }

    @Override
    public Customer save(Customer customer) {
        return repository.save(new CustomerEntity(customer)).toDomain();
    }

    @Override
    public Optional<Customer> findByEmail(String email) {
        return repository.findByEmail(email).map(CustomerEntity::toDomain);
    }

    @Override
    public Optional<Customer> findById(UUID id) {
        return repository.findById(id).map(CustomerEntity::toDomain);
    }

    @Override
    public boolean existsByEmail(String email) {
        return repository.existsByEmail(email);
    }
}
