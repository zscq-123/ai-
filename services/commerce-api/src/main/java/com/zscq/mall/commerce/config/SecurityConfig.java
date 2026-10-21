package com.zscq.mall.commerce.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.core.convert.converter.Converter;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import java.util.List;

import org.springframework.beans.factory.annotation.Value;

@Configuration
public class SecurityConfig {

    @Bean
    SecurityFilterChain apiSecurity(
            HttpSecurity http,
            Environment environment,
            CustomerSessionAuthenticationFilter customerSessionAuthenticationFilter,
            @Value("${commerce.security.local-admin-public:false}") boolean localAdminPublic) throws Exception {
        if (localAdminPublic && !environment.acceptsProfiles(Profiles.of("local"))) {
            throw new IllegalStateException("commerce.security.local-admin-public is only allowed with the local profile");
        }
        return http
                .cors(Customizer.withDefaults())
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authorize -> {
                    // Keep controller status codes intact when Spring performs an ERROR dispatch.
                    // The original request has already passed the authorization rules below.
                    authorize.requestMatchers("/error").permitAll();
                    authorize.requestMatchers("/actuator/health/**", "/actuator/info", "/actuator/prometheus").permitAll();
                    authorize.requestMatchers("/api/public/**").permitAll();
                    if (localAdminPublic) {
                        authorize.requestMatchers("/api/admin/**", "/api/seller/**", "/api/merchants/**", "/api/products/**").permitAll();
                    } else {
                        authorize.requestMatchers("/api/admin/**", "/api/merchants/**").hasRole("ADMIN");
                        authorize.requestMatchers("/api/seller/**", "/api/products/**").hasAnyRole("SELLER", "ADMIN");
                    }
                    authorize.requestMatchers("/api/orders/**").hasRole("CUSTOMER");
                    authorize.anyRequest().authenticated();
                })
                .addFilterBefore(customerSessionAuthenticationFilter, org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter.class)
                .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())))
                .build();
    }

    @Bean
    JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        Converter<Jwt, java.util.Collection<GrantedAuthority>> authorities = jwt -> {
            java.util.LinkedHashSet<String> names = new java.util.LinkedHashSet<>();
            java.util.List<String> direct = jwt.getClaimAsStringList("roles");
            if (direct != null) names.addAll(direct);
            Object realmAccess = jwt.getClaim("realm_access");
            if (realmAccess instanceof java.util.Map<?, ?> map && map.get("roles") instanceof java.util.Collection<?> realmRoles) {
                for (Object realmRole : realmRoles) names.add(String.valueOf(realmRole));
            }
            return names.stream().map(String::toUpperCase)
                    .map(role -> (GrantedAuthority) new SimpleGrantedAuthority("ROLE_" + role)).toList();
        };
        converter.setJwtGrantedAuthoritiesConverter(authorities);
        return converter;
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource(
            @Value("${commerce.cors.allowed-origins:http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175}")
            List<String> allowedOrigins) {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(allowedOrigins);
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("Authorization", "Content-Type", "Idempotency-Key"));
        configuration.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", configuration);
        return source;
    }
}
