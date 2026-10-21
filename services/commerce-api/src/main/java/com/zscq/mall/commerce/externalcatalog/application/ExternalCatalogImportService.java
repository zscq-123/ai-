package com.zscq.mall.commerce.externalcatalog.application;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogRepository;
import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ExternalCatalogImportService {
    private static final int MAX_SYNC_BATCH = 20;
    private final ExternalCatalogGateway gateway;
    private final ExternalCatalogRepository repository;

    public ExternalCatalogImportService(ExternalCatalogGateway gateway, ExternalCatalogRepository repository) {
        this.gateway = gateway;
        this.repository = repository;
    }

    @Transactional
    public ImportResult importLazada(List<String> rawUrls) {
        if (rawUrls == null || rawUrls.isEmpty()) throw new IllegalArgumentException("At least one Lazada product URL is required");
        if (rawUrls.size() > MAX_SYNC_BATCH) throw new IllegalArgumentException("A synchronous import accepts at most 20 URLs");

        List<URI> urls = rawUrls.stream().map(this::validatedLazadaUrl).distinct().toList();
        List<ExternalCatalogProduct> fetched = gateway.fetchLazadaProducts(urls);
        List<ImportedItem> items = new ArrayList<>();
        int created = 0;
        for (ExternalCatalogProduct product : fetched) {
            ExternalCatalogRepository.UpsertedProduct saved = repository.upsert(product);
            if (saved.created()) created++;
            items.add(new ImportedItem(saved.productId(), saved.merchantId(), product.externalProductId(), product.name(), saved.created()));
        }
        return new ImportResult(urls.size(), fetched.size(), created, fetched.size() - created, Instant.now(), List.copyOf(items));
    }

    @Transactional
    public void publish(UUID productId) {
        if (!repository.publish(productId)) throw new java.util.NoSuchElementException("Staged external product not found");
    }

    private URI validatedLazadaUrl(String rawUrl) {
        URI uri;
        try {
            uri = URI.create(rawUrl == null ? "" : rawUrl.trim());
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException("Invalid Lazada product URL", exception);
        }
        String host = uri.getHost();
        if (!"https".equalsIgnoreCase(uri.getScheme()) || host == null || !isLazadaHost(host)) {
            throw new IllegalArgumentException("Only HTTPS Lazada product URLs are accepted");
        }
        return uri;
    }

    private boolean isLazadaHost(String rawHost) {
        String host = rawHost.toLowerCase(Locale.ROOT);
        return host.equals("lazada.sg") || host.endsWith(".lazada.sg")
                || host.equals("lazada.com.my") || host.endsWith(".lazada.com.my")
                || host.equals("lazada.co.th") || host.endsWith(".lazada.co.th")
                || host.equals("lazada.vn") || host.endsWith(".lazada.vn")
                || host.equals("lazada.com.ph") || host.endsWith(".lazada.com.ph")
                || host.equals("lazada.co.id") || host.endsWith(".lazada.co.id");
    }

    public record ImportResult(int requested, int received, int created, int updated, Instant completedAt, String state, List<ImportedItem> items) {
        public ImportResult(int requested, int received, int created, int updated, Instant completedAt, List<ImportedItem> items) {
            this(requested, received, created, updated, completedAt, "STAGED_FOR_REVIEW", items);
        }
    }
    public record ImportedItem(UUID productId, UUID merchantId, String externalProductId, String name, boolean created) {}
}
