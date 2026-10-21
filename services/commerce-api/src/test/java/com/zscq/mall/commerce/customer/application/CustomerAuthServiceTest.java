package com.zscq.mall.commerce.customer.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.customer.domain.Customer;
import com.zscq.mall.commerce.customer.domain.CustomerRepository;
import com.zscq.mall.commerce.customer.domain.CustomerSession;
import com.zscq.mall.commerce.customer.domain.CustomerSessionRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

class CustomerAuthServiceTest {
    private final InMemoryCustomers customers = new InMemoryCustomers();
    private final InMemorySessions sessions = new InMemorySessions();
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);
    private final CustomerAuthService service = new CustomerAuthService(customers, sessions, encoder, Duration.ofDays(7));

    @Test
    void registrationHashesPasswordAndCreatesUsableSession() {
        AuthSession session = service.register("采购员小林", "Buyer@Example.com", "safe-password");

        Customer saved = customers.findByEmail("buyer@example.com").orElseThrow();
        assertThat(saved.passwordHash()).isNotEqualTo("safe-password");
        assertThat(encoder.matches("safe-password", saved.passwordHash())).isTrue();
        assertThat(service.authenticate(session.token()).email()).isEqualTo("buyer@example.com");
    }

    @Test
    void logoutRevokesTheOpaqueSession() {
        AuthSession session = service.register("采购员小周", "zhou@example.com", "safe-password");

        service.logout(session.token());

        assertThatThrownBy(() -> service.authenticate(session.token()))
                .isInstanceOf(SecurityException.class)
                .hasMessageContaining("失效");
    }

    @Test
    void loginRejectsWrongPasswordWithoutRevealingWhichFieldFailed() {
        service.register("采购员小吴", "wu@example.com", "safe-password");

        assertThatThrownBy(() -> service.login("wu@example.com", "wrong-password"))
                .isInstanceOf(SecurityException.class)
                .hasMessage("邮箱或密码不正确");
    }

    private static final class InMemoryCustomers implements CustomerRepository {
        private final Map<UUID, Customer> byId = new HashMap<>();

        @Override public Customer save(Customer customer) { byId.put(customer.id(), customer); return customer; }
        @Override public Optional<Customer> findByEmail(String email) { return byId.values().stream().filter(c -> c.email().equals(email)).findFirst(); }
        @Override public Optional<Customer> findById(UUID id) { return Optional.ofNullable(byId.get(id)); }
        @Override public boolean existsByEmail(String email) { return findByEmail(email).isPresent(); }
    }

    private static final class InMemorySessions implements CustomerSessionRepository {
        private final Map<String, CustomerSession> byHash = new HashMap<>();

        @Override public CustomerSession save(CustomerSession session) { byHash.put(session.tokenHash(), session); return session; }
        @Override public Optional<CustomerSession> findByTokenHash(String tokenHash) { return Optional.ofNullable(byHash.get(tokenHash)); }
        @Override public void revokeByTokenHash(String tokenHash, Instant revokedAt) {
            CustomerSession current = byHash.get(tokenHash);
            if (current != null) byHash.put(tokenHash, new CustomerSession(current.id(), current.customerId(), current.tokenHash(), current.expiresAt(), current.createdAt(), revokedAt));
        }
    }
}
