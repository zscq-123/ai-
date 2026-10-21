package com.zscq.mall.commerce.externalcatalog.infrastructure;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProviderException;
import com.zscq.mall.commerce.externalcatalog.domain.LazadaUrl;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.function.Function;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class LazadaDirectClient implements ExternalCatalogGateway {
    private static final int MAX_PAGE_BYTES = 3 * 1024 * 1024;
    private final Function<URI, String> fetchPage;
    private final Duration interval;

    @Autowired
    public LazadaDirectClient(
            @Value("${integrations.lazada-direct.timeout:PT20S}") Duration timeout,
            @Value("${integrations.lazada-direct.request-interval:PT1S}") Duration interval) {
        var client = HttpClient.newBuilder().connectTimeout(timeout).followRedirects(HttpClient.Redirect.NEVER).build();
        this.fetchPage = uri -> download(client, uri, timeout);
        this.interval = interval.isNegative() ? Duration.ZERO : interval;
    }

    LazadaDirectClient(Function<URI, String> fetchPage) {
        this.fetchPage = fetchPage;
        this.interval = Duration.ZERO;
    }

    @Override
    public List<ExternalCatalogProduct> fetchLazadaProducts(List<URI> productUrls) {
        var products = new LinkedHashMap<String, ExternalCatalogProduct>();
        int pages = 0;
        for (URI raw : productUrls) {
            URI url = LazadaUrl.validate(raw.toString());
            if (pages++ > 0 && !interval.isZero()) {
                try { Thread.sleep(interval.toMillis()); }
                catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                    throw new ExternalCatalogProviderException("Lazada direct collection was interrupted", exception);
                }
            }
            for (var product : LazadaPageParser.parse(url, fetchPage.apply(url), Instant.now())) {
                products.putIfAbsent(product.externalProductId(), product);
                if (products.size() >= 20) return List.copyOf(products.values());
            }
        }
        return List.copyOf(products.values());
    }

    static String download(HttpClient client, URI uri, Duration timeout) {
        var request = HttpRequest.newBuilder(uri).timeout(timeout)
                .header("User-Agent", "NOVA-Catalog/1.0 (public catalog import)")
                .header("Accept", "text/html,application/xhtml+xml").GET().build();
        try {
            var response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
            try (var body = response.body()) {
                if (response.statusCode() != 200) throw new ExternalCatalogProviderException(
                        "Lazada direct request returned HTTP " + response.statusCode() + " for " + uri
                                + "; redirects and verification challenges are not followed", null);
                byte[] bytes = body.readNBytes(MAX_PAGE_BYTES + 1);
                if (bytes.length > MAX_PAGE_BYTES) throw new ExternalCatalogProviderException("Lazada page exceeds the 3 MB import limit", null);
                return new String(bytes, StandardCharsets.UTF_8);
            }
        } catch (IOException exception) {
            throw new ExternalCatalogProviderException("Lazada direct request failed for " + uri, exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new ExternalCatalogProviderException("Lazada direct request was interrupted", exception);
        }
    }
}
