package com.zscq.mall.commerce.externalcatalog.api;

import com.zscq.mall.commerce.externalcatalog.application.ExternalProductDetailsService;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetails;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/integrations/lazada/products")
public class ExternalProductDetailsController {
    private final ExternalProductDetailsService service;

    public ExternalProductDetailsController(ExternalProductDetailsService service) { this.service = service; }

    @PostMapping("/{productId}/details")
    ExternalProductDetailsService.DetailResult supplement(@PathVariable UUID productId, @Valid @RequestBody DetailRequest request) {
        return service.supplement(productId, request.expectedVersion(), new ExternalProductDetails(
                ExternalProductDetailsService.PROVIDER, request.sourceUrl(), request.capturedAt(), request.brand(), request.description(),
                request.highlights(), request.attributes(), request.options(), request.sellerName(), request.sellerUrl(),
                request.observations(), request.imageUrls()));
    }

    record DetailRequest(@NotNull @PositiveOrZero Long expectedVersion,
            @NotBlank @Size(max = 2048) String sourceUrl, @NotNull Instant capturedAt,
            @Size(max = 100) String brand, @Size(max = 12000) String description,
            @Size(max = 20) List<@NotBlank @Size(max = 600) String> highlights,
            @Size(max = 60) Map<@NotBlank @Size(max = 80) String, @NotBlank @Size(max = 1200) String> attributes,
            @Size(max = 20) Map<@NotBlank @Size(max = 80) String, @NotNull @Size(max = 80) List<@NotBlank @Size(max = 200) String>> options,
            @Size(max = 160) String sellerName, @Size(max = 2048) String sellerUrl,
            @Size(max = 20) Map<@NotBlank @Size(max = 80) String, @NotBlank @Size(max = 1200) String> observations,
            @Size(max = 9) List<@NotBlank @Size(max = 2048) String> imageUrls) {}
}
