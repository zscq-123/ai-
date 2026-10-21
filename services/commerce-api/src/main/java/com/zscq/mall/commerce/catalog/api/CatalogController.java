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

@RestController
@RequestMapping("/api")
public class CatalogController {
    private final CatalogService service;
    public CatalogController(CatalogService service) { this.service = service; }

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
    Product create(@Valid @RequestBody CreateProductRequest r) {
        return service.create(r.merchantId(), r.categoryId(), r.name(), r.subtitle(), r.brand(), r.description(), r.weightKg(), r.skuCode(), r.skuTitle(), r.salePrice(), r.marketPrice(), r.availableStock());
    }

    @PutMapping("/products/{productId}")
    Product update(@PathVariable UUID productId, @Valid @RequestBody UpdateProductRequest r) {
        return service.update(productId, r.categoryId(), r.name(), r.subtitle(), r.brand(), r.description(), r.weightKg(), r.skuCode(), r.skuTitle(), r.salePrice(), r.marketPrice(), r.availableStock());
    }

    record CreateProductRequest(@NotNull UUID merchantId, @NotNull UUID categoryId, @NotBlank String name,
                                String subtitle, String brand, String description, @PositiveOrZero BigDecimal weightKg,
                                @NotBlank String skuCode, @NotBlank String skuTitle,
                                @NotNull @PositiveOrZero BigDecimal salePrice, @PositiveOrZero BigDecimal marketPrice,
                                @PositiveOrZero int availableStock) {}
    record UpdateProductRequest(@NotNull UUID categoryId, @NotBlank String name, String subtitle,
                                String brand, String description, @PositiveOrZero BigDecimal weightKg,
                                @NotBlank String skuCode, @NotBlank String skuTitle,
                                @NotNull @PositiveOrZero BigDecimal salePrice,
                                @PositiveOrZero BigDecimal marketPrice,
                                @PositiveOrZero int availableStock) {}
}
