package com.zscq.mall.commerce.merchant.domain;
import java.util.UUID;
public interface MerchantAuditRepository { void record(String action, UUID merchantId, String detail); }
