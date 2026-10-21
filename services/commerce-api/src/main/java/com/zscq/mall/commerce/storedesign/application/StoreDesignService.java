package com.zscq.mall.commerce.storedesign.application;

import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import com.zscq.mall.commerce.storedesign.domain.PublishedStoreDesign;
import com.zscq.mall.commerce.storedesign.domain.StoreChannel;
import com.zscq.mall.commerce.storedesign.domain.StoreDesign;
import com.zscq.mall.commerce.storedesign.domain.StoreDesignRepository;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class StoreDesignService {
    private final StoreDesignRepository repository;
    private final StoreDesignValidator validator;
    private final ObjectMapper objectMapper;

    public StoreDesignService(StoreDesignRepository repository, StoreDesignValidator validator, ObjectMapper objectMapper) {
        this.repository = repository;
        this.validator = validator;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public StoreDesign draft(UUID merchantId, StoreChannel channel) {
        String storeName = requireActiveMerchant(merchantId);
        return repository.find(merchantId, channel)
                .orElseGet(() -> new StoreDesign(merchantId, channel, 0, null,
                        defaultConfig(storeName, channel), null, null, null));
    }

    @Transactional
    public StoreDesign saveDraft(UUID merchantId, StoreChannel channel, long expectedVersion, JsonNode config) {
        requireActiveMerchant(merchantId);
        validator.validate(config);
        return repository.saveDraft(merchantId, channel, expectedVersion, config);
    }

    @Transactional
    public StoreDesign publish(UUID merchantId, StoreChannel channel) {
        requireActiveMerchant(merchantId);
        StoreDesign existing = repository.find(merchantId, channel)
                .orElseThrow(() -> new IllegalStateException("Save a draft before publishing"));
        validator.validate(existing.draft());
        return repository.publish(merchantId, channel);
    }

    @Transactional(readOnly = true)
    public PublishedStoreDesign published(UUID merchantId, StoreChannel channel) {
        return repository.findPublished(merchantId, channel)
                .orElseThrow(() -> new NoSuchElementException("Published store page not found"));
    }

    private String requireActiveMerchant(UUID merchantId) {
        return repository.activeMerchantName(merchantId)
                .orElseThrow(() -> new NoSuchElementException("Active merchant not found"));
    }

    private JsonNode defaultConfig(String storeName, StoreChannel channel) {
        try {
            return objectMapper.valueToTree(Map.of(
                "theme", Map.of(
                        "primaryColor", "#e1251b",
                        "backgroundColor", "#f5f5f7",
                        "textColor", "#1d1d1f"),
                "modules", java.util.List.of(
                        Map.of("id", "banner", "type", "BANNER", "visible", true,
                                "data", Map.of("title", storeName, "subtitle", channel == StoreChannel.WEB ? "用心服务每一次采购" : "店铺好物", "imageUrl", "")),
                        Map.of("id", "store-info", "type", "STORE_INFO", "visible", true,
                                "data", Map.of("title", storeName, "description", "品质商品与专业服务")),
                        Map.of("id", "products", "type", "PRODUCT_GRID", "visible", true,
                                "data", Map.of("title", "店铺精选", "limit", channel == StoreChannel.WEB ? 6 : 4)))));
        } catch (JacksonException exception) {
            throw new IllegalStateException("Unable to create default store design", exception);
        }
    }
}
