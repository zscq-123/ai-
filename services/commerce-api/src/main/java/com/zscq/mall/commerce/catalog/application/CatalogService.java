package com.zscq.mall.commerce.catalog.application;

import com.zscq.mall.commerce.catalog.domain.*;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CatalogService {
    private final CatalogRepository repository;
    public CatalogService(CatalogRepository repository) { this.repository = repository; }

    @Transactional
    public Product create(UUID merchantId, UUID categoryId, String name, String subtitle, String brand,
                          String description, BigDecimal weightKg, String skuCode,
                          String skuTitle, BigDecimal salePrice, BigDecimal marketPrice, int stock) {
        return repository.save(Product.draft(merchantId, categoryId, name, subtitle, brand, description, weightKg, skuCode, skuTitle, salePrice, marketPrice, stock));
    }

    @Transactional(readOnly = true)
    public List<Product> search(String query, UUID categoryId) { return repository.search(query, categoryId); }

    @Transactional(readOnly = true)
    public Product getActive(UUID productId) {
        return repository.findActiveById(productId).orElseThrow();
    }

    @Transactional(readOnly = true)
    public Product get(UUID productId) {
        return repository.findById(productId).orElseThrow();
    }

    @Transactional
    public Product update(UUID productId, UUID merchantId, long expectedVersion, UUID categoryId, String name, String subtitle, String brand,
                          String description, BigDecimal weightKg, String skuCode,
                          String skuTitle, BigDecimal salePrice, BigDecimal marketPrice, int stock) {
        Product product = repository.findById(productId).orElseThrow();
        if (!product.merchantId().equals(merchantId)) throw new SecurityException("Product does not belong to merchant");
        if (product.version() != expectedVersion) throw new org.springframework.dao.OptimisticLockingFailureException("Product was modified by another request");
        return repository.save(product.revise(categoryId, name, subtitle, brand, description, weightKg, skuCode, skuTitle, salePrice, marketPrice, stock));
    }
}
