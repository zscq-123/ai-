package com.zscq.mall.commerce.config;

import com.zscq.mall.commerce.customer.application.AuthenticatedCustomer;
import com.zscq.mall.commerce.customer.application.CustomerAuthService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Arrays;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
class CustomerSessionAuthenticationFilter extends OncePerRequestFilter {
    private static final String COOKIE_NAME = "nova_session";
    private final CustomerAuthService auth;

    CustomerSessionAuthenticationFilter(CustomerAuthService auth) {
        this.auth = auth;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() == null) {
            String token = cookie(request, COOKIE_NAME);
            if (token != null) {
                try {
                    AuthenticatedCustomer customer = auth.authenticate(token);
                    SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                            customer, token, java.util.List.of(new SimpleGrantedAuthority("ROLE_CUSTOMER"))));
                } catch (SecurityException ignored) {
                    // Invalid/expired cookies remain anonymous and are rejected by endpoint authorization.
                }
            }
        }
        chain.doFilter(request, response);
    }

    private static String cookie(HttpServletRequest request, String name) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) return null;
        return Arrays.stream(cookies).filter(cookie -> name.equals(cookie.getName()))
                .map(Cookie::getValue).findFirst().orElse(null);
    }
}
