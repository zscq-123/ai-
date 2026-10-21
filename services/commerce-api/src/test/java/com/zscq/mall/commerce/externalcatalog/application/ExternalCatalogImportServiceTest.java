package com.zscq.mall.commerce.externalcatalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogRepository;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ExternalCatalogImportServiceTest {
    @Test
    void importsOnlyValidatedLazadaUrlsAndReportsCreatedVsUpdated() {
        ExternalCatalogProduct product = new ExternalCatalogProduct(
                "LAZADA", "P-1", "S-1", "https://www.lazada.sg/products/p-i1.html", "Product",
                null, null, null, "Seller", new BigDecimal("10.00"), null, "SGD", 1, 0, null, null, "{}");
        var gateway = new FixedGateway(product);
        var repository = new CountingRepository();
        var service = new ExternalCatalogImportService(gateway, repository);

        var first = service.importLazada(List.of(product.sourceUrl()));
        var second = service.importLazada(List.of(product.sourceUrl()));

        assertThat(first.created()).isEqualTo(1);
        assertThat(first.state()).isEqualTo("STAGED_FOR_REVIEW");
        assertThat(first.updated()).isZero();
        assertThat(second.created()).isZero();
        assertThat(second.updated()).isEqualTo(1);
    }

    @Test
    void rejectsNonLazadaAndNonHttpsUrlsBeforeCallingProvider() {
        var service = new ExternalCatalogImportService(urls -> List.of(), new ExternalCatalogRepository() {
            public UpsertedProduct upsert(ExternalCatalogProduct product) { return null; }
            public boolean publish(UUID productId) { return true; }
        });

        assertThatThrownBy(() -> service.importLazada(List.of("http://www.lazada.sg/products/p-i1.html")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> service.importLazada(List.of("https://example.com/products/p-i1.html")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void selectsDirectByDefaultAndOnlyUsesBrightDataWhenExplicitlyRequested() {
        var directCalls = new java.util.concurrent.atomic.AtomicInteger();
        var brightCalls = new java.util.concurrent.atomic.AtomicInteger();
        var direct = (com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway) urls -> {
            directCalls.incrementAndGet(); return List.of();
        };
        var bright = new com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway() {
            public String provider() { return "BRIGHT_DATA"; }
            public List<ExternalCatalogProduct> fetchLazadaProducts(List<java.net.URI> urls) {
                brightCalls.incrementAndGet(); return List.of();
            }
        };
        var service = new ExternalCatalogImportService(List.of(direct, bright), new CountingRepository());
        service.importLazada(List.of("https://www.lazada.sg/"), 3);
        assertThat(directCalls.get()).isEqualTo(1);
        assertThat(brightCalls.get()).isZero();
        service.importLazadaFromBrightData(List.of("https://www.lazada.sg/products/p-i1.html"));
        assertThat(brightCalls.get()).isEqualTo(1);
    }

    @Test
    void reportsSkippedPublishedProductsWithoutCountingThemAsUpdates() {
        ExternalCatalogProduct product = new ExternalCatalogProduct("LAZADA", "SG:1", "S-1",
                "https://www.lazada.sg/products/p-i1.html", "Product", null, null, null, "Seller",
                new BigDecimal("10.00"), null, "SGD", 1, 0, null, null, "{}");
        var repository = new ExternalCatalogRepository() {
            public UpsertedProduct upsert(ExternalCatalogProduct source) {
                return new UpsertedProduct(UUID.randomUUID(), UUID.randomUUID(), false, "Product is ACTIVE; retained existing content");
            }
            public boolean publish(UUID productId) { return false; }
        };
        var result = new ExternalCatalogImportService(new FixedGateway(product), repository)
                .importLazada(List.of(product.sourceUrl()));
        assertThat(result.skipped()).isEqualTo(1);
        assertThat(result.updated()).isZero();
        assertThat(result.created()).isZero();
        assertThat(result.state()).isEqualTo("UNCHANGED");
        assertThat(result.items().getFirst().skipReason()).contains("ACTIVE");
    }

    private record FixedGateway(ExternalCatalogProduct product)
            implements com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway {
        @Override public List<ExternalCatalogProduct> fetchLazadaProducts(List<java.net.URI> urls) { return List.of(product); }
    }

    private static final class CountingRepository implements ExternalCatalogRepository {
        private boolean exists;
        @Override public UpsertedProduct upsert(ExternalCatalogProduct product) {
            boolean created = !exists;
            exists = true;
            return new UpsertedProduct(UUID.fromString("30000000-0000-0000-0000-000000000099"),
                    UUID.fromString("20000000-0000-0000-0000-000000000099"), created);
        }
        @Override public boolean publish(UUID productId) { return true; }
    }
}
