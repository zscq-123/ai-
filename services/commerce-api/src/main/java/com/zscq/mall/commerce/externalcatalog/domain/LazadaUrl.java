package com.zscq.mall.commerce.externalcatalog.domain;

import java.net.URI;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

/** Public catalog URLs only; no arbitrary subdomains, credentials, ports or redirects. */
public final class LazadaUrl {
    private static final Map<String, String> MARKETS = Map.of(
            "lazada.sg", "SG", "lazada.com.my", "MY", "lazada.co.th", "TH",
            "lazada.vn", "VN", "lazada.com.ph", "PH", "lazada.co.id", "ID");
    private static final Map<String, String> CURRENCIES = Map.of(
            "SG", "SGD", "MY", "MYR", "TH", "THB", "VN", "VND", "PH", "PHP", "ID", "IDR");
    private static final Pattern PRODUCT = Pattern.compile("/products/[^/]*-i(\\d+)(?:-s(\\d+))?\\.html");

    private LazadaUrl() {}

    public static URI validate(String raw) {
        URI uri;
        try { uri = URI.create(raw == null ? "" : raw.trim()); }
        catch (IllegalArgumentException exception) { throw new IllegalArgumentException("Invalid Lazada URL", exception); }
        String host = uri.getHost();
        if (!"https".equalsIgnoreCase(uri.getScheme()) || host == null || uri.getUserInfo() != null
                || uri.getPort() != -1 || !MARKETS.containsKey(baseHost(host))) {
            throw new IllegalArgumentException("Only HTTPS Lazada storefront URLs are accepted");
        }
        String path = uri.getPath();
        if (path == null || path.isEmpty()) path = "/";
        if (!"/".equals(path) && !PRODUCT.matcher(path).matches()) {
            throw new IllegalArgumentException("Use a Lazada homepage or product detail URL");
        }
        return URI.create("https://www." + baseHost(host) + path);
    }

    public static String market(URI uri) { return MARKETS.get(baseHost(uri.getHost())); }
    public static String currency(URI uri) { return CURRENCIES.get(market(uri)); }
    public static String productId(URI uri) {
        var match = PRODUCT.matcher(uri.getPath());
        if (!match.matches()) throw new IllegalArgumentException("Lazada product URL has no item ID");
        return market(uri) + ":" + match.group(1);
    }
    public static String skuId(URI uri) {
        var match = PRODUCT.matcher(uri.getPath());
        return match.matches() && match.group(2) != null
                ? match.group(1) + "_" + market(uri) + "AMZ-" + match.group(2) : null;
    }
    private static String baseHost(String host) {
        String normalized = host.toLowerCase(Locale.ROOT);
        return normalized.startsWith("www.") ? normalized.substring(4) : normalized;
    }
}
