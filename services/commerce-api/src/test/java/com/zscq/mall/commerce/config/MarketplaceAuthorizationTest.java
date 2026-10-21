package com.zscq.mall.commerce.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.customer.application.AuthenticatedCustomer;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.server.ResponseStatusException;

class MarketplaceAuthorizationTest {
    private final MarketplaceAuthorization authorization = new MarketplaceAuthorization(false);

    @Test
    void sellerCanOnlyAccessMerchantBoundToJwtClaim() {
        UUID merchantId = UUID.randomUUID();
        var authentication = jwt(Map.of("merchant_id", merchantId.toString()), "ROLE_SELLER");

        authorization.requireMerchant(authentication, merchantId);
        assertThatThrownBy(() -> authorization.requireMerchant(authentication, UUID.randomUUID()))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("403");
    }

    @Test
    void customerIdComesFromTrustedPrincipalRatherThanRequestData() {
        UUID customerId = UUID.randomUUID();
        var principal = new AuthenticatedCustomer(customerId, "buyer@example.com", "Buyer");
        var authentication = new UsernamePasswordAuthenticationToken(
                principal, "session", List.of(new SimpleGrantedAuthority("ROLE_CUSTOMER")));

        assertThat(authorization.customerId(authentication)).isEqualTo(customerId);
    }

    @Test
    void jwtRolesSupportDirectAndKeycloakRealmClaims() {
        Jwt jwt = new Jwt("token", Instant.now(), Instant.now().plusSeconds(60), Map.of("alg", "none"),
                Map.of("roles", List.of("seller"), "realm_access", Map.of("roles", List.of("customer"))));
        var authentication = new SecurityConfig().jwtAuthenticationConverter().convert(jwt);

        assertThat(authentication.getAuthorities()).extracting("authority")
                .contains("ROLE_SELLER", "ROLE_CUSTOMER");
    }

    private static JwtAuthenticationToken jwt(Map<String, Object> claims, String role) {
        Jwt jwt = new Jwt("token", Instant.now(), Instant.now().plusSeconds(60),
                Map.of("alg", "none"), claims);
        return new JwtAuthenticationToken(jwt, List.of(new SimpleGrantedAuthority(role)));
    }
}
