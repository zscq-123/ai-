package com.zscq.mall.commerce.catalog.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface CatalogRepository {
    Product save(Product product);
    List<Product> search(String query, UUID categoryId);
    Optional<Product> findActiveById(UUID productId);
    Optional<Product> findById(UUID productId);
    Optional<Product> findByIdForUpdate(UUID productId);
    List<Category> categories();
}
