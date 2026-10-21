package com.zscq.mall.commerce.media.infrastructure;

import com.zscq.mall.commerce.media.domain.ProductImage;
import com.zscq.mall.commerce.media.domain.ProductImageRepository;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
class JdbcProductImageRepository implements ProductImageRepository {
    private final JdbcTemplate jdbc;

    JdbcProductImageRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public boolean activeMerchantExists(UUID merchantId) {
        return Boolean.TRUE.equals(jdbc.queryForObject(
                "select exists(select 1 from merchants where id = ? and status = 'ACTIVE')", Boolean.class, merchantId));
    }

    public void save(ProductImage image) {
        jdbc.update("""
                insert into product_media(id, merchant_id, storage_key, content_type, width, height, size_bytes)
                values (?, ?, ?, ?, ?, ?, ?)
                """, image.id(), image.merchantId(), image.storageKey(), image.contentType(), image.width(), image.height(), image.sizeBytes());
    }

    public Optional<ProductImage> find(UUID id) {
        return jdbc.query("select * from product_media where id = ?", (row, number) -> new ProductImage(
                row.getObject("id", UUID.class), row.getObject("merchant_id", UUID.class), row.getString("storage_key"),
                row.getString("content_type"), row.getInt("width"), row.getInt("height"), row.getLong("size_bytes")), id).stream().findFirst();
    }
}
