package com.zscq.mall.commerce.payment.domain;
public interface PaymentCallbackRepository {
    boolean register(String callbackId, String orderNo, String provider, String payloadHash);
    java.util.Optional<Fingerprint> find(String callbackId);
    record Fingerprint(String orderNo, String provider, String payloadHash) {}
}
