package com.zscq.mall.commerce.storedesign.domain;

import tools.jackson.databind.JsonNode;
import java.util.Optional;
import java.util.UUID;

public interface StoreDesignRepository {
    Optional<String> activeMerchantName(UUID merchantId);
    Optional<StoreDesign> find(UUID merchantId, StoreChannel channel);
    Optional<PublishedStoreDesign> findPublished(UUID merchantId, StoreChannel channel);
    StoreDesign saveDraft(UUID merchantId, StoreChannel channel, long expectedVersion, JsonNode config);
    StoreDesign publish(UUID merchantId, StoreChannel channel);
}
