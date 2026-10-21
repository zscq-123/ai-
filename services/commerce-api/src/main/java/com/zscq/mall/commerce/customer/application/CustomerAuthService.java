package com.zscq.mall.commerce.customer.application;

import com.zscq.mall.commerce.customer.domain.Customer;
import com.zscq.mall.commerce.customer.domain.CustomerRepository;
import com.zscq.mall.commerce.customer.domain.CustomerSession;
import com.zscq.mall.commerce.customer.domain.CustomerSessionRepository;
import com.zscq.mall.commerce.customer.domain.CustomerStatus;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CustomerAuthService {
    private final CustomerRepository customers;
    private final CustomerSessionRepository sessions;
    private final PasswordEncoder passwordEncoder;
    private final Duration sessionDuration;
    private final SecureRandom secureRandom = new SecureRandom();

    public CustomerAuthService(
            CustomerRepository customers,
            CustomerSessionRepository sessions,
            PasswordEncoder passwordEncoder,
            @Value("${commerce.auth.session-duration:PT168H}") Duration sessionDuration) {
        this.customers = customers;
        this.sessions = sessions;
        this.passwordEncoder = passwordEncoder;
        this.sessionDuration = sessionDuration;
    }

    @Transactional
    public AuthSession register(String displayName, String email, String password) {
        String normalizedEmail = normalizeEmail(email);
        if (customers.existsByEmail(normalizedEmail)) {
            throw new IllegalStateException("该邮箱已注册");
        }
        Instant now = Instant.now();
        Customer customer = customers.save(Customer.register(
                normalizedEmail, displayName.trim(), passwordEncoder.encode(password), now));
        return createSession(customer, now);
    }

    @Transactional
    public AuthSession login(String email, String password) {
        Customer customer = customers.findByEmail(normalizeEmail(email))
                .orElseThrow(CustomerAuthService::invalidCredentials);
        if (customer.status() != CustomerStatus.ACTIVE || !passwordEncoder.matches(password, customer.passwordHash())) {
            throw invalidCredentials();
        }
        Instant now = Instant.now();
        Customer updated = customers.save(customer.recordLogin(now));
        return createSession(updated, now);
    }

    @Transactional(readOnly = true)
    public AuthenticatedCustomer authenticate(String token) {
        if (token == null || token.isBlank()) {
            throw new SecurityException("请先登录");
        }
        Instant now = Instant.now();
        CustomerSession session = sessions.findByTokenHash(hashToken(token))
                .filter(candidate -> candidate.isActiveAt(now))
                .orElseThrow(() -> new SecurityException("登录状态已失效，请重新登录"));
        Customer customer = customers.findById(session.customerId())
                .filter(candidate -> candidate.status() == CustomerStatus.ACTIVE)
                .orElseThrow(() -> new SecurityException("账号不可用"));
        return AuthenticatedCustomer.from(customer);
    }

    @Transactional
    public void logout(String token) {
        if (token != null && !token.isBlank()) {
            sessions.revokeByTokenHash(hashToken(token), Instant.now());
        }
    }

    private AuthSession createSession(Customer customer, Instant now) {
        byte[] bytes = new byte[32];
        secureRandom.nextBytes(bytes);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        sessions.save(CustomerSession.create(customer.id(), hashToken(token), now, now.plus(sessionDuration)));
        return new AuthSession(AuthenticatedCustomer.from(customer), token, sessionDuration);
    }

    private static String normalizeEmail(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }

    private static SecurityException invalidCredentials() {
        return new SecurityException("邮箱或密码不正确");
    }

    private static String hashToken(String token) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 unavailable", exception);
        }
    }
}
