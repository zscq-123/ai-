package com.zscq.mall.commerce.catalog.application;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import com.zscq.mall.commerce.catalog.domain.CatalogRepository;
import com.zscq.mall.commerce.catalog.domain.Product;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.dao.OptimisticLockingFailureException;

class CatalogServiceSecurityTest {
    @Test
    void savesGalleryOrderAndCoverWithoutDiscardingOtherFields() {
        UUID merchantId = UUID.randomUUID();
        Product product = Product.draft(merchantId, UUID.randomUUID(), "Name", "Subtitle", "Brand", "Description",
                new BigDecimal("1.2"), "SKU", "Default", new BigDecimal("12.50"), new BigDecimal("15"), 7);
        var media = mock(com.zscq.mall.commerce.media.MediaAssets.class);
        List<String> urls = List.of("/api/public/media/product-images/second", "/api/public/media/product-images/first");
        when(media.validateProductImages(merchantId, urls, product.imageUrls())).thenReturn(urls);
        var service = new CatalogService(new FixedRepository(product), media);

        Product saved = service.update(product.id(), merchantId, product.version(), product.categoryId(), product.name(),
                product.subtitle(), product.brand(), product.description(), product.weightKg(), product.skuCode(),
                product.skuTitle(), product.salePrice(), product.marketPrice(), product.availableStock(), urls);

        assertThat(saved.imageUrls()).containsExactlyElementsOf(urls);
        assertThat(saved.coverImageUrl()).isEqualTo(urls.getFirst());
        assertThat(saved.name()).isEqualTo(product.name());
        assertThat(saved.description()).isEqualTo(product.description());
        assertThat(saved.skuId()).isEqualTo(product.skuId());
        assertThat(saved.salePrice()).isEqualByComparingTo(product.salePrice());
        assertThat(saved.availableStock()).isEqualTo(7);
        assertThat(saved.currency()).isEqualTo("CNY");
        verify(media).validateProductImages(merchantId, urls, product.imageUrls());
    }

    @Test
    void updateRequiresMerchantOwnershipAndMatchingVersion() {
        UUID merchantId = UUID.randomUUID();
        Product product = Product.draft(merchantId, UUID.randomUUID(), "Name", null, null, null,
                BigDecimal.ZERO, "SKU", "Default", BigDecimal.ONE, null, 2);
        CatalogService service = new CatalogService(new FixedRepository(product), org.mockito.Mockito.mock(com.zscq.mall.commerce.media.MediaAssets.class));

        assertThatThrownBy(() -> service.update(product.id(), UUID.randomUUID(), product.version(),
                product.categoryId(), "Changed", null, null, null, BigDecimal.ZERO,
                "SKU", "Default", BigDecimal.ONE, null, 2))
                .isInstanceOf(SecurityException.class);

        assertThatThrownBy(() -> service.update(product.id(), merchantId, product.version() + 1,
                product.categoryId(), "Changed", null, null, null, BigDecimal.ZERO,
                "SKU", "Default", BigDecimal.ONE, null, 2))
                .isInstanceOf(OptimisticLockingFailureException.class);
    }

    private record FixedRepository(Product product) implements CatalogRepository {
        public Product save(Product value) { return value; }
        public List<Product> search(String query, UUID categoryId) { return List.of(); }
        public Optional<Product> findActiveById(UUID id) { return Optional.empty(); }
        public Optional<Product> findById(UUID id) { return Optional.of(product); }
        public Optional<Product> findByIdForUpdate(UUID id) { return Optional.of(product); }
        public List<com.zscq.mall.commerce.catalog.domain.Category> categories() { return List.of(); }
    }
}
