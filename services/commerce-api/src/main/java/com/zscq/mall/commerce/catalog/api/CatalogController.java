package com.zscq.mall.commerce.catalog.api;

import com.zscq.mall.commerce.catalog.application.CatalogService;
import com.zscq.mall.commerce.catalog.domain.Product;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import com.zscq.mall.commerce.config.MarketplaceAuthorization;

@RestController
@RequestMapping("/api")
public class CatalogController {
    private final CatalogService service;
    private final MarketplaceAuthorization authorization;
    public CatalogController(CatalogService service, MarketplaceAuthorization authorization) { this.service = service; this.authorization = authorization; }

    @GetMapping("/public/categories")
    List<com.zscq.mall.commerce.catalog.domain.Category> categories() { return service.categories(); }

    @GetMapping("/public/products")
    List<Product> search(@RequestParam(defaultValue = "") String query, @RequestParam(required = false) UUID categoryId) {
        return service.search(query, categoryId);
    }

    @GetMapping("/public/products/{productId}")
    Product detail(@PathVariable UUID productId) {
        try {
            return service.getActive(productId);
        } catch (java.util.NoSuchElementException exception) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Product not found", exception);
        }
    }

    @PostMapping("/products")
    @ResponseStatus(HttpStatus.CREATED)
    Product create(@Valid @RequestBody CreateProductRequest r, Authentication authentication) {
        authorization.requireMerchant(authentication, r.merchantId());
        return service.create(r.merchantId(), r.categoryId(), r.name(), r.subtitle(), r.brand(), r.description(), r.weightKg(), r.skuCode(), r.skuTitle(), r.salePrice(), r.marketPrice(), r.availableStock(), r.imageUrls());
    }

    @PutMapping("/products/{productId}")
    Product update(@PathVariable UUID productId, @Valid @RequestBody UpdateProductRequest r, Authentication authentication) {
        Product existing = service.get(productId);
        authorization.requireMerchant(authentication, existing.merchantId());
        return service.update(productId, existing.merchantId(), r.expectedVersion(), r.categoryId(), r.name(), r.subtitle(), r.brand(), r.description(), r.weightKg(), r.skuCode(), r.skuTitle(), r.salePrice(), r.marketPrice(), r.availableStock(), r.imageUrls());
    }

    @GetMapping("/seller/{merchantId}/products/{productId}")
    Product sellerDetail(@PathVariable UUID merchantId, @PathVariable UUID productId, Authentication authentication) {
        authorization.requireMerchant(authentication, merchantId);
        return service.getForMerchant(productId, merchantId);
    }

    @PutMapping("/seller/{merchantId}/products/{productId}")
    Product sellerUpdate(@PathVariable UUID merchantId, @PathVariable UUID productId,
                         @Valid @RequestBody UpdateProductRequest r, Authentication authentication) {
        authorization.requireMerchant(authentication, merchantId);
        service.getForMerchant(productId, merchantId);
        return service.update(productId, merchantId, r.expectedVersion(), r.categoryId(), r.name(), r.subtitle(),
                r.brand(), r.description(), r.weightKg(), r.skuCode(), r.skuTitle(), r.salePrice(), r.marketPrice(), r.availableStock(), r.imageUrls());
    }

    @PostMapping("/seller/{merchantId}/products")
    @ResponseStatus(HttpStatus.CREATED)
    Product sellerCreate(@PathVariable UUID merchantId, @Valid @RequestBody SellerCreateProductRequest r, Authentication authentication) {
        authorization.requireMerchant(authentication, merchantId);
        return service.create(merchantId, r.categoryId(), r.name(), r.subtitle(), r.brand(), r.description(), r.weightKg(),
                r.skuCode(), r.skuTitle(), r.salePrice(), r.marketPrice(), r.availableStock(), r.imageUrls());
    }

    record CreateProductRequest(@NotNull UUID merchantId, @NotNull UUID categoryId, @NotBlank String name,
                                String subtitle, String brand, String description, @PositiveOrZero BigDecimal weightKg,
                                @NotBlank String skuCode, @NotBlank String skuTitle,
                                @NotNull @PositiveOrZero BigDecimal salePrice, @PositiveOrZero BigDecimal marketPrice,
                                @PositiveOrZero int availableStock, @Size(max = 9) List<@NotBlank String> imageUrls) {}
    record UpdateProductRequest(@NotNull @PositiveOrZero Long expectedVersion, @NotNull UUID categoryId, @NotBlank String name, String subtitle,
                                String brand, String description, @PositiveOrZero BigDecimal weightKg,
                                @NotBlank String skuCode, @NotBlank String skuTitle,
                                @NotNull @PositiveOrZero BigDecimal salePrice,
                                @PositiveOrZero BigDecimal marketPrice,
                                @PositiveOrZero int availableStock, @Size(max = 9) List<@NotBlank String> imageUrls) {}

    record SellerCreateProductRequest(@NotNull UUID categoryId, @NotBlank String name,
                                String subtitle, String brand, String description, @PositiveOrZero BigDecimal weightKg,
                                @NotBlank String skuCode, @NotBlank String skuTitle,
                                @NotNull @PositiveOrZero BigDecimal salePrice, @PositiveOrZero BigDecimal marketPrice,
                                @PositiveOrZero int availableStock, @Size(max = 9) List<@NotBlank String> imageUrls) {}
}
