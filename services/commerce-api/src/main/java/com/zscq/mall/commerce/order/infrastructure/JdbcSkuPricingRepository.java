package com.zscq.mall.commerce.order.infrastructure;
import com.zscq.mall.commerce.order.domain.*;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSkuPricingRepository implements SkuPricingRepository {
    private final JdbcClient jdbc;
    JdbcSkuPricingRepository(JdbcClient jdbc) { this.jdbc=jdbc; }
    public Optional<SkuSnapshot> find(UUID skuId) {
        return jdbc.sql("select s.id,p.merchant_id,p.name,s.title,s.sale_price,s.available_stock from product_skus s join products p on p.id=s.product_id where s.id=:id and s.enabled=true and p.status='ACTIVE'")
                .param("id",skuId).query((rs,row)->new SkuSnapshot(rs.getObject(1,UUID.class),rs.getObject(2,UUID.class),rs.getString(3),rs.getString(4),rs.getBigDecimal(5),rs.getInt(6))).optional();
    }

    public Optional<SkuSnapshot> reserve(UUID skuId, int quantity) {
        if (quantity <= 0) throw new IllegalArgumentException("Quantity must be positive");
        return jdbc.sql("""
                update product_skus s
                   set available_stock = s.available_stock - :quantity
                  from products p
                 where s.id = :id
                   and p.id = s.product_id
                   and s.enabled = true
                   and p.status = 'ACTIVE'
                   and s.available_stock >= :quantity
                returning s.id, p.merchant_id, p.name, s.title, s.sale_price, s.available_stock
                """)
                .param("id", skuId).param("quantity", quantity)
                .query((rs,row)->new SkuSnapshot(rs.getObject(1,UUID.class),rs.getObject(2,UUID.class),rs.getString(3),rs.getString(4),rs.getBigDecimal(5),rs.getInt(6)))
                .optional();
    }
}
