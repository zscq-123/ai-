package com.zscq.mall.commerce.merchant.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface MerchantRepository {
    Merchant save(Merchant merchant);
    Optional<Merchant> findById(UUID id);
    boolean existsByBusinessLicenseNo(String number);
    List<Merchant> findAll();
}
