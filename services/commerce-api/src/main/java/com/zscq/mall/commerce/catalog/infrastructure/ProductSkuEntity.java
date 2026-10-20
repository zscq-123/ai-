package com.zscq.mall.commerce.catalog.infrastructure;

import com.zscq.mall.commerce.catalog.domain.Product;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "product_skus")
class ProductSkuEntity {
    @Id UUID id;
    @OneToOne(fetch = FetchType.LAZY) @JoinColumn(name = "product_id") ProductEntity product;
    String skuCode;
    String title;
    BigDecimal salePrice;
    BigDecimal marketPrice;
    int availableStock;
    boolean enabled = true;
    protected ProductSkuEntity() {}
    ProductSkuEntity(Product p, ProductEntity product) { id=p.skuId(); this.product=product; skuCode=p.skuCode(); title=p.skuTitle(); salePrice=p.salePrice(); marketPrice=p.marketPrice(); availableStock=p.availableStock(); }
}
