package com.zscq.mall.commerce.support.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.support.domain.FaqEntry;
import com.zscq.mall.commerce.support.domain.FaqKnowledgeRepository;
import com.zscq.mall.commerce.support.domain.FaqStatus;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class FaqKnowledgeServiceTest {
    private final MemoryRepository repository = new MemoryRepository();
    private final FaqKnowledgeService service = new FaqKnowledgeService(repository);

    @Test
    void importsNormalizedEntriesAsDraftsThenPublishes() {
        List<FaqEntry> imported = service.importDrafts(null, List.of(
                new FaqEntry.Draft("  能开发票吗？ ", " 以商品说明为准。 ",
                        List.of("发票", " 发票 ", "开票"), -1)));

        assertThat(imported).hasSize(1);
        assertThat(imported.getFirst().question()).isEqualTo("能开发票吗？");
        assertThat(imported.getFirst().keywords()).containsExactly("发票", "开票");
        assertThat(imported.getFirst().displayOrder()).isZero();
        assertThat(imported.getFirst().status()).isEqualTo(FaqStatus.DRAFT);

        FaqEntry published = service.publish(imported.getFirst().id());
        assertThat(published.status()).isEqualTo(FaqStatus.PUBLISHED);
    }

    @Test
    void rejectsEmptyKnowledgeImport() {
        assertThatThrownBy(() -> service.importDrafts(null, List.of()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("empty");
    }

    private static final class MemoryRepository implements FaqKnowledgeRepository {
        private final List<FaqEntry> entries = new ArrayList<>();

        @Override public List<FaqEntry> findAll(UUID merchantId) { return List.copyOf(entries); }
        @Override public List<FaqEntry> findPublished(UUID merchantId) {
            return entries.stream().filter(entry -> entry.status() == FaqStatus.PUBLISHED).toList();
        }
        @Override public List<FaqEntry> importDrafts(UUID merchantId, List<FaqEntry.Draft> drafts) {
            entries.clear();
            Instant now = Instant.parse("2026-11-02T00:00:00Z");
            drafts.forEach(draft -> entries.add(new FaqEntry(UUID.randomUUID(), merchantId,
                    draft.question(), draft.answer(), draft.keywords(), FaqStatus.DRAFT,
                    draft.displayOrder(), now, now, null)));
            return List.copyOf(entries);
        }
        @Override public FaqEntry publish(UUID id) {
            FaqEntry current = entries.stream().filter(entry -> entry.id().equals(id)).findFirst().orElseThrow();
            FaqEntry published = new FaqEntry(current.id(), current.merchantId(), current.question(),
                    current.answer(), current.keywords(), FaqStatus.PUBLISHED, current.displayOrder(),
                    current.createdAt(), current.updatedAt(), Instant.parse("2026-11-02T00:00:00Z"));
            entries.set(entries.indexOf(current), published);
            return published;
        }
    }
}
