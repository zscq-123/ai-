package com.zscq.mall.commerce.support.api;

import com.zscq.mall.commerce.support.application.FaqKnowledgeService;
import com.zscq.mall.commerce.support.domain.FaqEntry;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class FaqKnowledgeController {
    private final FaqKnowledgeService service;

    public FaqKnowledgeController(FaqKnowledgeService service) {
        this.service = service;
    }

    @GetMapping("/api/public/support/faqs")
    List<FaqEntry> published(@RequestParam(required = false) UUID merchantId) {
        return service.published(merchantId);
    }

    @GetMapping("/api/admin/support/faqs")
    List<FaqEntry> list(@RequestParam(required = false) UUID merchantId) {
        return service.list(merchantId);
    }

    @PostMapping("/api/admin/support/faqs/import")
    List<FaqEntry> importDrafts(@RequestParam(required = false) UUID merchantId,
                                @Valid @RequestBody ImportRequest request) {
        List<FaqEntry.Draft> drafts = request.entries().stream()
                .map(item -> new FaqEntry.Draft(item.question(), item.answer(), item.keywords(), item.displayOrder()))
                .toList();
        return service.importDrafts(merchantId, drafts);
    }

    @PostMapping("/api/admin/support/faqs/{id}/publish")
    FaqEntry publish(@PathVariable UUID id) {
        return service.publish(id);
    }

    public record ImportRequest(@NotNull @Size(min = 1, max = 200) List<@Valid ImportItem> entries) { }

    public record ImportItem(
            @NotBlank @Size(max = 240) String question,
            @NotBlank @Size(max = 4_000) String answer,
            @Size(max = 20) List<@Size(max = 40) String> keywords,
            int displayOrder) { }
}
