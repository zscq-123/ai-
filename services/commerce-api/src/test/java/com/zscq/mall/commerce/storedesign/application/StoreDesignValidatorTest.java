package com.zscq.mall.commerce.storedesign.application;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

import tools.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

class StoreDesignValidatorTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final StoreDesignValidator validator = new StoreDesignValidator();

    @Test
    void acceptsSupportedModules() throws Exception {
        var config = mapper.readTree("""
                {"theme":{"primaryColor":"#e1251b","backgroundColor":"#ffffff","textColor":"#1d1d1f"},
                 "modules":[{"id":"hero","type":"BANNER","visible":true,
                 "data":{"title":"Store","imageUrl":"https://cdn.example.com/hero.jpg"}}]}
                """);
        assertDoesNotThrow(() -> validator.validate(config));
    }

    @Test
    void rejectsDuplicateModuleIds() throws Exception {
        var config = mapper.readTree("""
                {"theme":{"primaryColor":"#e1251b","backgroundColor":"#ffffff","textColor":"#1d1d1f"},
                 "modules":[{"id":"same","type":"BANNER","visible":true,"data":{}},
                 {"id":"same","type":"ANNOUNCEMENT","visible":true,"data":{}}]}
                """);
        assertThrows(IllegalArgumentException.class, () -> validator.validate(config));
    }

    @Test
    void rejectsUnsafeImageUrl() throws Exception {
        var config = mapper.readTree("""
                {"theme":{"primaryColor":"#e1251b","backgroundColor":"#ffffff","textColor":"#1d1d1f"},
                 "modules":[{"id":"hero","type":"BANNER","visible":true,
                 "data":{"imageUrl":"javascript:alert(1)"}}]}
                """);
        assertThrows(IllegalArgumentException.class, () -> validator.validate(config));
    }

    @Test
    void rejectsInvalidThemeColor() throws Exception {
        var config = mapper.readTree("""
                {"theme":{"primaryColor":"red","backgroundColor":"#ffffff","textColor":"#1d1d1f"},
                 "modules":[{"id":"hero","type":"BANNER","visible":true,"data":{}}]}
                """);
        assertThrows(IllegalArgumentException.class, () -> validator.validate(config));
    }
}
