package com.zscq.mall.commerce.storedesign.application;

import tools.jackson.databind.JsonNode;
import java.net.URI;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class StoreDesignValidator {
    private static final Set<String> MODULE_TYPES = Set.of(
            "BANNER", "STORE_INFO", "PRODUCT_GRID", "ANNOUNCEMENT", "COUPON");
    private static final Pattern COLOR = Pattern.compile("^#[0-9a-fA-F]{6}$");

    public void validate(JsonNode config) {
        if (config == null || !config.isObject()) {
            throw new IllegalArgumentException("Store design must be a JSON object");
        }
        validateTheme(config.path("theme"));
        JsonNode modules = config.path("modules");
        if (!modules.isArray() || modules.isEmpty() || modules.size() > 30) {
            throw new IllegalArgumentException("Store design must contain between 1 and 30 modules");
        }
        Set<String> ids = new HashSet<>();
        modules.forEach(module -> validateModule(module, ids));
    }

    private void validateTheme(JsonNode theme) {
        if (!theme.isObject()) {
            throw new IllegalArgumentException("Theme must be an object");
        }
        for (String field : Set.of("primaryColor", "backgroundColor", "textColor")) {
            String value = theme.path(field).asText("");
            if (!COLOR.matcher(value).matches()) {
                throw new IllegalArgumentException(field + " must use #RRGGBB format");
            }
        }
    }

    private void validateModule(JsonNode module, Set<String> ids) {
        if (!module.isObject()) {
            throw new IllegalArgumentException("Every module must be an object");
        }
        String id = module.path("id").asText("").trim();
        if (id.isEmpty() || id.length() > 80 || !ids.add(id)) {
            throw new IllegalArgumentException("Module ids must be non-empty and unique");
        }
        String type = module.path("type").asText("");
        if (!MODULE_TYPES.contains(type)) {
            throw new IllegalArgumentException("Unsupported module type: " + type);
        }
        if (!module.path("visible").isBoolean() || !module.path("data").isObject()) {
            throw new IllegalArgumentException("Every module needs visible and data fields");
        }
        JsonNode data = module.path("data");
        data.properties().forEach(entry -> {
            if (entry.getValue().isTextual() && entry.getValue().asText().length() > 1000) {
                throw new IllegalArgumentException("Module text is too long");
            }
        });
        String imageUrl = data.path("imageUrl").asText("").trim();
        if (!imageUrl.isEmpty() && !safeImageUrl(imageUrl)) {
            throw new IllegalArgumentException("Image URL must use http or https");
        }
        int limit = data.path("limit").asInt(6);
        if ("PRODUCT_GRID".equals(type) && (limit < 1 || limit > 24)) {
            throw new IllegalArgumentException("Product module limit must be between 1 and 24");
        }
    }

    private boolean safeImageUrl(String value) {
        try {
            URI uri = URI.create(value);
            return "http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme());
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }
}
