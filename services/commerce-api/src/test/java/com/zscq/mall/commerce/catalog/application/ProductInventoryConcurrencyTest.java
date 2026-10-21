package com.zscq.mall.commerce.catalog.application;

import static org.assertj.core.api.Assertions.*;

import com.zscq.mall.commerce.catalog.domain.Product;
import com.zscq.mall.commerce.order.domain.SkuPricingRepository;
import java.sql.DriverManager;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.*;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/** Real PostgreSQL locks in an isolated, disposable schema; opt in with NOVA_POSTGRES_TEST_URL. */
@SpringBootTest
@DirtiesContext
@EnabledIfEnvironmentVariable(named = "NOVA_POSTGRES_TEST_URL", matches = ".+")
class ProductInventoryConcurrencyTest {
    private static final String SCHEMA = "media_race_" + UUID.randomUUID().toString().replace("-", "");
    private static final UUID PRODUCT = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID SKU = UUID.fromString("40000000-0000-0000-0000-000000000001");

    @Autowired CatalogService catalog;
    @Autowired SkuPricingRepository pricing;
    @Autowired JdbcTemplate jdbc;
    @Autowired PlatformTransactionManager transactionManager;

    @DynamicPropertySource
    static void database(DynamicPropertyRegistry properties) throws Exception {
        try (var connection = DriverManager.getConnection(databaseUrl(), username(), password());
             var statement = connection.createStatement()) {
            statement.execute("create schema " + SCHEMA);
        }
        properties.add("spring.datasource.url", () -> databaseUrl() + (databaseUrl().contains("?") ? "&" : "?") + "currentSchema=" + SCHEMA);
        properties.add("spring.datasource.username", ProductInventoryConcurrencyTest::username);
        properties.add("spring.datasource.password", ProductInventoryConcurrencyTest::password);
        properties.add("spring.flyway.schemas", () -> SCHEMA);
    }

    @AfterAll
    static void cleanup() throws Exception {
        try (var connection = DriverManager.getConnection(databaseUrl(), username(), password());
             var statement = connection.createStatement()) {
            statement.execute("drop schema if exists " + SCHEMA + " cascade");
        }
    }

    @BeforeEach
    void resetFixture() {
        jdbc.update("update products set version=0, image_urls='[]'::jsonb, status='ACTIVE' where id=?", PRODUCT);
        jdbc.update("update product_skus set available_stock=10, enabled=true where id=?", SKU);
    }

    @Test
    void aCheckoutCommittedBeforeImageSaveMakesTheOldEditorConflict() {
        Product opened = catalog.get(PRODUCT);
        assertThat(pricing.reserve(SKU, 1)).isPresent();

        assertThatThrownBy(() -> save(opened, opened.availableStock()))
                .isInstanceOf(OptimisticLockingFailureException.class);
        assertThat(catalog.get(PRODUCT).availableStock()).isEqualTo(9);
        assertThat(catalog.get(PRODUCT).version()).isEqualTo(opened.version() + 1);
    }

    @Test
    void anImageSaveWaitingBehindCheckoutReadsTheCommittedVersion() throws Exception {
        Product opened = catalog.get(PRODUCT);
        CountDownLatch checkoutLocked = new CountDownLatch(1);
        CountDownLatch releaseCheckout = new CountDownLatch(1);
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var checkout = executor.submit(() -> new TransactionTemplate(transactionManager).execute(status -> {
                var reserved = pricing.reserve(SKU, 1);
                checkoutLocked.countDown();
                await(releaseCheckout);
                return reserved;
            }));
            assertThat(checkoutLocked.await(10, TimeUnit.SECONDS)).isTrue();
            var edit = executor.submit(() -> save(opened, opened.availableStock()));
            try {
                assertThatThrownBy(() -> edit.get(150, TimeUnit.MILLISECONDS)).isInstanceOf(TimeoutException.class);
            } finally { releaseCheckout.countDown(); }

            assertThat(checkout.get(10, TimeUnit.SECONDS)).isPresent();
            assertThatThrownBy(() -> edit.get(10, TimeUnit.SECONDS))
                    .isInstanceOf(ExecutionException.class).hasCauseInstanceOf(OptimisticLockingFailureException.class);
        }
        assertThat(catalog.get(PRODUCT).availableStock()).isEqualTo(9);
    }

    @Test
    void checkoutWaitingBehindMerchantSaveReservesFromTheNewStock() throws Exception {
        Product opened = catalog.get(PRODUCT);
        CountDownLatch merchantLocked = new CountDownLatch(1);
        CountDownLatch releaseMerchant = new CountDownLatch(1);
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var edit = executor.submit(() -> new TransactionTemplate(transactionManager).execute(status -> {
                Product saved = save(opened, 5);
                merchantLocked.countDown();
                await(releaseMerchant);
                return saved;
            }));
            assertThat(merchantLocked.await(10, TimeUnit.SECONDS)).isTrue();
            var checkout = executor.submit(() -> pricing.reserve(SKU, 1));
            try {
                assertThatThrownBy(() -> checkout.get(150, TimeUnit.MILLISECONDS)).isInstanceOf(TimeoutException.class);
            } finally { releaseMerchant.countDown(); }

            assertThat(edit.get(10, TimeUnit.SECONDS).availableStock()).isEqualTo(5);
            assertThat(checkout.get(10, TimeUnit.SECONDS)).hasValueSatisfying(sku -> assertThat(sku.stock()).isEqualTo(4));
        }
        Product result = catalog.get(PRODUCT);
        assertThat(result.availableStock()).isEqualTo(4);
        assertThat(result.version()).isEqualTo(2);
    }

    private Product save(Product opened, int stock) {
        return catalog.update(opened.id(), opened.merchantId(), opened.version(), opened.categoryId(), opened.name(),
                opened.subtitle(), opened.brand(), opened.description(), opened.weightKg(), opened.skuCode(), opened.skuTitle(),
                opened.salePrice(), opened.marketPrice(), stock, List.of());
    }

    private static void await(CountDownLatch latch) {
        try {
            if (!latch.await(10, TimeUnit.SECONDS)) throw new IllegalStateException("Timed out waiting for concurrent transaction");
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(exception);
        }
    }

    private static String databaseUrl() { return System.getenv("NOVA_POSTGRES_TEST_URL"); }
    private static String username() { return System.getenv().getOrDefault("POSTGRES_USER", "commerce"); }
    private static String password() { return System.getenv().getOrDefault("POSTGRES_PASSWORD", "commerce_local"); }
}
