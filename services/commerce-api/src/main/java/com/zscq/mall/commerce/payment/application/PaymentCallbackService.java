package com.zscq.mall.commerce.payment.application;
import com.zscq.mall.commerce.order.OrderPaymentFacade;
import com.zscq.mall.commerce.payment.domain.PaymentCallbackRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PaymentCallbackService {
    private final PaymentCallbackRepository callbacks; private final OrderPaymentFacade orders; private final String secret;
    public PaymentCallbackService(PaymentCallbackRepository callbacks, OrderPaymentFacade orders, @Value("${commerce.payment.webhook-secret:local-payment-secret}") String secret) { this.callbacks=callbacks; this.orders=orders; this.secret=secret; }
    @Transactional
    public boolean accept(String callbackId, String orderNo, String provider, String signature, String payload) {
        if (!MessageDigest.isEqual(secret.getBytes(StandardCharsets.UTF_8), signature.getBytes(StandardCharsets.UTF_8))) throw new IllegalArgumentException("Invalid payment signature");
        String hash=HexFormat.of().formatHex(digest(payload));
        if (!callbacks.register(callbackId,orderNo,provider,hash)) return false;
        orders.markPaid(orderNo); return true;
    }
    private byte[] digest(String value) { try { return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)); } catch (Exception e) { throw new IllegalStateException(e); } }
}
