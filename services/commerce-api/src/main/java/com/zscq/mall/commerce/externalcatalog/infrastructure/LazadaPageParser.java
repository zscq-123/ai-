package com.zscq.mall.commerce.externalcatalog.infrastructure;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProviderException;
import com.zscq.mall.commerce.externalcatalog.domain.LazadaUrl;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Reads data embedded in public HTML. Never evaluates page JavaScript. */
final class LazadaPageParser {
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String FIRST_SCREEN_DATA = "window.__FIRST_SCREEN_DATA";
    private static final Pattern JSON_LD = Pattern.compile(
            "<script[^>]*type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>",
            Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private LazadaPageParser() {}

    static List<ExternalCatalogProduct> parse(URI page, String html, Instant fetchedAt) {
        String lower = html.toLowerCase(Locale.ROOT);
        if (lower.contains("_____tmd_____/punish") || lower.contains("\"action\":\"captcha\"")
                || lower.contains("<title>access denied") || lower.contains("<title>captcha")) {
            throw new ExternalCatalogProviderException("Lazada requires verification for " + page
                    + "; collection stopped without retrying or bypassing verification", null);
        }
        List<ExternalCatalogProduct> products = new ArrayList<>();
        if ("/".equals(page.getPath())) {
            String data = jsonAssignment(html, FIRST_SCREEN_DATA);
            if (data != null) collectHomepageCards(JSON.readTree(data), page, fetchedAt, products);
        } else {
            var matcher = JSON_LD.matcher(html);
            while (matcher.find()) {
                try { collectJsonLd(JSON.readTree(matcher.group(1)), page, fetchedAt, products); }
                catch (IllegalArgumentException ignored) { /* Ignore unrelated malformed JSON-LD. */ }
            }
        }
        if (products.isEmpty()) throw new ExternalCatalogProviderException(
                "Lazada page contains no supported public product data: " + page, null);
        var unique = new LinkedHashMap<String, ExternalCatalogProduct>();
        products.forEach(product -> unique.putIfAbsent(product.externalProductId(), product));
        return List.copyOf(unique.values());
    }

    private static void collectHomepageCards(JsonNode node, URI page, Instant fetchedAt,
            List<ExternalCatalogProduct> products) {
        if (node == null) return;
        if (node.isObject() && text(node, "itemUrl") != null && text(node, "itemTitle") != null) {
            String rawUrl = text(node, "itemUrl");
            URI productUrl;
            try { productUrl = LazadaUrl.validate(page.resolve(rawUrl).toString()); }
            catch (IllegalArgumentException ignored) { return; }
            if ("/".equals(productUrl.getPath()) || !LazadaUrl.market(page).equals(LazadaUrl.market(productUrl))) return;
            BigDecimal price = decimal(node, "itemDiscountPrice");
            if (price == null) price = decimal(node, "itemPrice");
            if (price == null || price.signum() < 0) return;
            BigDecimal originalPrice = decimal(node, "itemPrice");
            if (originalPrice != null && originalPrice.compareTo(price) < 0) originalPrice = null;
            String currency = LazadaUrl.currency(productUrl);
            String declaredCurrency = text(node, "currency");
            if (declaredCurrency != null && declaredCurrency.matches("[A-Za-z]{3}")
                    && !currency.equalsIgnoreCase(declaredCurrency)) return;
            int stock = nonNegativeInt(node, "itemCurrentStock");
            products.add(new ExternalCatalogProduct("LAZADA", LazadaUrl.productId(productUrl),
                    LazadaUrl.skuId(productUrl), productUrl.toString(), text(node, "itemTitle"), null, null, null,
                    "Lazada " + LazadaUrl.market(page) + " · 待确认商家", money(price), money(originalPrice), currency,
                    stock, 0, null, safeImage(text(node, "itemImg")),
                    payload(node, page, fetchedAt, "PUBLIC_HOMEPAGE_SSR")));
            return;
        }
        if (node.isObject() || node.isArray()) {
            for (JsonNode child : node) collectHomepageCards(child, page, fetchedAt, products);
        }
    }

    private static void collectJsonLd(JsonNode node, URI page, Instant fetchedAt,
            List<ExternalCatalogProduct> products) {
        if (node == null) return;
        if (node.isArray()) {
            for (JsonNode child : node) collectJsonLd(child, page, fetchedAt, products);
            return;
        }
        if (!node.isObject()) return;
        if (!isProduct(node.get("@type"))) {
            collectJsonLd(node.get("@graph"), page, fetchedAt, products);
            return;
        }
        JsonNode offer = node.get("offers");
        if (offer != null && offer.isArray() && !offer.isEmpty()) offer = offer.get(0);
        if (offer == null || !offer.isObject()) return;
        // AggregateOffer.lowPrice is a range boundary, not a purchasable SKU price.
        BigDecimal price = decimal(offer, "price");
        String name = text(node, "name");
        String currency = text(offer, "priceCurrency");
        if (price == null || price.signum() < 0 || name == null || currency == null
                || !currency.matches("[A-Za-z]{3}")) return;
        String brand = nestedName(node.get("brand"));
        String seller = nestedName(offer.get("seller"));
        if (seller == null) seller = "Lazada " + LazadaUrl.market(page) + " · 待确认商家";
        BigDecimal rating = decimal(node.get("aggregateRating"), "ratingValue");
        if (rating != null && (rating.signum() < 0 || rating.compareTo(BigDecimal.valueOf(5)) > 0)) rating = null;
        products.add(new ExternalCatalogProduct("LAZADA", LazadaUrl.productId(page),
                text(node, "sku") == null ? LazadaUrl.skuId(page) : text(node, "sku"), page.toString(), name,
                brand, brand, text(node, "description"), seller, money(price), null,
                currency.toUpperCase(Locale.ROOT), 0, 0, rating,
                image(node.get("image")), payload(node, page, fetchedAt, "PUBLIC_PRODUCT_JSON_LD")));
    }

    private static boolean isProduct(JsonNode type) {
        if (type == null) return false;
        if (type.isArray()) { for (JsonNode child : type) if (isProduct(child)) return true; }
        return type.isTextual() && "Product".equalsIgnoreCase(type.asText());
    }
    private static String nestedName(JsonNode node) { return node == null ? null : node.isTextual() ? node.asText() : text(node, "name"); }
    private static String image(JsonNode node) {
        if (node == null) return null;
        if (node.isArray()) return node.isEmpty() ? null : image(node.get(0));
        return safeImage(node.isTextual() ? node.asText() : text(node, "url"));
    }
    private static String safeImage(String value) {
        if (value == null) return null;
        try {
            URI uri = URI.create(value.startsWith("//") ? "https:" + value : value);
            return "https".equalsIgnoreCase(uri.getScheme()) && uri.getHost() != null && uri.getUserInfo() == null
                    ? uri.toString() : null;
        } catch (IllegalArgumentException ignored) { return null; }
    }
    private static String payload(JsonNode source, URI page, Instant at, String format) {
        var payload = JSON.createObjectNode();
        payload.put("provider", "LAZADA_DIRECT");
        payload.put("format", format);
        payload.put("fetchedFrom", page.toString());
        payload.put("fetchedAt", at.toString());
        payload.set("record", source);
        return payload.toString();
    }
    private static String text(JsonNode node, String field) {
        JsonNode value = node == null ? null : node.get(field);
        if (value == null || value.isNull() || !value.isValueNode()) return null;
        String result = value.asText().trim();
        return result.isEmpty() ? null : result;
    }
    private static BigDecimal decimal(JsonNode node, String field) {
        String value = text(node, field);
        try { return value == null ? null : new BigDecimal(value); }
        catch (NumberFormatException ignored) { return null; }
    }
    private static int nonNegativeInt(JsonNode node, String field) {
        BigDecimal value = decimal(node, field);
        if (value == null || value.signum() < 0 || value.compareTo(BigDecimal.valueOf(Integer.MAX_VALUE)) > 0) return 0;
        try { return value.intValueExact(); } catch (ArithmeticException ignored) { return 0; }
    }
    private static BigDecimal money(BigDecimal value) { return value == null ? null : value.setScale(2, RoundingMode.HALF_UP); }

    static String jsonAssignment(String html, String assignment) {
        int start = html.indexOf(assignment);
        if (start < 0) return null;
        int cursor = start + assignment.length();
        while (cursor < html.length() && Character.isWhitespace(html.charAt(cursor))) cursor++;
        if (cursor >= html.length() || html.charAt(cursor++) != '=') return null;
        while (cursor < html.length() && Character.isWhitespace(html.charAt(cursor))) cursor++;
        if (cursor >= html.length() || html.charAt(cursor) != '{') return null;
        start = cursor;
        int depth = 0;
        boolean quoted = false;
        boolean escaped = false;
        for (; cursor < html.length(); cursor++) {
            char value = html.charAt(cursor);
            if (quoted) {
                if (escaped) escaped = false;
                else if (value == '\\') escaped = true;
                else if (value == '"') quoted = false;
            } else if (value == '"') quoted = true;
            else if (value == '{') depth++;
            else if (value == '}' && --depth == 0) return html.substring(start, cursor + 1);
        }
        return null;
    }
}
