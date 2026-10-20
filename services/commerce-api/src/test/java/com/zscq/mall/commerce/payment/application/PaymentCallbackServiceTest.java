package com.zscq.mall.commerce.payment.application;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.concurrent.atomic.AtomicBoolean;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.junit.jupiter.api.Test;

class PaymentCallbackServiceTest {
    private static final String SECRET = "a-development-secret-that-is-long-enough";

    @Test
    void verifiesHmacBeforeProcessingCallback() throws Exception {
        var registered = new AtomicBoolean();
        var paid = new AtomicBoolean();
        var service = new PaymentCallbackService(
                (callbackId, orderNo, provider, payloadHash) -> registered.compareAndSet(false, true),
                orderNo -> paid.set(true),
                SECRET);
        String payload = "{\"status\":\"paid\"}";

        assertThrows(IllegalArgumentException.class,
                () -> service.accept("callback-1", "NO-1", "sandbox", "not-hex", payload));

        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        String signature = HexFormat.of().formatHex(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));

        assertTrue(service.accept("callback-1", "NO-1", "sandbox", signature, payload));
        assertTrue(registered.get());
        assertTrue(paid.get());
    }
}
