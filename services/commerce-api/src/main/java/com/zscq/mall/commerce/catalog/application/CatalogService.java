package com.zscq.mall.commerce.catalog.application;

import com.zscq.mall.commerce.catalog.domain.*;
import com.zscq.mall.commerce.media.MediaAssets;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CatalogService {
    private final CatalogRepository repository;
    private final MediaAssets media;
    public CatalogService(CatalogRepository repository, MediaAssets media) { this.repository = repository; this.media = media; }

    @Transactional
    public Product create(UUID merchantId, UUID categoryId, String name, String subtitle, String brand,
                          String description, BigDecimal weightKg, String skuCode,
                          String skuTitle, BigDecimal salePrice, BigDecimal marketPrice, int stock) {
        return create(merchantId, categoryId, name, subtitle, brand, description, weightKg, skuCode, skuTitle, salePrice, marketPrice, stock, List.of());
    }

    @Transactional
    public Product create(UUID merchantId, UUID categoryId, String name, String subtitle, String brand,
                          String description, BigDecimal weightKg, String skuCode,
                          String skuTitle, BigDecimal salePrice, BigDecimal marketPrice, int stock, List<String> imageUrls) {
        media.requireActiveMerchant(merchantId);
        var images = media.validateProductImages(merchantId, imageUrls, List.of());
        return repository.save(Product.draft(merchantId, categoryId, name, subtitle, brand, description, weightKg, skuCode, skuTitle, salePrice, marketPrice, stock).withImages(images));
    }

    @Transactional(readOnly = true)
    public List<Product> search(String query, UUID categoryId) { return repository.search(query, categoryId); }

    @Transactional(readOnly = true)
    public List<Category> categories() { return repository.categories(); }

    @Transactional(readOnly = true)
    public Product getActive(UUID productId) {
        return repository.findActiveById(productId).orElseThrow();
    }

    @Transactional(readOnly = true)
    public Product get(UUID productId) {
        return repository.findById(productId).orElseThrow();
    }

    @Transactional(readOnly = true)
    public Product getForMerchant(UUID productId, UUID merchantId) {
        Product product = get(productId);
        if (!product.merchantId().equals(merchantId)) throw new org.springframework.web.server.ResponseStatusException(
                org.springframework.http.HttpStatus.FORBIDDEN, "Product does not belong to merchant");
        return product;
    }

    @Transactional
    public Product update(UUID productId, UUID merchantId, long expectedVersion, UUID categoryId, String name, String subtitle, String brand,
                          String description, BigDecimal weightKg, String skuCode,
                          String skuTitle, BigDecimal salePrice, BigDecimal marketPrice, int stock) {
        return update(productId, merchantId, expectedVersion, categoryId, name, subtitle, brand, description, weightKg,
                skuCode, skuTitle, salePrice, marketPrice, stock, null);
    }

    @Transactional
    public Product update(UUID productId, UUID merchantId, long expectedVersion, UUID categoryId, String name, String subtitle, String brand,
                          String description, BigDecimal weightKg, String skuCode,
                          String skuTitle, BigDecimal salePrice, BigDecimal marketPrice, int stock, List<String> imageUrls) {
        Product product = repository.findByIdForUpdate(productId).orElseThrow();
        if (!product.merchantId().equals(merchantId)) throw new SecurityException("Product does not belong to merchant");
        if (product.version() != expectedVersion) throw new org.springframework.dao.OptimisticLockingFailureException("Product was modified by another request");
        var images = media.validateProductImages(merchantId, imageUrls, product.imageUrls());
        return repository.save(product.revise(categoryId, name, subtitle, brand, description, weightKg, skuCode, skuTitle, salePrice, marketPrice, stock).withImages(images));
    }
}
