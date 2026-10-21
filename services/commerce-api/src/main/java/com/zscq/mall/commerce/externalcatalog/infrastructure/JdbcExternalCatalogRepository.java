package com.zscq.mall.commerce.externalcatalog.infrastructure;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogRepository;
import java.nio.charset.StandardCharsets;
import java.sql.Types;
import java.time.OffsetDateTime;
import java.util.Locale;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class JdbcExternalCatalogRepository implements ExternalCatalogRepository {
    private final JdbcTemplate jdbc;

    public JdbcExternalCatalogRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public UpsertedProduct upsert(ExternalCatalogProduct product) {
        UUID merchantId = deterministicUuid("merchant", product.sourcePlatform() + ":" + product.sellerName());
        String externalLicense = "EXT-" + product.sourcePlatform() + "-" + merchantId.toString().replace("-", "").substring(0, 24);
        jdbc.update("""
                INSERT INTO merchants (id, legal_name, store_name, contact_name, contact_phone, business_license_no, status, created_at, reviewed_at)
                VALUES (?, ?, ?, 'External catalog import', 'N/A', ?, 'PENDING_REVIEW', CURRENT_TIMESTAMP, NULL)
                ON CONFLICT (business_license_no) DO UPDATE SET store_name = EXCLUDED.store_name
                """, merchantId, truncate(product.sellerName(), 160), truncate(product.sellerName(), 100), externalLicense);

        UUID productId = deterministicUuid("product", product.sourcePlatform() + ":" + product.externalProductId());
        Boolean existed = jdbc.queryForObject("SELECT EXISTS (SELECT 1 FROM products WHERE source_platform = ? AND external_product_id = ?)",
                Boolean.class, product.sourcePlatform(), product.externalProductId());
        String payload = product.sourcePayload();
        jdbc.update(connection -> {
            var statement = connection.prepareStatement("""
                    INSERT INTO products (
                        id, merchant_id, category_id, name, subtitle, brand, description, weight_kg, status,
                        created_at, updated_at, source_platform, external_product_id, source_url,
                        source_image_url, source_currency, source_sold_count, source_rating,
                        source_payload, source_last_synced_at)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, 0, 'DRAFT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                        ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?)
                    ON CONFLICT (source_platform, external_product_id) WHERE source_platform IS NOT NULL AND external_product_id IS NOT NULL
                    DO UPDATE SET
                        merchant_id = EXCLUDED.merchant_id,
                        name = EXCLUDED.name,
                        subtitle = EXCLUDED.subtitle,
                        brand = EXCLUDED.brand,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP,
                        source_url = EXCLUDED.source_url,
                        source_image_url = EXCLUDED.source_image_url,
                        source_currency = EXCLUDED.source_currency,
                        source_sold_count = EXCLUDED.source_sold_count,
                        source_rating = EXCLUDED.source_rating,
                        source_payload = EXCLUDED.source_payload,
                        source_last_synced_at = EXCLUDED.source_last_synced_at
                    """);
            int index = 1;
            statement.setObject(index++, productId);
            statement.setObject(index++, merchantId);
            statement.setString(index++, truncate(product.name(), 180));
            setNullable(statement, index++, truncate(product.subtitle(), 300), Types.VARCHAR);
            setNullable(statement, index++, truncate(product.brand(), 100), Types.VARCHAR);
            setNullable(statement, index++, product.description(), Types.VARCHAR);
            statement.setString(index++, product.sourcePlatform());
            statement.setString(index++, truncate(product.externalProductId(), 180));
            statement.setString(index++, product.sourceUrl());
            setNullable(statement, index++, product.imageUrl(), Types.VARCHAR);
            statement.setString(index++, truncate(product.currency(), 12));
            statement.setLong(index++, product.soldCount());
            setNullable(statement, index++, product.rating(), Types.NUMERIC);
            statement.setString(index++, payload);
            statement.setObject(index, OffsetDateTime.now());
            return statement;
        });

        UUID skuId = deterministicUuid("sku", product.sourcePlatform() + ":" + product.externalProductId());
        String skuCode = ("LZ-" + productId.toString()).toUpperCase(Locale.ROOT);
        jdbc.update("""
                INSERT INTO product_skus (id, product_id, sku_code, title, sale_price, market_price, available_stock, enabled, external_sku_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, FALSE, ?)
                ON CONFLICT (sku_code) DO UPDATE SET
                    title = EXCLUDED.title,
                    sale_price = EXCLUDED.sale_price,
                    market_price = EXCLUDED.market_price,
                    available_stock = EXCLUDED.available_stock,
                    external_sku_id = EXCLUDED.external_sku_id
                """, skuId, productId, skuCode, truncate(product.name(), 160), product.salePrice(), product.marketPrice(),
                product.availableStock(), truncate(product.externalSkuId(), 180));
        return new UpsertedProduct(productId, merchantId, !Boolean.TRUE.equals(existed));
    }

    @Override
    public boolean publish(UUID productId) {
        int changed = jdbc.update("""
                WITH candidate AS (
                    SELECT merchant_id FROM products
                     WHERE id = ? AND source_platform IS NOT NULL AND status IN ('DRAFT', 'PENDING_REVIEW')
                ), merchant_update AS (
                    UPDATE merchants SET status='ACTIVE', reviewed_at=CURRENT_TIMESTAMP
                     WHERE id=(SELECT merchant_id FROM candidate) AND status='PENDING_REVIEW'
                ), product_update AS (
                    UPDATE products SET status='ACTIVE', updated_at=CURRENT_TIMESTAMP
                     WHERE id=? AND EXISTS (SELECT 1 FROM candidate)
                    RETURNING id
                )
                UPDATE product_skus SET enabled=TRUE
                 WHERE product_id IN (SELECT id FROM product_update)
                """, productId, productId);
        return changed > 0;
    }

    private static UUID deterministicUuid(String type, String value) {
        return UUID.nameUUIDFromBytes(("nova:" + type + ":" + value).getBytes(StandardCharsets.UTF_8));
    }

    private static String truncate(String value, int max) {
        if (value == null) return null;
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static void setNullable(java.sql.PreparedStatement statement, int index, Object value, int sqlType) throws java.sql.SQLException {
        if (value == null) statement.setNull(index, sqlType);
        else statement.setObject(index, value, sqlType);
    }
}
