package com.zscq.mall.commerce.support.application;

import com.zscq.mall.commerce.support.domain.FaqEntry;
import com.zscq.mall.commerce.support.domain.FaqKnowledgeRepository;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class FaqKnowledgeService {
    private static final int MAX_IMPORT_ROWS = 200;
    private final FaqKnowledgeRepository repository;

    public FaqKnowledgeService(FaqKnowledgeRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<FaqEntry> list(UUID merchantId) {
        return repository.findAll(merchantId);
    }

    @Transactional(readOnly = true)
    public List<FaqEntry> published(UUID merchantId) {
        return repository.findPublished(merchantId);
    }

    @Transactional
    public List<FaqEntry> importDrafts(UUID merchantId, List<FaqEntry.Draft> drafts) {
        if (drafts == null || drafts.isEmpty()) {
            throw new IllegalArgumentException("FAQ knowledge file is empty");
        }
        if (drafts.size() > MAX_IMPORT_ROWS) {
            throw new IllegalArgumentException("A single FAQ import supports at most 200 entries");
        }
        List<FaqEntry.Draft> normalized = drafts.stream().map(this::normalize).toList();
        return repository.importDrafts(merchantId, normalized);
    }

    @Transactional
    public FaqEntry publish(UUID id) {
        return repository.publish(id);
    }

    private FaqEntry.Draft normalize(FaqEntry.Draft draft) {
        if (draft == null) throw new IllegalArgumentException("FAQ entry cannot be null");
        String question = clean(draft.question(), "FAQ question", 2, 240);
        String answer = clean(draft.answer(), "FAQ answer", 1, 4_000);
        List<String> keywords = new LinkedHashSet<>(draft.keywords() == null ? List.<String>of()
                : draft.keywords().stream().map(String::trim).filter(value -> !value.isEmpty()).toList())
                .stream().limit(20).map(value -> value.length() > 40 ? value.substring(0, 40) : value)
                .toList();
        return new FaqEntry.Draft(question, answer, keywords, Math.max(0, draft.displayOrder()));
    }

    private String clean(String value, String label, int min, int max) {
        String cleaned = value == null ? "" : value.trim();
        if (cleaned.length() < min || cleaned.length() > max) {
            throw new IllegalArgumentException(label + " length must be between " + min + " and " + max);
        }
        return cleaned;
    }
}
