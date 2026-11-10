package com.zscq.mall.commerce.support.domain;

import java.util.List;
import java.util.UUID;

public interface FaqKnowledgeRepository {
    List<FaqEntry> findAll(UUID merchantId);
    List<FaqEntry> findPublished(UUID merchantId);
    List<FaqEntry> importDrafts(UUID merchantId, List<FaqEntry.Draft> drafts);
    FaqEntry publish(UUID id);
}
