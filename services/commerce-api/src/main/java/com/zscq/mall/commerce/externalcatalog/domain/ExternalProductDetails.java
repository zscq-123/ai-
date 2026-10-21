package com.zscq.mall.commerce.externalcatalog.domain;

import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A separately captured detail-page observation, not a price or stock update. */
public record ExternalProductDetails(String provider, String sourceUrl, Instant capturedAt, String brand,
        String description, List<String> highlights, Map<String, String> attributes,
        Map<String, List<String>> options, String sellerName, String sellerUrl,
        Map<String, String> observations, List<String> imageUrls) {
    public ExternalProductDetails {
        highlights = highlights == null ? List.of() : List.copyOf(highlights);
        attributes = attributes == null ? Map.of() : Collections.unmodifiableMap(new LinkedHashMap<>(attributes));
        var normalizedOptions = new LinkedHashMap<String, List<String>>();
        if (options != null) options.forEach((key, values) -> normalizedOptions.put(key, List.copyOf(values)));
        options = Collections.unmodifiableMap(normalizedOptions);
        observations = observations == null ? Map.of() : Collections.unmodifiableMap(new LinkedHashMap<>(observations));
        imageUrls = imageUrls == null ? List.of() : List.copyOf(imageUrls);
    }
}
