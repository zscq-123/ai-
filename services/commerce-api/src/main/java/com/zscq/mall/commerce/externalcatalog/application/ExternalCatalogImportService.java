package com.zscq.mall.commerce.externalcatalog.application;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogRepository;
import com.zscq.mall.commerce.externalcatalog.domain.LazadaUrl;
import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ExternalCatalogImportService {
    private static final int MAX_SYNC_BATCH = 20;
    private final List<ExternalCatalogGateway> gateways;
    private final ExternalCatalogRepository repository;

    public ExternalCatalogImportService(ExternalCatalogGateway gateway, ExternalCatalogRepository repository) {
        this(List.of(gateway), repository);
    }

    @Autowired
    public ExternalCatalogImportService(List<ExternalCatalogGateway> gateways, ExternalCatalogRepository repository) {
        this.gateways = List.copyOf(gateways);
        this.repository = repository;
    }

    @Transactional
    public ImportResult importLazada(List<String> rawUrls) {
        return importProducts(rawUrls, MAX_SYNC_BATCH, "DIRECT");
    }

    @Transactional
    public ImportResult importLazada(List<String> rawUrls, int limit) {
        return importProducts(rawUrls, limit, "DIRECT");
    }

    @Transactional
    public ImportResult importLazadaFromBrightData(List<String> rawUrls) {
        if (rawUrls != null && rawUrls.stream().map(LazadaUrl::validate).anyMatch(url -> "/".equals(url.getPath()))) {
            throw new IllegalArgumentException("The Bright Data route accepts product detail URLs only");
        }
        return importProducts(rawUrls, MAX_SYNC_BATCH, "BRIGHT_DATA");
    }

    private ImportResult importProducts(List<String> rawUrls, int limit, String provider) {
        if (rawUrls == null || rawUrls.isEmpty()) throw new IllegalArgumentException("At least one Lazada product URL is required");
        if (rawUrls.size() > MAX_SYNC_BATCH) throw new IllegalArgumentException("A synchronous import accepts at most 20 URLs");
        if (limit < 1 || limit > MAX_SYNC_BATCH) throw new IllegalArgumentException("Product limit must be between 1 and 20");

        List<URI> urls = rawUrls.stream().map(LazadaUrl::validate).distinct().toList();
        ExternalCatalogGateway gateway = gateways.stream().filter(candidate -> provider.equals(candidate.provider()))
                .findFirst().orElseThrow(() -> new IllegalStateException("Catalog provider is not configured: " + provider));
        List<ExternalCatalogProduct> fetched = gateway.fetchLazadaProducts(urls).stream().limit(limit).toList();
        List<ImportedItem> items = new ArrayList<>();
        int created = 0;
        int skipped = 0;
        for (ExternalCatalogProduct product : fetched) {
            ExternalCatalogRepository.UpsertedProduct saved = repository.upsert(product);
            if (saved.created()) created++;
            if (saved.skipped()) skipped++;
            items.add(new ImportedItem(saved.productId(), saved.merchantId(), product.externalProductId(), product.name(), saved.created(), saved.skipReason()));
        }
        return new ImportResult(urls.size(), fetched.size(), created, fetched.size() - created - skipped, skipped, Instant.now(),
                skipped > 0 && skipped == fetched.size() ? "UNCHANGED" : "STAGED_FOR_REVIEW", List.copyOf(items));
    }

    @Transactional
    public void publish(UUID productId) {
        if (!repository.publish(productId)) throw new java.util.NoSuchElementException("Staged external product not found");
    }

    public record ImportResult(int requested, int received, int created, int updated, int skipped, Instant completedAt, String state, List<ImportedItem> items) {}
    public record ImportedItem(UUID productId, UUID merchantId, String externalProductId, String name, boolean created, String skipReason) {}
}
