package com.zscq.mall.commerce.catalog.infrastructure;

import com.zscq.mall.commerce.catalog.domain.*;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
class CatalogRepositoryAdapter implements CatalogRepository {
    private final JpaCatalogRepository repository;
    private final org.springframework.jdbc.core.JdbcTemplate jdbc;
    CatalogRepositoryAdapter(JpaCatalogRepository repository, org.springframework.jdbc.core.JdbcTemplate jdbc) { this.repository = repository; this.jdbc = jdbc; }
    public Product save(Product product) {
        ProductEntity entity = new ProductEntity(product);
        repository.findById(product.id()).ifPresent(existing -> entity.sku.enabled = existing.sku.enabled);
        return repository.saveAndFlush(entity).toDomain();
    }
    public List<Product> search(String query, UUID categoryId) { return repository.search(ProductStatus.ACTIVE, query, categoryId).stream().map(ProductEntity::toDomain).toList(); }
    public Optional<Product> findActiveById(UUID productId) { return repository.findByIdAndStatus(productId, ProductStatus.ACTIVE).map(ProductEntity::toDomain); }
    public Optional<Product> findById(UUID productId) { return repository.findById(productId).map(ProductEntity::toDomain); }
    public Optional<Product> findByIdForUpdate(UUID productId) {
        // Match checkout's lock order: product first, then its SKU. Read the version only after acquiring the lock.
        var rows = jdbc.query("select id from products where id = ? for update", (row, index) -> row.getObject(1, UUID.class), productId);
        return rows.isEmpty() ? Optional.empty() : repository.findById(productId).map(ProductEntity::toDomain);
    }
    public List<Category> categories() {
        return jdbc.query("select id, parent_id, name, slug from categories where enabled = true order by sort_order, name",
                (row, index) -> new Category(row.getObject("id", UUID.class), row.getObject("parent_id", UUID.class), row.getString("name"), row.getString("slug")));
    }
}
