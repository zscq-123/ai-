package com.zscq.mall.commerce.catalog.infrastructure;

import com.zscq.mall.commerce.catalog.domain.*;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
class CatalogRepositoryAdapter implements CatalogRepository {
    private final JpaCatalogRepository repository;
    CatalogRepositoryAdapter(JpaCatalogRepository repository) { this.repository = repository; }
    public Product save(Product product) { return repository.save(new ProductEntity(product)).toDomain(); }
    public List<Product> search(String query, UUID categoryId) { return repository.search(ProductStatus.ACTIVE, query, categoryId).stream().map(ProductEntity::toDomain).toList(); }
    public Optional<Product> findActiveById(UUID productId) { return repository.findByIdAndStatus(productId, ProductStatus.ACTIVE).map(ProductEntity::toDomain); }
    public Optional<Product> findById(UUID productId) { return repository.findById(productId).map(ProductEntity::toDomain); }
}
