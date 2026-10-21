package com.zscq.mall.commerce.externalcatalog.application;

import static org.assertj.core.api.Assertions.*;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogRepository;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetails;
import java.math.BigDecimal;
import java.sql.DriverManager;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@SpringBootTest
@DirtiesContext
@EnabledIfEnvironmentVariable(named = "NOVA_POSTGRES_TEST_URL", matches = ".+")
class ExternalProductDetailsPersistenceTest {
    private static final String SCHEMA = "detail_evidence_" + UUID.randomUUID().toString().replace("-", "");
    @Autowired ExternalProductDetailsService details;
    @Autowired ExternalCatalogRepository externalCatalog;
    @Autowired JdbcTemplate jdbc;
    @Autowired PlatformTransactionManager transactionManager;

    @DynamicPropertySource
    static void database(DynamicPropertyRegistry properties) throws Exception {
        try (var connection = DriverManager.getConnection(url(), username(), password()); var statement = connection.createStatement()) {
            statement.execute("create schema " + SCHEMA);
        }
        properties.add("spring.datasource.url", () -> url() + (url().contains("?") ? "&" : "?") + "currentSchema=" + SCHEMA);
        properties.add("spring.datasource.username", ExternalProductDetailsPersistenceTest::username);
        properties.add("spring.datasource.password", ExternalProductDetailsPersistenceTest::password);
        properties.add("spring.flyway.schemas", () -> SCHEMA);
    }

    @AfterAll
    static void cleanup() throws Exception {
        try (var connection = DriverManager.getConnection(url(), username(), password()); var statement = connection.createStatement()) {
            statement.execute("drop schema if exists " + SCHEMA + " cascade");
        }
    }

    @Test
    void storesBrowserEvidenceWithoutReplacingHomepageCommercialFactsAndRetainsItOnHomepageResync() {
        String sourceUrl = "https://www.lazada.sg/products/test-product-i987654321-s123.html";
        String homepagePayload = "{\"provider\":\"LAZADA_DIRECT\",\"format\":\"PUBLIC_HOMEPAGE_SSR\",\"record\":{\"itemCurrentStock\":13}}";
        var source = new ExternalCatalogProduct("LAZADA", "SG:987654321", "987654321_SGAMZ-123", sourceUrl,
                "Homepage title", null, null, null, "Original homepage merchant", new BigDecimal("19.50"), new BigDecimal("25.00"),
                "SGD", 13, 7, null, "https://img.lazcdn.com/g/p/cover.jpg", homepagePayload);
        var transaction = new TransactionTemplate(transactionManager);
        var imported = transaction.execute(status -> externalCatalog.upsert(source));
        assertThat(imported).isNotNull();
        UUID id = imported.productId();
        var beforeProduct = jdbc.queryForMap("select merchant_id,status,source_currency,source_sold_count,source_payload::text from products where id=?", id);
        var beforeSku = jdbc.queryForMap("select * from product_skus where product_id=?", id);

        var result = details.supplement(id, 0, new ExternalProductDetails("BROWSER_VISIBLE_DETAIL", sourceUrl,
                Instant.now().minusSeconds(60), "Visible brand", null, List.of("Visible feature"),
                Map.of("Material", "Cotton"), Map.of("Color", List.of("Blue")), "Visible storefront name",
                "https://www.lazada.sg/shop/visible-store", Map.of("delivery", "Delivery time shown for current destination"), List.of()));

        assertThat(result.version()).isEqualTo(1);
        assertThat(result.updatedFields()).containsExactly("brand", "description");
        assertThat(jdbc.queryForMap("select merchant_id,status,source_currency,source_sold_count,source_payload::text from products where id=?", id)).isEqualTo(beforeProduct);
        assertThat(jdbc.queryForMap("select * from product_skus where product_id=?", id)).isEqualTo(beforeSku);
        assertThat(jdbc.queryForObject("select source_detail_payload->>'provider' from products where id=?", String.class, id)).isEqualTo("BROWSER_VISIBLE_DETAIL");
        assertThat(jdbc.queryForObject("select source_detail_payload->'attributes'->>'Material' from products where id=?", String.class, id)).isEqualTo("Cotton");
        String savedDetails = jdbc.queryForObject("select source_detail_payload::text from products where id=?", String.class, id);

        transaction.execute(status -> externalCatalog.upsert(source));
        assertThat(jdbc.queryForObject("select brand from products where id=?", String.class, id)).isEqualTo("Visible brand");
        assertThat(jdbc.queryForObject("select description from products where id=?", String.class, id)).contains("Visible feature", "Material：Cotton");
        assertThat(jdbc.queryForObject("select source_detail_payload::text from products where id=?", String.class, id)).isEqualTo(savedDetails);
    }

    private static String url() { return System.getenv("NOVA_POSTGRES_TEST_URL"); }
    private static String username() { return System.getenv().getOrDefault("POSTGRES_USER", "commerce"); }
    private static String password() { return System.getenv().getOrDefault("POSTGRES_PASSWORD", "commerce_local"); }
}
