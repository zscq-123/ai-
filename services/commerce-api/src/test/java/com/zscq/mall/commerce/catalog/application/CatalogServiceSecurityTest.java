package com.zscq.mall.commerce.catalog.application;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

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
    void updateRequiresMerchantOwnershipAndMatchingVersion() {
        UUID merchantId = UUID.randomUUID();
        Product product = Product.draft(merchantId, UUID.randomUUID(), "Name", null, null, null,
                BigDecimal.ZERO, "SKU", "Default", BigDecimal.ONE, null, 2);
        CatalogService service = new CatalogService(new FixedRepository(product));

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
    }
}
