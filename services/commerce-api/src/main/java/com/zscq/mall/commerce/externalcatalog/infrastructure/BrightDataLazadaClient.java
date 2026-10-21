package com.zscq.mall.commerce.externalcatalog.infrastructure;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogGateway;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProviderException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URI;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@Component
public class BrightDataLazadaClient implements ExternalCatalogGateway {
    static final String LAZADA = "LAZADA";
    private static final Pattern PRODUCT_ID_IN_URL = Pattern.compile("(?:-|/)i(\\d+)(?:-|\\.|/|$)");
    private static final Pattern JSON_LD_SCRIPT = Pattern.compile(
            "<script[^>]*type=[\\\"']application/ld\\+json[\\\"'][^>]*>(.*?)</script>",
            Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private final RestClient client;
    private final String apiKey;
    private final String datasetId;
    private final int pollAttempts;
    private final Duration pollInterval;

    public BrightDataLazadaClient(
            @Value("${integrations.bright-data.base-url:https://api.brightdata.com}") String baseUrl,
            @Value("${integrations.bright-data.api-key:}") String apiKey,
            @Value("${integrations.bright-data.lazada-dataset-id:gd_m6gjtfmeh43we6cqc}") String datasetId,
            @Value("${integrations.bright-data.poll-attempts:20}") int pollAttempts,
            @Value("${integrations.bright-data.poll-interval:PT3S}") Duration pollInterval) {
        this.client = RestClient.builder().baseUrl(baseUrl).build();
        this.apiKey = apiKey;
        this.datasetId = datasetId;
        this.pollAttempts = pollAttempts;
        this.pollInterval = pollInterval;
    }

    @Override
    public List<ExternalCatalogProduct> fetchLazadaProducts(List<URI> productUrls) {
        try {
            return fetch(productUrls);
        } catch (RestClientResponseException exception) {
            throw new ExternalCatalogProviderException(
                    "Bright Data Lazada request failed with HTTP " + exception.getStatusCode().value(), exception);
        }
    }

    private List<ExternalCatalogProduct> fetch(List<URI> productUrls) {
        if (apiKey == null || apiKey.isBlank()) throw new IllegalStateException("BRIGHT_DATA_API_KEY is not configured");
        List<Map<String, Object>> inputs = productUrls.stream()
                .map(uri -> Map.<String, Object>of("url", uri.toString()))
                .toList();
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("input", inputs);
        request.put("limit_per_input", null);
        ResponseEntity<JsonNode> response = client.post()
                .uri(uriBuilder -> uriBuilder.path("/datasets/v3/scrape")
                        .queryParam("dataset_id", datasetId)
                        .queryParam("notify", false)
                        .queryParam("format", "json")
                        .queryParam("include_errors", true)
                        .build())
                .header("Authorization", "Bearer " + apiKey)
                .body(request)
                .retrieve()
                .toEntity(JsonNode.class);

        JsonNode body = response.getBody();
        if (response.getStatusCode() == HttpStatus.ACCEPTED) {
            String snapshotId = text(body, "snapshot_id");
            if (snapshotId == null) throw new IllegalStateException("Bright Data returned 202 without a snapshot_id");
            body = awaitSnapshot(snapshotId);
        }
        if (body == null || !body.isArray()) throw new IllegalStateException("Bright Data returned an unexpected Lazada response");

        List<ExternalCatalogProduct> result = new ArrayList<>();
        for (JsonNode record : body) {
            if (record.hasNonNull("error") && text(record, "url") == null) continue;
            result.add(normalize(record));
        }
        return List.copyOf(result);
    }

    private JsonNode awaitSnapshot(String snapshotId) {
        for (int attempt = 0; attempt < pollAttempts; attempt++) {
            JsonNode progress = client.get()
                    .uri("/datasets/v3/progress/{snapshotId}", snapshotId)
                    .header("Authorization", "Bearer " + apiKey)
                    .retrieve().body(JsonNode.class);
            String status = text(progress, "status");
            if ("ready".equalsIgnoreCase(status)) {
                return client.get()
                        .uri(uriBuilder -> uriBuilder.path("/datasets/v3/snapshot/{snapshotId}")
                                .queryParam("format", "json").build(snapshotId))
                        .header("Authorization", "Bearer " + apiKey)
                        .retrieve().body(JsonNode.class);
            }
            if ("failed".equalsIgnoreCase(status)) throw new IllegalStateException("Bright Data Lazada collection failed");
            try {
                Thread.sleep(pollInterval.toMillis());
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("Bright Data Lazada collection was interrupted", exception);
            }
        }
        throw new IllegalStateException("Bright Data Lazada collection did not finish before timeout");
    }

    static ExternalCatalogProduct normalize(JsonNode record) {
        JsonNode structured = record.has("data") && record.get("data").isObject() ? record.get("data") : record;
        if (firstText(structured, "title", "name", "product_name") == null
                || firstDecimal(structured, "final_price", "price", "sale_price", "actual_price") == null) {
            ExternalCatalogProduct generic = normalizeGenericPage(record);
            if (generic != null) return generic;
        }
        record = structured;
        String sourceUrl = requiredText(record, "url", "origin_url");
        String externalSku = firstText(record, "sku", "item_id", "product_id");
        String externalId = externalProductId(sourceUrl, externalSku);
        String name = requiredText(record, "title", "name", "product_name");
        BigDecimal salePrice = firstDecimal(record, "final_price", "price", "sale_price", "actual_price");
        if (salePrice == null) throw new IllegalArgumentException("Lazada record has no usable price");
        BigDecimal marketPrice = firstDecimal(record, "initial_price", "original_price", "market_price");
        if (marketPrice != null && marketPrice.compareTo(salePrice) < 0) marketPrice = null;
        String currency = normalizedCurrency(firstText(record, "currency", "currency_code"), sourceUrl);
        int stock = firstInteger(record, "stock", "available_stock", "quantity");
        if (stock < 0) stock = availabilityStock(record);
        long sold = Math.max(0, firstLong(record, "number_sold", "sold", "sales"));
        BigDecimal rating = firstDecimal(record, "rating", "rating_score");
        if (rating != null) rating = rating.setScale(2, RoundingMode.HALF_UP);
        String image = firstImage(record);
        String seller = firstText(record, "seller_name", "shop_name", "seller");
        if (seller == null) seller = "Lazada 商家";
        String description = firstText(record, "description", "product_description");
        String subtitle = firstText(record, "brand", "category", "category_name");
        return new ExternalCatalogProduct(
                LAZADA, externalId, externalSku, sourceUrl, name, subtitle,
                firstText(record, "brand", "brand_name"), description, seller,
                salePrice.setScale(2, RoundingMode.HALF_UP), marketPrice, currency,
                Math.max(0, stock), sold, rating, image, record.toString());
    }

    private static ExternalCatalogProduct normalizeGenericPage(JsonNode record) {
        String sourceUrl = firstText(record, "url", "origin_url");
        String html = firstText(record, "content", "html", "body", "page_content");
        if (sourceUrl == null || html == null) return null;
        Matcher matcher = JSON_LD_SCRIPT.matcher(html);
        while (matcher.find()) {
            try {
                JsonNode product = findProductNode(JSON.readTree(matcher.group(1).trim()));
                if (product == null) continue;
                JsonNode offers = product.get("offers");
                if (offers != null && offers.isArray() && !offers.isEmpty()) offers = offers.get(0);
                BigDecimal price = offers == null ? null : firstDecimal(offers, "price", "lowPrice");
                String name = firstText(product, "name", "title");
                if (price == null || name == null) continue;
                String externalSku = firstText(product, "sku", "productID", "mpn");
                String image = imageFromJsonLd(product.get("image"));
                String brand = nestedText(product.get("brand"), "name");
                String seller = offers == null ? null : nestedText(offers.get("seller"), "name");
                JsonNode aggregateRating = product.get("aggregateRating");
                BigDecimal rating = aggregateRating == null ? null : firstDecimal(aggregateRating, "ratingValue");
                int stock = offers != null && String.valueOf(firstText(offers, "availability")).toLowerCase(Locale.ROOT).contains("instock") ? 1 : 0;
                String currency = offers == null ? null : firstText(offers, "priceCurrency");
                return new ExternalCatalogProduct(
                        LAZADA, externalProductId(sourceUrl, externalSku), externalSku, sourceUrl, name,
                        brand, brand, firstText(product, "description"), seller == null ? "Lazada 商家" : seller,
                        price.setScale(2, RoundingMode.HALF_UP), null, normalizedCurrency(currency, sourceUrl),
                        stock, 0, rating, image, record.toString());
            } catch (RuntimeException ignored) {
                // A page can contain several unrelated or malformed JSON-LD blocks.
            }
        }
        return null;
    }

    private static JsonNode findProductNode(JsonNode node) {
        if (node == null) return null;
        if (node.isArray()) {
            for (JsonNode child : node) {
                JsonNode found = findProductNode(child);
                if (found != null) return found;
            }
        } else if (node.isObject()) {
            String type = firstText(node, "@type");
            if (type != null && type.equalsIgnoreCase("Product")) return node;
            JsonNode graph = node.get("@graph");
            if (graph != null) return findProductNode(graph);
        }
        return null;
    }

    private static String imageFromJsonLd(JsonNode image) {
        if (image == null || image.isNull()) return null;
        if (image.isTextual()) return image.asText();
        if (image.isArray() && !image.isEmpty()) return imageFromJsonLd(image.get(0));
        return firstText(image, "url", "contentUrl");
    }

    private static String nestedText(JsonNode node, String field) {
        if (node == null) return null;
        return node.isTextual() ? node.asText() : firstText(node, field);
    }

    private static String externalProductId(String sourceUrl, String sku) {
        if (sku != null && !sku.isBlank()) return truncate(sku, 180);
        Matcher matcher = PRODUCT_ID_IN_URL.matcher(sourceUrl);
        if (matcher.find()) return matcher.group(1);
        return java.util.UUID.nameUUIDFromBytes(sourceUrl.getBytes(java.nio.charset.StandardCharsets.UTF_8)).toString();
    }

    private static String firstImage(JsonNode node) {
        String direct = firstText(node, "image_url", "main_image", "image", "thumbnail");
        if (direct != null) return direct;
        JsonNode images = node.get("images");
        if (images != null && images.isArray() && !images.isEmpty()) {
            JsonNode first = images.get(0);
            return first.isTextual() ? first.asText() : firstText(first, "url", "image_url");
        }
        return null;
    }

    private static int availabilityStock(JsonNode node) {
        JsonNode available = node.get("availability");
        if (available == null) available = node.get("in_stock");
        if (available == null || available.isNull()) return 0;
        if (available.isBoolean()) return available.asBoolean() ? 1 : 0;
        String value = available.asText("").toLowerCase(Locale.ROOT);
        return value.contains("in stock") || value.contains("available") ? 1 : 0;
    }

    private static String normalizedCurrency(String value, String url) {
        if (value != null && !value.isBlank() && !"$".equals(value.trim())) return value.trim().toUpperCase(Locale.ROOT);
        if (url.contains("lazada.com.my")) return "MYR";
        if (url.contains("lazada.co.th")) return "THB";
        if (url.contains("lazada.vn")) return "VND";
        if (url.contains("lazada.com.ph")) return "PHP";
        if (url.contains("lazada.co.id")) return "IDR";
        return "SGD";
    }

    private static String requiredText(JsonNode node, String... fields) {
        String value = firstText(node, fields);
        if (value == null) throw new IllegalArgumentException("Lazada record is missing " + fields[0]);
        return value;
    }

    private static String firstText(JsonNode node, String... fields) {
        if (node == null) return null;
        for (String field : fields) {
            JsonNode value = node.get(field);
            if (value != null && !value.isNull() && !value.isArray() && !value.isObject()) {
                String text = value.asText().trim();
                if (!text.isEmpty()) return text;
            }
        }
        return null;
    }

    private static String text(JsonNode node, String field) {
        return firstText(node, field);
    }

    private static BigDecimal firstDecimal(JsonNode node, String... fields) {
        String raw = firstText(node, fields);
        if (raw == null) return null;
        String normalized = raw.replaceAll("[^0-9.\\-]", "");
        if (normalized.isBlank() || normalized.equals("-") || normalized.equals(".")) return null;
        try { return new BigDecimal(normalized); }
        catch (NumberFormatException ignored) { return null; }
    }

    private static int firstInteger(JsonNode node, String... fields) {
        long value = firstLong(node, fields);
        if (value < 0) return -1;
        return value > Integer.MAX_VALUE ? Integer.MAX_VALUE : (int) value;
    }

    private static long firstLong(JsonNode node, String... fields) {
        String raw = firstText(node, fields);
        if (raw == null) return -1;
        String normalized = raw.replaceAll("[^0-9-]", "");
        if (normalized.isBlank() || normalized.equals("-")) return -1;
        try { return Long.parseLong(normalized); }
        catch (NumberFormatException ignored) { return -1; }
    }

    private static String truncate(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }
}
