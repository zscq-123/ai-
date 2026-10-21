package com.zscq.mall.commerce.storedesign.api;

import com.zscq.mall.commerce.storedesign.application.StoreDesignService;
import com.zscq.mall.commerce.storedesign.domain.PublishedStoreDesign;
import com.zscq.mall.commerce.storedesign.domain.StoreChannel;
import java.util.NoSuchElementException;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/public/stores")
public class PublicStoreDesignController {
    private final StoreDesignService service;

    public PublicStoreDesignController(StoreDesignService service) {
        this.service = service;
    }

    @GetMapping("/{merchantId}/{channel}")
    PublishedStoreDesign published(@PathVariable UUID merchantId, @PathVariable StoreChannel channel) {
        try {
            return service.published(merchantId, channel);
        } catch (NoSuchElementException exception) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, exception.getMessage(), exception);
        }
    }
}
