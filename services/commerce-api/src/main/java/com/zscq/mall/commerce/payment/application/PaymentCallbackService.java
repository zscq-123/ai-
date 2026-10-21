package com.zscq.mall.commerce.payment.application;
import com.zscq.mall.commerce.order.OrderPaymentFacade;
import com.zscq.mall.commerce.payment.domain.PaymentCallbackRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PaymentCallbackService {
    private final PaymentCallbackRepository callbacks; private final OrderPaymentFacade orders; private final String secret;
    public PaymentCallbackService(PaymentCallbackRepository callbacks, OrderPaymentFacade orders, @Value("${commerce.payment.webhook-secret:local-payment-secret}") String secret) { this.callbacks=callbacks; this.orders=orders; this.secret=secret; }
    @Transactional
    public boolean accept(String callbackId, String orderNo, String provider, String signature, String payload) {
        String signedContent = canonical(callbackId, orderNo, provider, payload);
        byte[] expected = hmac(signedContent);
        byte[] supplied;
        try {
            supplied = HexFormat.of().parseHex(signature);
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException("Invalid payment signature", exception);
        }
        if (!MessageDigest.isEqual(expected, supplied)) throw new IllegalArgumentException("Invalid payment signature");
        String hash=HexFormat.of().formatHex(digest(signedContent));
        if (!callbacks.register(callbackId,orderNo,provider,hash)) {
            var existing = callbacks.find(callbackId).orElseThrow(() -> new IllegalStateException("Callback replay state unavailable"));
            if (!existing.orderNo().equals(orderNo) || !existing.provider().equals(provider) || !existing.payloadHash().equals(hash)) {
                throw new SecurityException("Payment callback replay conflict");
            }
            return false;
        }
        orders.markPaid(orderNo); return true;
    }
    public static String canonical(String callbackId, String orderNo, String provider, String payload) {
        return callbackId + "\n" + orderNo + "\n" + provider + "\n" + payload;
    }
    private byte[] hmac(String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return mac.doFinal(value.getBytes(StandardCharsets.UTF_8));
        } catch (Exception exception) {
            throw new IllegalStateException(exception);
        }
    }
    private byte[] digest(String value) { try { return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)); } catch (Exception e) { throw new IllegalStateException(e); } }
}
