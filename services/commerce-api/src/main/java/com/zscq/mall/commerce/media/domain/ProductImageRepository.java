package com.zscq.mall.commerce.media.domain;

import java.util.Optional;
import java.util.UUID;

public interface ProductImageRepository {
    boolean activeMerchantExists(UUID merchantId);
    void save(ProductImage image);
    Optional<ProductImage> find(UUID id);
}
