package com.zscq.mall.commerce.externalcatalog.api;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.validation.Validation;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ExternalProductDetailsValidationTest {
    @Test
    void validatesNestedOptionListsAndRequiresVersionAndCapturedTime() {
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var request = new ExternalProductDetailsController.DetailRequest(null, "https://www.lazada.sg/products/item-i123.html",
                    null, null, null, List.of(), Map.of(), Map.of("Color", List.of("")), null, null, Map.of(), List.of());
            var paths = factory.getValidator().validate(request).stream().map(violation -> violation.getPropertyPath().toString()).toList();
            assertThat(paths).contains("expectedVersion", "capturedAt");
            assertThat(paths).anyMatch(path -> path.startsWith("options"));
        }
    }

    @Test
    void acceptsACompleteVisibleDetailRequestWithoutImageUrls() {
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var request = new ExternalProductDetailsController.DetailRequest(0L, "https://www.lazada.sg/products/item-i123.html",
                    Instant.now(), null, null, List.of("Visible selling point"), Map.of("Size", "40 cm"),
                    Map.of("Color", List.of("Black")), "Visible shop", "https://www.lazada.sg/shop/example", Map.of(), null);
            assertThat(factory.getValidator().validate(request)).isEmpty();
        }
    }
}
