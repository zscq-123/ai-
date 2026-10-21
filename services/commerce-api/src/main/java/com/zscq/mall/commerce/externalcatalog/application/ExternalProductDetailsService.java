package com.zscq.mall.commerce.externalcatalog.application;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetails;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetailsRepository;
import com.zscq.mall.commerce.externalcatalog.domain.LazadaUrl;
import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ExternalProductDetailsService {
    public static final String PROVIDER = "BROWSER_VISIBLE_DETAIL";
    private final ExternalProductDetailsRepository repository;

    public ExternalProductDetailsService(ExternalProductDetailsRepository repository) { this.repository = repository; }

    @Transactional
    public DetailResult supplement(UUID productId, long expectedVersion, ExternalProductDetails details) {
        URI source = validate(details);
        var product = repository.findForUpdate(productId).orElseThrow();
        if (!"DRAFT".equals(product.status())) throw new ResponseStatusException(HttpStatus.CONFLICT, "仅草稿商品可补充来源详情");
        if (product.version() != expectedVersion) throw new OptimisticLockingFailureException("商品已更新，请刷新后再补充详情");
        if (!"LAZADA".equals(product.sourcePlatform())
                || !LazadaUrl.productId(source).equals(product.externalProductId())
                || !LazadaUrl.productId(source).equals(LazadaUrl.productId(LazadaUrl.validate(product.sourceUrl())))) {
            throw new IllegalArgumentException("详情来源与当前商品的 Lazada 站点和商品编号不一致");
        }
        String brand = null;
        String description = null;
        var changed = new ArrayList<String>();
        if ("LAZADA_DIRECT".equals(product.sourceProvider())) {
            if (product.brand() == null && hasText(details.brand())) { brand = details.brand(); changed.add("brand"); }
            if (product.description() == null) {
                description = description(details);
                if (description != null) changed.add("description");
            }
        }
        List<String> images = null;
        // Only SQL NULL proves no explicit gallery exists. Any list can encode a merchant's selection,
        // including [] or a single original cover after the merchant removed other detail images.
        boolean originalGallery = product.imageUrls() == null;
        if (!details.imageUrls().isEmpty() && originalGallery) {
            var merged = new LinkedHashSet<String>();
            if (hasText(product.sourceImageUrl())) merged.add(product.sourceImageUrl());
            merged.addAll(details.imageUrls());
            images = merged.stream().limit(9).toList();
            if (images.equals(product.imageUrls())) images = null;
            else changed.add("imageUrls");
        }
        long version = repository.save(productId, expectedVersion, details, brand, description, images);
        return new DetailResult(productId, version, List.copyOf(changed), PROVIDER, details.sourceUrl(), details.capturedAt());
    }

    private static URI validate(ExternalProductDetails details) {
        if (!PROVIDER.equals(details.provider())) throw new IllegalArgumentException("详情来源必须标记为 BROWSER_VISIBLE_DETAIL");
        checkText(details.sourceUrl(), "sourceUrl", 2048, true);
        URI source = LazadaUrl.validate(https(details.sourceUrl(), "sourceUrl").toString());
        LazadaUrl.productId(source);
        if (details.capturedAt() == null || details.capturedAt().isAfter(Instant.now().plusSeconds(300))) {
            throw new IllegalArgumentException("capturedAt 必须为有效的采集时间");
        }
        checkText(details.brand(), "brand", 100, false);
        checkText(details.description(), "description", 12000, false);
        checkList(details.highlights(), "highlights", 20, 600);
        checkMap(details.attributes(), "attributes", 60, 1200);
        checkMap(details.observations(), "observations", 20, 1200);
        if (details.options().size() > 20) throw new IllegalArgumentException("options 最多 20 组");
        details.options().forEach((key, values) -> {
            checkText(key, "options key", 80, true);
            checkList(values, "options values", 80, 200);
        });
        checkText(details.sellerName(), "sellerName", 160, false);
        if (hasText(details.sellerUrl())) {
            URI seller = https(details.sellerUrl(), "sellerUrl");
            if (!host(seller).equals(host(source))) throw new IllegalArgumentException("sellerUrl 必须来自商品所在的 Lazada 站点");
        }
        checkList(details.imageUrls(), "imageUrls", 9, 2048);
        for (String value : details.imageUrls()) {
            URI image = https(value, "imageUrls");
            String domain = image.getHost().toLowerCase(java.util.Locale.ROOT);
            if (!(domain.endsWith(".slatic.net") || domain.equals("slatic.net")
                    || domain.endsWith(".lazcdn.com") || domain.equals("lazcdn.com"))) {
                throw new IllegalArgumentException("图片必须来自 Lazada 的 slatic.net 或 lazcdn.com 静态资源域名");
            }
        }
        return source;
    }

    private static URI https(String text, String field) {
        checkText(text, field, 2048, true);
        URI uri;
        try { uri = URI.create(text); } catch (IllegalArgumentException exception) { throw new IllegalArgumentException(field + " 地址无效"); }
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getUserInfo() != null || uri.getPort() != -1
                || uri.getFragment() != null) throw new IllegalArgumentException(field + " 必须为无账号、端口及片段的 HTTPS 地址");
        return uri;
    }

    private static String host(URI uri) { return uri.getHost().toLowerCase(java.util.Locale.ROOT).replaceFirst("^www\\.", ""); }
    private static void checkList(List<String> values, String field, int maxItems, int maxLength) {
        if (values.size() > maxItems) throw new IllegalArgumentException(field + " 数量超限");
        values.forEach(value -> checkText(value, field, maxLength, true));
    }
    private static void checkMap(Map<String, String> values, String field, int maxItems, int maxLength) {
        if (values.size() > maxItems) throw new IllegalArgumentException(field + " 数量超限");
        values.forEach((key, value) -> { checkText(key, field + " key", 80, true); checkText(value, field, maxLength, true); });
    }
    private static void checkText(String value, String field, int maxLength, boolean required) {
        if (value == null) { if (required) throw new IllegalArgumentException(field + " 不能为空"); return; }
        if (value.length() > maxLength || required && value.isBlank()) throw new IllegalArgumentException(field + " 为空或长度超限");
        if (value.indexOf('\0') >= 0) throw new IllegalArgumentException(field + " 含有无效字符");
    }
    private static boolean hasText(String value) { return value != null && !value.isBlank(); }

    private static String description(ExternalProductDetails details) {
        if (hasText(details.description())) return details.description();
        var lines = new ArrayList<String>();
        lines.addAll(details.highlights());
        details.attributes().forEach((key, value) -> lines.add(key + "：" + value));
        if (lines.isEmpty()) return null;
        String text = String.join("\n", lines);
        // Full structured evidence remains in source_detail_payload; keep the editable description bounded.
        return text.length() <= 12000 ? text : text.substring(0, 12000);
    }

    public record DetailResult(UUID productId, long version, List<String> updatedFields,
                               String provider, String sourceUrl, Instant capturedAt) {}
}
