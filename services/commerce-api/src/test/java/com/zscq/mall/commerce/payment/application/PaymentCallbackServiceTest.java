package com.zscq.mall.commerce.payment.application;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.Optional;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.junit.jupiter.api.Test;

class PaymentCallbackServiceTest {
    private static final String SECRET = "a-development-secret-that-is-long-enough";

    @Test
    void verifiesHmacBeforeProcessingCallback() throws Exception {
        var registered = new AtomicBoolean();
        var paid = new AtomicBoolean();
        var repository = new com.zscq.mall.commerce.payment.domain.PaymentCallbackRepository() {
            Fingerprint saved;
            public boolean register(String callbackId, String orderNo, String provider, String payloadHash) {
                if (!registered.compareAndSet(false, true)) return false;
                saved = new Fingerprint(orderNo, provider, payloadHash);
                return true;
            }
            public Optional<Fingerprint> find(String callbackId) { return Optional.ofNullable(saved); }
        };
        var service = new PaymentCallbackService(
                repository,
                orderNo -> paid.set(true),
                SECRET);
        String payload = "{\"status\":\"paid\"}";

        assertThrows(IllegalArgumentException.class,
                () -> service.accept("callback-1", "NO-1", "sandbox", "not-hex", payload));

        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        String canonical = PaymentCallbackService.canonical("callback-1", "NO-1", "sandbox", payload);
        String signature = HexFormat.of().formatHex(mac.doFinal(canonical.getBytes(StandardCharsets.UTF_8)));

        assertTrue(service.accept("callback-1", "NO-1", "sandbox", signature, payload));
        assertTrue(registered.get());
        assertTrue(paid.get());
        assertFalse(service.accept("callback-1", "NO-1", "sandbox", signature, payload));

        String replayCanonical = PaymentCallbackService.canonical("callback-1", "NO-2", "sandbox", payload);
        String replaySignature = HexFormat.of().formatHex(mac.doFinal(replayCanonical.getBytes(StandardCharsets.UTF_8)));
        assertThrows(SecurityException.class,
                () -> service.accept("callback-1", "NO-2", "sandbox", replaySignature, payload));
    }
}
