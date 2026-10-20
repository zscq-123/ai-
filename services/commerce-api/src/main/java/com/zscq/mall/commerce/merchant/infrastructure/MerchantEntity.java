package com.zscq.mall.commerce.merchant.infrastructure;

import com.zscq.mall.commerce.merchant.domain.*;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "merchants")
class MerchantEntity {
    @Id UUID id;
    String legalName;
    String storeName;
    String contactName;
    String contactPhone;
    String businessLicenseNo;
    @Enumerated(EnumType.STRING) MerchantStatus status;
    String rejectionReason;
    Instant createdAt;
    Instant reviewedAt;
    protected MerchantEntity() {}
    MerchantEntity(Merchant m) { id=m.id(); legalName=m.legalName(); storeName=m.storeName(); contactName=m.contactName(); contactPhone=m.contactPhone(); businessLicenseNo=m.businessLicenseNo(); status=m.status(); rejectionReason=m.rejectionReason(); createdAt=m.createdAt(); reviewedAt=m.reviewedAt(); }
    Merchant toDomain() { return new Merchant(id, legalName, storeName, contactName, contactPhone, businessLicenseNo, status, rejectionReason, createdAt, reviewedAt); }
}
