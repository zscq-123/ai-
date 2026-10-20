package com.zscq.mall.commerce.merchant.infrastructure;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface JpaMerchantRepository extends JpaRepository<MerchantEntity, UUID> {
    boolean existsByBusinessLicenseNo(String number);
}
