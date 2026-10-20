package com.zscq.mall.commerce.catalog.infrastructure;

import com.zscq.mall.commerce.catalog.domain.*;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "products")
class ProductEntity {
    @Id UUID id;
    UUID merchantId;
    UUID categoryId;
    String name;
    String subtitle;
    @Enumerated(EnumType.STRING) ProductStatus status;
    Instant createdAt;
    Instant updatedAt;
    @OneToOne(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.EAGER)
    ProductSkuEntity sku;
    protected ProductEntity() {}
    ProductEntity(Product p) {
        id=p.id(); merchantId=p.merchantId(); categoryId=p.categoryId(); name=p.name(); subtitle=p.subtitle();
        status=p.status(); createdAt=p.createdAt(); updatedAt=p.updatedAt(); sku=new ProductSkuEntity(p, this);
    }
    Product toDomain() { return new Product(id, merchantId, categoryId, name, subtitle, status, sku.id, sku.skuCode, sku.title, sku.salePrice, sku.marketPrice, sku.availableStock, createdAt, updatedAt); }
}
