package com.zscq.mall.commerce.externalcatalog.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ExternalProductDetailsRepository {
    Optional<DraftSnapshot> findForUpdate(UUID productId);
    long save(UUID productId, long expectedVersion, ExternalProductDetails details,
              String brandToFill, String descriptionToFill, List<String> imagesToReplace);

    record DraftSnapshot(UUID id, UUID merchantId, long version, String status, String sourcePlatform,
            String externalProductId, String sourceUrl, String sourceProvider, String brand,
            String description, List<String> imageUrls, String sourceImageUrl) {}
}
