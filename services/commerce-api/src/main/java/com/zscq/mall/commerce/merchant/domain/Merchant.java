package com.zscq.mall.commerce.merchant.domain;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record Merchant(UUID id, String legalName, String storeName, String contactName,
                       String contactPhone, String businessLicenseNo, MerchantStatus status,
                       String rejectionReason, Instant createdAt, Instant reviewedAt) {
    public Merchant {
        Objects.requireNonNull(id); Objects.requireNonNull(legalName); Objects.requireNonNull(storeName);
        Objects.requireNonNull(contactName); Objects.requireNonNull(contactPhone);
        Objects.requireNonNull(businessLicenseNo); Objects.requireNonNull(status); Objects.requireNonNull(createdAt);
    }

    public static Merchant apply(String legalName, String storeName, String contactName, String contactPhone, String licenseNo) {
        return new Merchant(UUID.randomUUID(), legalName, storeName, contactName, contactPhone, licenseNo,
                MerchantStatus.PENDING_REVIEW, null, Instant.now(), null);
    }

    public Merchant approve() {
        if (status != MerchantStatus.PENDING_REVIEW) throw new IllegalStateException("Only pending merchants can be approved");
        return new Merchant(id, legalName, storeName, contactName, contactPhone, businessLicenseNo,
                MerchantStatus.ACTIVE, null, createdAt, Instant.now());
    }

    public Merchant reject(String reason) {
        if (status != MerchantStatus.PENDING_REVIEW) throw new IllegalStateException("Only pending merchants can be rejected");
        return new Merchant(id, legalName, storeName, contactName, contactPhone, businessLicenseNo,
                MerchantStatus.REJECTED, Objects.requireNonNull(reason), createdAt, Instant.now());
    }
}
