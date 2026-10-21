package com.zscq.mall.commerce.storedesign.infrastructure;

import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import com.zscq.mall.commerce.storedesign.domain.PublishedStoreDesign;
import com.zscq.mall.commerce.storedesign.domain.StoreChannel;
import com.zscq.mall.commerce.storedesign.domain.StoreDesign;
import com.zscq.mall.commerce.storedesign.domain.StoreDesignRepository;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
class JdbcStoreDesignRepository implements StoreDesignRepository {
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    JdbcStoreDesignRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    @Override
    public Optional<String> activeMerchantName(UUID merchantId) {
        return jdbc.query("SELECT store_name FROM merchants WHERE id = ? AND status = 'ACTIVE'",
                (rs, row) -> rs.getString(1), merchantId).stream().findFirst();
    }

    @Override
    public Optional<StoreDesign> find(UUID merchantId, StoreChannel channel) {
        return jdbc.query("""
                SELECT merchant_id, channel, draft_version, published_version, draft_config,
                       published_config, updated_at, published_at
                FROM store_designs WHERE merchant_id = ? AND channel = ?
                """, this::mapDesign, merchantId, channel.name()).stream().findFirst();
    }

    @Override
    public Optional<PublishedStoreDesign> findPublished(UUID merchantId, StoreChannel channel) {
        return jdbc.query("""
                SELECT d.merchant_id, m.store_name, d.channel, d.published_version,
                       d.published_config, d.published_at
                FROM store_designs d
                JOIN merchants m ON m.id = d.merchant_id AND m.status = 'ACTIVE'
                WHERE d.merchant_id = ? AND d.channel = ? AND d.published_config IS NOT NULL
                """, (rs, row) -> new PublishedStoreDesign(
                        rs.getObject("merchant_id", UUID.class),
                        rs.getString("store_name"),
                        StoreChannel.valueOf(rs.getString("channel")),
                        rs.getLong("published_version"),
                        json(rs.getString("published_config")),
                        instant(rs.getTimestamp("published_at"))), merchantId, channel.name())
                .stream().findFirst();
    }

    @Override
    public StoreDesign saveDraft(UUID merchantId, StoreChannel channel, long expectedVersion, JsonNode config) {
        Optional<StoreDesign> existing = find(merchantId, channel);
        if (existing.isEmpty()) {
            if (expectedVersion != 0) throw new IllegalStateException("Draft changed in another session; reload before saving");
            jdbc.update("""
                    INSERT INTO store_designs(id, merchant_id, channel, draft_version, draft_config)
                    VALUES (?, ?, ?, 1, ?::jsonb)
                    """, UUID.randomUUID(), merchantId, channel.name(), config.toString());
        } else {
            int updated = jdbc.update("""
                    UPDATE store_designs SET draft_config = ?::jsonb,
                        draft_version = draft_version + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE merchant_id = ? AND channel = ? AND draft_version = ?
                    """, config.toString(), merchantId, channel.name(), expectedVersion);
            if (updated != 1) throw new IllegalStateException("Draft changed in another session; reload before saving");
        }
        return find(merchantId, channel).orElseThrow();
    }

    @Override
    public StoreDesign publish(UUID merchantId, StoreChannel channel) {
        int updated = jdbc.update("""
                UPDATE store_designs SET
                    published_config = draft_config,
                    published_version = draft_version,
                    published_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE merchant_id = ? AND channel = ?
                """, merchantId, channel.name());
        if (updated != 1) {
            throw new IllegalStateException("Store design draft was not found");
        }
        return find(merchantId, channel).orElseThrow();
    }

    private StoreDesign mapDesign(ResultSet rs, int row) throws SQLException {
        Number publishedVersion = (Number) rs.getObject("published_version");
        String published = rs.getString("published_config");
        return new StoreDesign(
                rs.getObject("merchant_id", UUID.class),
                StoreChannel.valueOf(rs.getString("channel")),
                rs.getLong("draft_version"),
                publishedVersion == null ? null : publishedVersion.longValue(),
                json(rs.getString("draft_config")),
                published == null ? null : json(published),
                instant(rs.getTimestamp("updated_at")),
                instant(rs.getTimestamp("published_at")));
    }

    private JsonNode json(String raw) {
        try {
            return objectMapper.readTree(raw);
        } catch (JacksonException exception) {
            throw new IllegalStateException("Stored design contains invalid JSON", exception);
        }
    }

    private Instant instant(Timestamp timestamp) {
        return timestamp == null ? null : timestamp.toInstant();
    }
}
