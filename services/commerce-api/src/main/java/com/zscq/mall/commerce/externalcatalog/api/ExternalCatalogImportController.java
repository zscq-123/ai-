package com.zscq.mall.commerce.externalcatalog.api;

import com.zscq.mall.commerce.externalcatalog.application.ExternalCatalogImportService;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProviderException;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/admin/integrations")
public class ExternalCatalogImportController {
    private final ExternalCatalogImportService service;

    public ExternalCatalogImportController(ExternalCatalogImportService service) {
        this.service = service;
    }

    @PostMapping("/lazada/import")
    ExternalCatalogImportService.ImportResult importLazada(@Valid @RequestBody LazadaImportRequest request) {
        try {
            return service.importLazada(request.urls(), request.limit() == null ? 20 : request.limit());
        } catch (ExternalCatalogProviderException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, exception.getMessage(), exception);
        }
    }

    @PostMapping("/bright-data/lazada/import")
    ExternalCatalogImportService.ImportResult importWithBrightData(@Valid @RequestBody LazadaImportRequest request) {
        try {
            return service.importLazadaFromBrightData(request.urls());
        } catch (ExternalCatalogProviderException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, exception.getMessage(), exception);
        }
    }

    @PostMapping({"/lazada/products/{productId}/publish", "/bright-data/lazada/products/{productId}/publish"})
    void publish(@PathVariable UUID productId) {
        service.publish(productId);
    }

    record LazadaImportRequest(@NotEmpty @Size(max = 20) List<String> urls, @Min(1) @Max(20) Integer limit) {}
}
