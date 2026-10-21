package com.zscq.mall.commerce.externalcatalog.infrastructure;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetails;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetailsRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.json.JsonMapper;

@Repository
class JdbcExternalProductDetailsRepository implements ExternalProductDetailsRepository {
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private final JdbcTemplate jdbc;

    JdbcExternalProductDetailsRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public Optional<DraftSnapshot> findForUpdate(UUID productId) {
        return jdbc.query("""
                SELECT id, merchant_id, version, status, source_platform, external_product_id, source_url,
                       source_payload->>'provider' source_provider, brand, description, image_urls, source_image_url
                  FROM products WHERE id=? FOR UPDATE
                """, (row, index) -> new DraftSnapshot(row.getObject("id", UUID.class), row.getObject("merchant_id", UUID.class),
                row.getLong("version"), row.getString("status"), row.getString("source_platform"),
                row.getString("external_product_id"), row.getString("source_url"), row.getString("source_provider"),
                row.getString("brand"), row.getString("description"), images(row.getString("image_urls")), row.getString("source_image_url")),
                productId).stream().findFirst();
    }

    public long save(UUID productId, long expectedVersion, ExternalProductDetails details,
                     String brandToFill, String descriptionToFill, List<String> imagesToReplace) {
        var versions = jdbc.query("""
                UPDATE products SET source_detail_payload=?::jsonb,
                       brand=CASE WHEN ?::text IS NOT NULL AND brand IS NULL THEN ? ELSE brand END,
                       description=CASE WHEN ?::text IS NOT NULL AND description IS NULL THEN ? ELSE description END,
                       image_urls=CASE WHEN ?::jsonb IS NOT NULL THEN ?::jsonb ELSE image_urls END,
                       version=version+1, updated_at=CURRENT_TIMESTAMP
                 WHERE id=? AND version=? AND status='DRAFT'
                 RETURNING version
                """, (row, index) -> row.getLong("version"), JSON.writeValueAsString(details), brandToFill, brandToFill,
                descriptionToFill, descriptionToFill,
                imagesToReplace == null ? null : JSON.writeValueAsString(imagesToReplace),
                imagesToReplace == null ? null : JSON.writeValueAsString(imagesToReplace), productId, expectedVersion);
        if (versions.isEmpty()) throw new OptimisticLockingFailureException("商品已更新，请刷新后再补充详情");
        return versions.getFirst();
    }

    private static List<String> images(String json) {
        if (json == null) return null;
        var result = new ArrayList<String>();
        JSON.readTree(json).forEach(value -> result.add(value.asText()));
        return List.copyOf(result);
    }
}
