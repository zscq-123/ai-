package com.zscq.mall.commerce.externalcatalog.infrastructure;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.sun.net.httpserver.HttpServer;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProviderException;
import com.zscq.mall.commerce.externalcatalog.domain.LazadaUrl;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class LazadaDirectClientTest {
    private static final Instant FETCHED_AT = Instant.parse("2026-10-21T03:00:00Z");
    private static final String HOMEPAGE = """
            <script>window.__FIRST_SCREEN_DATA = {"data":{"homepage":{"sections":[{"items":[
              {"itemId":111650098,"itemTitle":"Sample { carton }","itemUrl":"//www.lazada.sg/products/pdp-i111650098-s23209659764.html?tracking=1",
               "itemDiscountPrice":"30.90","itemPrice":"38.00","currency":"$","itemCurrentStock":810,
               "itemSoldCnt":690,"itemImg":"https://img.lazcdn.com/sample.png"},
              {"itemTitle":"No stock count","itemUrl":"//www.lazada.sg/products/pdp-i222-s333.html",
               "itemPrice":"4.20","currency":"$","itemHaveStock":1}
            ]}]}}};window.unrelated = true;</script>
            """;

    @Test
    void parsesObservedPublicHomepageShapeAndKeepsProvenance() {
        var products = LazadaPageParser.parse(URI.create("https://www.lazada.sg/"), HOMEPAGE, FETCHED_AT);
        assertThat(products).hasSize(2);
        var first = products.get(0);
        assertThat(first.externalProductId()).isEqualTo("SG:111650098");
        assertThat(first.externalSkuId()).isEqualTo("111650098_SGAMZ-23209659764");
        assertThat(first.sourceUrl()).isEqualTo("https://www.lazada.sg/products/pdp-i111650098-s23209659764.html");
        assertThat(first.salePrice()).isEqualByComparingTo("30.90");
        assertThat(first.marketPrice()).isEqualByComparingTo("38.00");
        assertThat(first.currency()).isEqualTo("SGD");
        assertThat(first.availableStock()).isEqualTo(810);
        // Homepage itemSoldCnt describes the campaign, not total lifetime sales.
        assertThat(first.soldCount()).isZero();
        assertThat(first.sellerName()).contains("待确认商家");
        assertThat(first.sourcePayload()).contains("LAZADA_DIRECT", "PUBLIC_HOMEPAGE_SSR", FETCHED_AT.toString(), "itemSoldCnt");
        assertThat(products.get(1).availableStock()).isZero();
    }

    @Test
    void parsesJsonLdWithoutTurningAvailabilityIntoInventory() {
        String html = """
                <script type="application/ld+json">{"@graph":[{"@type":["Thing","Product"],
                "name":"Detail product","sku":"sku-2","brand":{"name":"Sample"},"image":["https://img.lazcdn.com/a.jpg"],
                "offers":{"@type":"Offer","price":"125.50","priceCurrency":"MYR","availability":"https://schema.org/InStock",
                "seller":{"name":"Actual seller"}}}]}</script>
                """;
        var product = LazadaPageParser.parse(URI.create("https://www.lazada.com.my/products/pdp-i123-s456.html"), html, FETCHED_AT).getFirst();
        assertThat(product.externalProductId()).isEqualTo("MY:123");
        assertThat(product.sellerName()).isEqualTo("Actual seller");
        assertThat(product.currency()).isEqualTo("MYR");
        assertThat(product.availableStock()).isZero();
        assertThat(product.sourcePayload()).contains("PUBLIC_PRODUCT_JSON_LD");
    }

    @Test
    void stopsAtVerificationWithoutRetryOrInventedData() {
        AtomicInteger calls = new AtomicInteger();
        var client = new LazadaDirectClient(url -> {
            calls.incrementAndGet();
            return "<script>window._config_={\"action\":\"captcha\"};location.href='/_____tmd_____/punish';</script>";
        });
        assertThatThrownBy(() -> client.fetchLazadaProducts(List.of(URI.create("https://www.lazada.sg/products/pdp-i1-s2.html"))))
                .isInstanceOf(ExternalCatalogProviderException.class).hasMessageContaining("requires verification");
        assertThat(calls.get()).isEqualTo(1);
    }

    @Test
    void rejectsUntrustedHostsPortsCredentialsAndNonCatalogPaths() {
        for (String url : List.of("https://evil.lazada.sg/", "https://www.lazada.sg:444/", "https://token@www.lazada.sg/",
                "https://www.lazada.sg.evil.test/", "https://www.lazada.sg/redirect", "http://www.lazada.sg/")) {
            assertThatThrownBy(() -> LazadaUrl.validate(url)).isInstanceOf(IllegalArgumentException.class);
        }
        assertThat(LazadaUrl.validate("https://lazada.sg/?tracking=1").toString()).isEqualTo("https://www.lazada.sg/");
    }

    @Test
    void deduplicatesAcrossMultiplePublicPages() {
        var client = new LazadaDirectClient(url -> HOMEPAGE);
        var products = client.fetchLazadaProducts(List.of(URI.create("https://www.lazada.sg/"), URI.create("https://lazada.sg/")));
        assertThat(products).hasSize(2);
    }

    @Test
    void directHttpDoesNotSendBrightDataCredentialsOrFollowRedirects() throws Exception {
        AtomicInteger targetCalls = new AtomicInteger();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/page", exchange -> {
            assertThat(exchange.getRequestHeaders().getFirst("Authorization")).isNull();
            byte[] bytes = HOMEPAGE.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.createContext("/redirect", exchange -> {
            exchange.getResponseHeaders().set("Location", "/target");
            exchange.sendResponseHeaders(302, -1);
            exchange.close();
        });
        server.createContext("/target", exchange -> { targetCalls.incrementAndGet(); exchange.sendResponseHeaders(200, -1); exchange.close(); });
        server.start();
        try (var http = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build()) {
            URI base = URI.create("http://127.0.0.1:" + server.getAddress().getPort());
            assertThat(LazadaDirectClient.download(http, base.resolve("/page"), Duration.ofSeconds(2))).isEqualTo(HOMEPAGE);
            assertThatThrownBy(() -> LazadaDirectClient.download(http, base.resolve("/redirect"), Duration.ofSeconds(2)))
                    .isInstanceOf(ExternalCatalogProviderException.class).hasMessageContaining("HTTP 302");
            assertThat(targetCalls.get()).isZero();
        } finally { server.stop(0); }
    }
}
