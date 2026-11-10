package com.zscq.mall.commerce.support.infrastructure;

import com.zscq.mall.commerce.support.domain.FaqEntry;
import com.zscq.mall.commerce.support.domain.FaqKnowledgeRepository;
import com.zscq.mall.commerce.support.domain.FaqStatus;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
class JdbcFaqKnowledgeRepository implements FaqKnowledgeRepository {
    private final JdbcTemplate jdbc;

    JdbcFaqKnowledgeRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<FaqEntry> findAll(UUID merchantId) {
        if (merchantId == null) {
            return jdbc.query(selectBase() + " WHERE merchant_id IS NULL ORDER BY display_order, updated_at DESC", this::map);
        }
        return jdbc.query(selectBase() + " WHERE merchant_id = ? ORDER BY display_order, updated_at DESC", this::map, merchantId);
    }

    @Override
    public List<FaqEntry> findPublished(UUID merchantId) {
        if (merchantId == null) {
            return jdbc.query(selectBase() + " WHERE merchant_id IS NULL AND status = 'PUBLISHED' ORDER BY display_order, updated_at DESC", this::map);
        }
        return jdbc.query(selectBase() + " WHERE status = 'PUBLISHED' AND (merchant_id = ? OR merchant_id IS NULL) "
                + "ORDER BY CASE WHEN merchant_id = ? THEN 0 ELSE 1 END, display_order, updated_at DESC", this::map, merchantId, merchantId);
    }

    @Override
    public List<FaqEntry> importDrafts(UUID merchantId, List<FaqEntry.Draft> drafts) {
        for (FaqEntry.Draft draft : drafts) {
            if (merchantId == null) {
                jdbc.update("DELETE FROM support_faq_entries WHERE merchant_id IS NULL "
                        + "AND status = 'DRAFT' AND lower(question) = lower(?)", draft.question());
            } else {
                jdbc.update("DELETE FROM support_faq_entries WHERE merchant_id = ? "
                        + "AND status = 'DRAFT' AND lower(question) = lower(?)", merchantId, draft.question());
            }
            jdbc.update("""
                    INSERT INTO support_faq_entries(
                        id, merchant_id, question, answer, keywords, status, display_order
                    ) VALUES (?, ?, ?, ?, ?, 'DRAFT', ?)
                    """, UUID.randomUUID(), merchantId, draft.question(), draft.answer(),
                    String.join("|", draft.keywords()), draft.displayOrder());
        }
        return findAll(merchantId);
    }

    @Override
    public FaqEntry publish(UUID id) {
        jdbc.update("""
                UPDATE support_faq_entries existing
                SET status = 'ARCHIVED', updated_at = CURRENT_TIMESTAMP
                WHERE existing.id <> ? AND existing.status = 'PUBLISHED'
                  AND lower(existing.question) = lower(
                      (SELECT candidate.question FROM support_faq_entries candidate WHERE candidate.id = ?)
                  )
                  AND existing.merchant_id IS NOT DISTINCT FROM (
                      SELECT candidate.merchant_id FROM support_faq_entries candidate WHERE candidate.id = ?
                  )
                """, id, id, id);
        int updated = jdbc.update("""
                UPDATE support_faq_entries
                SET status = 'PUBLISHED', published_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, id);
        if (updated != 1) throw new NoSuchElementException("FAQ entry not found");
        return jdbc.query(selectBase() + " WHERE id = ?", this::map, id).stream().findFirst().orElseThrow();
    }

    private String selectBase() {
        return "SELECT id, merchant_id, question, answer, keywords, status, display_order, "
                + "created_at, updated_at, published_at FROM support_faq_entries";
    }

    private FaqEntry map(ResultSet rs, int row) throws SQLException {
        String rawKeywords = rs.getString("keywords");
        List<String> keywords = rawKeywords == null || rawKeywords.isBlank()
                ? List.of() : Arrays.stream(rawKeywords.split("\\|"))
                        .map(String::trim).filter(value -> !value.isEmpty()).toList();
        return new FaqEntry(
                rs.getObject("id", UUID.class),
                rs.getObject("merchant_id", UUID.class),
                rs.getString("question"),
                rs.getString("answer"),
                keywords,
                FaqStatus.valueOf(rs.getString("status")),
                rs.getInt("display_order"),
                instant(rs.getTimestamp("created_at")),
                instant(rs.getTimestamp("updated_at")),
                instant(rs.getTimestamp("published_at")));
    }

    private Instant instant(Timestamp timestamp) {
        return timestamp == null ? null : timestamp.toInstant();
    }
}
