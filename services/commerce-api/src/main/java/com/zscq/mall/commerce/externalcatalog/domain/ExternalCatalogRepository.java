package com.zscq.mall.commerce.externalcatalog.domain;

import java.util.UUID;

public interface ExternalCatalogRepository {
    UpsertedProduct upsert(ExternalCatalogProduct product);
    boolean publish(UUID productId);

    record UpsertedProduct(UUID productId, UUID merchantId, boolean created) {}
}
