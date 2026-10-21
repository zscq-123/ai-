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
import tools.jackson.databind.json.JsonMapper;

@Repository
public class JdbcExternalCatalogRepository implements ExternalCatalogRepository {
    private final JdbcTemplate jdbc;

    public JdbcExternalCatalogRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public UpsertedProduct upsert(ExternalCatalogProduct product) {
        // Keep published / review-in-progress products untouched; lock before deciding so a
        // concurrent publish cannot race the import and overwrite live catalog edits.
        var existingRows = jdbc.query("SELECT id, merchant_id, status FROM products WHERE source_platform=? AND external_product_id=? FOR UPDATE",
                (row, index) -> new ExistingProduct(row.getObject("id", UUID.class), row.getObject("merchant_id", UUID.class), row.getString("status")),
                product.sourcePlatform(), product.externalProductId());
        ExistingProduct existing = existingRows.isEmpty() ? null : existingRows.getFirst();
        if (existing != null && !"DRAFT".equals(existing.status())) return skipped(existing);
        UUID merchantId = existing == null ? deterministicUuid("merchant", product.sourcePlatform() + ":" + product.sellerName()) : existing.merchantId();
        String externalLicense = "EXT-" + product.sourcePlatform() + "-" + merchantId.toString().replace("-", "").substring(0, 24);
        if (existing == null) jdbc.update("""
                INSERT INTO merchants (id, legal_name, store_name, contact_name, contact_phone, business_license_no, status, created_at, reviewed_at)
                VALUES (?, ?, ?, 'External catalog import', 'N/A', ?, 'PENDING_REVIEW', CURRENT_TIMESTAMP, NULL)
                ON CONFLICT (business_license_no) DO UPDATE SET store_name = EXCLUDED.store_name
                """, merchantId, truncate(product.sellerName(), 160), truncate(product.sellerName(), 100), externalLicense);

        UUID productId = existing == null ? deterministicUuid("product", product.sourcePlatform() + ":" + product.externalProductId()) : existing.id();
        String payload = product.sourcePayload();
        var savedRows = jdbc.query(connection -> {
            var statement = connection.prepareStatement("""
                    INSERT INTO products (
                        id, merchant_id, category_id, name, subtitle, brand, description, weight_kg, status,
                        created_at, updated_at, source_platform, external_product_id, source_url,
                        source_image_url, source_currency, source_sold_count, source_rating,
                        source_payload, source_last_synced_at, image_urls)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, 0, 'DRAFT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                        ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?::jsonb)
                    ON CONFLICT (source_platform, external_product_id) WHERE source_platform IS NOT NULL AND external_product_id IS NOT NULL
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        subtitle = EXCLUDED.subtitle,
                        brand = COALESCE(EXCLUDED.brand, products.brand),
                        description = COALESCE(EXCLUDED.description, products.description),
                        status = 'DRAFT',
                        version = products.version + 1,
                        updated_at = CURRENT_TIMESTAMP,
                        source_url = EXCLUDED.source_url,
                        source_image_url = EXCLUDED.source_image_url,
                        source_currency = EXCLUDED.source_currency,
                        source_sold_count = EXCLUDED.source_sold_count,
                        source_rating = EXCLUDED.source_rating,
                        source_payload = EXCLUDED.source_payload,
                        source_last_synced_at = EXCLUDED.source_last_synced_at,
                        image_urls = COALESCE(products.image_urls, EXCLUDED.image_urls)
                    WHERE products.status = 'DRAFT'
                    RETURNING id, merchant_id, (xmax = 0) AS inserted
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
            statement.setObject(index++, OffsetDateTime.now());
            statement.setString(index, product.imageUrl() == null ? null
                    : JsonMapper.builder().build().writeValueAsString(java.util.List.of(product.imageUrl())));
            return statement;
        }, (row, index) -> new UpsertedProduct(row.getObject("id", UUID.class),
                row.getObject("merchant_id", UUID.class), row.getBoolean("inserted")));
        if (savedRows.isEmpty()) {
            var current = jdbc.queryForObject("SELECT id, merchant_id, status FROM products WHERE source_platform=? AND external_product_id=?",
                    (row, index) -> new ExistingProduct(row.getObject("id", UUID.class), row.getObject("merchant_id", UUID.class), row.getString("status")),
                    product.sourcePlatform(), product.externalProductId());
            return skipped(current);
        }

        UUID savedProductId = savedRows.getFirst().productId();
        synchronizeSku(savedProductId, product);
        return savedRows.getFirst();
    }

    void synchronizeSku(UUID savedProductId, ExternalCatalogProduct product) {
        var existingSkuIds = jdbc.query("SELECT id FROM product_skus WHERE product_id=? ORDER BY id FOR UPDATE",
                (row, index) -> row.getObject("id", UUID.class), savedProductId);
        if (existingSkuIds.size() > 1) {
            throw new IllegalStateException("External product has multiple SKUs; map the source SKU explicitly before resyncing");
        }
        if (!existingSkuIds.isEmpty()) {
            // A merchant can edit sku_code; identity and the one-product/one-source-SKU relation remain stable.
            jdbc.update("""
                    UPDATE product_skus SET title=?, sale_price=?, market_price=?, available_stock=?,
                        enabled=FALSE, external_sku_id=?
                     WHERE id=?
                    """, truncate(product.name(), 160), product.salePrice(), product.marketPrice(),
                    product.availableStock(), truncate(product.externalSkuId(), 180), existingSkuIds.getFirst());
            return;
        }
        UUID skuId = deterministicUuid("sku", product.sourcePlatform() + ":" + product.externalProductId());
        String skuCode = ("LZ-" + savedProductId.toString()).toUpperCase(Locale.ROOT);
        jdbc.update("""
                INSERT INTO product_skus (id, product_id, sku_code, title, sale_price, market_price, available_stock, enabled, external_sku_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, FALSE, ?)
                """, skuId, savedProductId, skuCode, truncate(product.name(), 160), product.salePrice(), product.marketPrice(),
                product.availableStock(), truncate(product.externalSkuId(), 180));
    }

    private static UpsertedProduct skipped(ExistingProduct product) {
        return new UpsertedProduct(product.id(), product.merchantId(), false,
                "Product is " + product.status() + "; retained existing content. Move it to draft explicitly before resyncing.");
    }

    private record ExistingProduct(UUID id, UUID merchantId, String status) {}

    @Override
    public boolean publish(UUID productId) {
        // Match seller editing / stock reservation: lock the product before touching its SKUs.
        var merchants = jdbc.query("""
                SELECT merchant_id FROM products
                 WHERE id=? AND source_platform IS NOT NULL AND status IN ('DRAFT', 'PENDING_REVIEW')
                 FOR UPDATE
                """, (row, index) -> row.getObject("merchant_id", UUID.class), productId);
        if (merchants.isEmpty()) return false;
        jdbc.update("UPDATE merchants SET status='ACTIVE', reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='PENDING_REVIEW'",
                merchants.getFirst());
        jdbc.update("UPDATE products SET status='ACTIVE', version=version+1, updated_at=CURRENT_TIMESTAMP WHERE id=?", productId);
        int changed = jdbc.update("UPDATE product_skus SET enabled=TRUE WHERE product_id=?", productId);
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
