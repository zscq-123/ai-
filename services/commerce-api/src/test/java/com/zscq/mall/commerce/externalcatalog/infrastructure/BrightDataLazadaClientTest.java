package com.zscq.mall.commerce.externalcatalog.infrastructure;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.URI;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

class BrightDataLazadaClientTest {
    private final JsonMapper mapper = JsonMapper.builder().build();

    @Test
    void normalizesTheCurrentLazadaProductShape() throws Exception {
        var source = mapper.readTree("""
                {
                  "url": "https://www.lazada.sg/products/sample-i3143299189-s21422552211.html",
                  "title": "Fresh Wear Foundation",
                  "sku": "3143299189_SGAMZ-21422552211",
                  "seller_name": "L'Oreal Paris",
                  "brand": "L'Oreal",
                  "initial_price": "$32.90",
                  "final_price": "$27.90",
                  "currency": "$",
                  "stock": 12,
                  "number_sold": 120,
                  "rating": 4.7,
                  "images": ["https://img.example.test/product.jpg"]
                }
                """);

        var product = BrightDataLazadaClient.normalize(source);

        assertThat(product.sourcePlatform()).isEqualTo("LAZADA");
        assertThat(product.externalProductId()).isEqualTo("3143299189_SGAMZ-21422552211");
        assertThat(product.salePrice()).isEqualByComparingTo(new BigDecimal("27.90"));
        assertThat(product.marketPrice()).isEqualByComparingTo(new BigDecimal("32.90"));
        assertThat(product.currency()).isEqualTo("SGD");
        assertThat(product.availableStock()).isEqualTo(12);
        assertThat(product.soldCount()).isEqualTo(120);
        assertThat(product.imageUrl()).isEqualTo("https://img.example.test/product.jpg");
        assertThat(product.sourcePayload()).contains("Fresh Wear Foundation");
    }

    @Test
    void derivesProductIdAndCurrencyWhenOptionalFieldsAreMissing() throws Exception {
        var source = mapper.readTree("""
                {
                  "url": "https://www.lazada.com.my/products/sample-i487926315-s847390602.html",
                  "name": "Baby Carrier",
                  "price": "RM 19.50",
                  "availability": true
                }
                """);

        var product = BrightDataLazadaClient.normalize(source);

        assertThat(product.externalProductId()).isEqualTo("487926315");
        assertThat(product.currency()).isEqualTo("MYR");
        assertThat(product.availableStock()).isEqualTo(1);
    }

    @Test
    void normalizesGenericPageOutputThroughProductJsonLd() throws Exception {
        var source = mapper.readTree("""
                {
                  "url": "https://www.lazada.sg/products/sample-i123456-s789.html",
                  "content": "<html><script type='application/ld+json'>{\\"@context\\":\\"https://schema.org\\",\\"@type\\":\\"Product\\",\\"name\\":\\"JSON-LD Product\\",\\"sku\\":\\"123456_SGAMZ-789\\",\\"brand\\":{\\"name\\":\\"NOVA\\"},\\"image\\":[\\"https://img.example.test/a.jpg\\"],\\"aggregateRating\\":{\\"ratingValue\\":\\"4.9\\"},\\"offers\\":{\\"price\\":\\"88.50\\",\\"priceCurrency\\":\\"SGD\\",\\"availability\\":\\"https://schema.org/InStock\\",\\"seller\\":{\\"name\\":\\"SG Seller\\"}}}</script></html>"
                }
                """);

        var product = BrightDataLazadaClient.normalize(source);

        assertThat(product.name()).isEqualTo("JSON-LD Product");
        assertThat(product.salePrice()).isEqualByComparingTo("88.50");
        assertThat(product.availableStock()).isEqualTo(1);
        assertThat(product.sellerName()).isEqualTo("SG Seller");
        assertThat(product.imageUrl()).isEqualTo("https://img.example.test/a.jpg");
    }

    @Test
    void sendsTheAccountSpecificWrapperContract() throws Exception {
        AtomicReference<String> query = new AtomicReference<>();
        AtomicReference<String> body = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/datasets/v3/scrape", exchange -> {
            query.set(exchange.getRequestURI().getQuery());
            body.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] response = """
                    [{"url":"https://www.lazada.sg/products/test-i123-s456.html","title":"Test","sku":"123_SGAMZ-456","price":9.9,"currency":"SGD"}]
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        try {
            var client = new BrightDataLazadaClient(
                    "http://127.0.0.1:" + server.getAddress().getPort(), "test-token",
                    "gd_m6gjtfmeh43we6cqc", 1, Duration.ZERO);

            var products = client.fetchLazadaProducts(List.of(URI.create("https://www.lazada.sg/products/test-i123-s456.html")));

            assertThat(products).hasSize(1);
            assertThat(query.get()).contains("dataset_id=gd_m6gjtfmeh43we6cqc", "notify=false", "include_errors=true");
            JsonNode sent = mapper.readTree(body.get());
            assertThat(sent.get("input").isArray()).isTrue();
            assertThat(sent.get("input").get(0).get("url").asText()).contains("lazada.sg/products/test");
            assertThat(sent.has("limit_per_input")).isTrue();
            assertThat(sent.get("limit_per_input").isNull()).isTrue();
        } finally {
            server.stop(0);
        }
    }
}
