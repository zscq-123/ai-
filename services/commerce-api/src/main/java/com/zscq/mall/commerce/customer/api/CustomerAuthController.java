package com.zscq.mall.commerce.customer.api;

import com.zscq.mall.commerce.customer.application.AuthSession;
import com.zscq.mall.commerce.customer.application.AuthenticatedCustomer;
import com.zscq.mall.commerce.customer.application.CustomerAuthService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CookieValue;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/public/auth")
public class CustomerAuthController {
    static final String COOKIE_NAME = "nova_session";
    private final CustomerAuthService service;
    private final boolean secureCookie;

    public CustomerAuthController(
            CustomerAuthService service,
            @Value("${commerce.auth.secure-cookie:false}") boolean secureCookie) {
        this.service = service;
        this.secureCookie = secureCookie;
    }

    @PostMapping("/register")
    ResponseEntity<AuthenticatedCustomer> register(@Valid @RequestBody RegisterRequest request) {
        AuthSession session = service.register(request.displayName(), request.email(), request.password());
        return authenticatedResponse(session, HttpStatus.CREATED);
    }

    @PostMapping("/login")
    ResponseEntity<AuthenticatedCustomer> login(@Valid @RequestBody LoginRequest request) {
        AuthSession session = service.login(request.email(), request.password());
        return authenticatedResponse(session, HttpStatus.OK);
    }

    @GetMapping("/me")
    AuthenticatedCustomer me(@CookieValue(name = COOKIE_NAME, required = false) String token) {
        return service.authenticate(token);
    }

    @PostMapping("/logout")
    ResponseEntity<Void> logout(@CookieValue(name = COOKIE_NAME, required = false) String token) {
        service.logout(token);
        ResponseCookie cookie = cookie("", Duration.ZERO);
        return ResponseEntity.noContent().header(HttpHeaders.SET_COOKIE, cookie.toString()).build();
    }

    private ResponseEntity<AuthenticatedCustomer> authenticatedResponse(AuthSession session, HttpStatus status) {
        ResponseCookie cookie = cookie(session.token(), session.maxAge());
        return ResponseEntity.status(status)
                .header(HttpHeaders.SET_COOKIE, cookie.toString())
                .body(session.customer());
    }

    private ResponseCookie cookie(String value, Duration maxAge) {
        return ResponseCookie.from(COOKIE_NAME, value)
                .httpOnly(true)
                .secure(secureCookie)
                .sameSite("Lax")
                .path("/")
                .maxAge(maxAge)
                .build();
    }

    record RegisterRequest(
            @NotBlank @Size(min = 2, max = 80) String displayName,
            @NotBlank @Email @Size(max = 254) String email,
            @NotBlank @Size(min = 8, max = 72) String password) {}

    record LoginRequest(
            @NotBlank @Email @Size(max = 254) String email,
            @NotBlank @Size(min = 8, max = 72) String password) {}
}
