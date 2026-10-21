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
