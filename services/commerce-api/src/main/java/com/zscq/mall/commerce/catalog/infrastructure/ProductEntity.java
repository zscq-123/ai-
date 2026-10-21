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
    String brand;
    @Column(columnDefinition = "text") String description;
    java.math.BigDecimal weightKg;
    @Enumerated(EnumType.STRING) ProductStatus status;
    Instant createdAt;
    Instant updatedAt;
    @Version long version;
    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
    @Column(columnDefinition = "jsonb") java.util.List<String> imageUrls;
    @Column(insertable = false, updatable = false) String sourceImageUrl;
    @Column(insertable = false, updatable = false) String sourceCurrency;
    @OneToOne(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.EAGER)
    ProductSkuEntity sku;
    protected ProductEntity() {}
    ProductEntity(Product p) {
        id=p.id(); merchantId=p.merchantId(); categoryId=p.categoryId(); name=p.name(); subtitle=p.subtitle();
        brand=p.brand(); description=p.description(); weightKg=p.weightKg();
        status=p.status(); createdAt=p.createdAt(); updatedAt=p.updatedAt(); version=p.version(); sku=new ProductSkuEntity(p, this);
        imageUrls=p.imageUrls(); sourceCurrency=p.currency();
    }
    Product toDomain() {
        var images = imageUrls != null ? imageUrls : sourceImageUrl != null && !sourceImageUrl.isBlank() ? java.util.List.of(sourceImageUrl) : java.util.List.<String>of();
        return new Product(id, merchantId, categoryId, name, subtitle, brand, description, weightKg, status,
                sku.id, sku.skuCode, sku.title, sku.salePrice, sku.marketPrice, sku.availableStock, version, createdAt, updatedAt,
                images, null, sourceCurrency);
    }
}
