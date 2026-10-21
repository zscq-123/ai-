package com.zscq.mall.commerce.config;

import com.zscq.mall.commerce.customer.application.AuthenticatedCustomer;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

@Component
public class MarketplaceAuthorization {
    private final boolean localPublic;

    public MarketplaceAuthorization(@Value("${commerce.security.local-admin-public:false}") boolean localPublic) {
        this.localPublic = localPublic;
    }

    public void requireMerchant(Authentication authentication, UUID merchantId) {
        if (localPublic) return;
        if (hasRole(authentication, "ROLE_ADMIN")) return;
        Jwt jwt = jwt(authentication);
        UUID claim = uuidClaim(jwt, "merchant_id");
        if (!hasRole(authentication, "ROLE_SELLER") || !merchantId.equals(claim)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Merchant access denied");
        }
    }

    public UUID customerId(Authentication authentication) {
        if (authentication != null && authentication.getPrincipal() instanceof AuthenticatedCustomer customer) {
            return customer.id();
        }
        Jwt jwt = jwt(authentication);
        UUID customerId = uuidClaim(jwt, "customer_id");
        if (!hasRole(authentication, "ROLE_CUSTOMER") || customerId == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Customer identity required");
        }
        return customerId;
    }

    public boolean isAdmin(Authentication authentication) {
        return hasRole(authentication, "ROLE_ADMIN");
    }

    private static boolean hasRole(Authentication authentication, String role) {
        return authentication != null && authentication.getAuthorities().stream()
                .anyMatch(authority -> role.equals(authority.getAuthority()));
    }

    private static Jwt jwt(Authentication authentication) {
        if (authentication != null && authentication.getPrincipal() instanceof Jwt jwt) return jwt;
        return null;
    }

    private static UUID uuidClaim(Jwt jwt, String name) {
        if (jwt == null) return null;
        String value = jwt.getClaimAsString(name);
        try {
            return value == null ? null : UUID.fromString(value);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }
}
