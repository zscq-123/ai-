package com.zscq.mall.commerce.payment.domain;
public interface PaymentCallbackRepository { boolean register(String callbackId, String orderNo, String provider, String payloadHash); }
