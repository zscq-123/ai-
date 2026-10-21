package com.zscq.mall.commerce.storedesign.api;

import tools.jackson.databind.JsonNode;
import com.zscq.mall.commerce.config.MarketplaceAuthorization;
import com.zscq.mall.commerce.storedesign.application.StoreDesignService;
import com.zscq.mall.commerce.storedesign.domain.StoreChannel;
import com.zscq.mall.commerce.storedesign.domain.StoreDesign;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.NoSuchElementException;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/seller/{merchantId}/store-design")
public class StoreDesignController {
    private final StoreDesignService service;
    private final MarketplaceAuthorization authorization;

    public StoreDesignController(StoreDesignService service, MarketplaceAuthorization authorization) {
        this.service = service;
        this.authorization = authorization;
    }

    @GetMapping({"/{channel}/draft", "/{channel}/preview"})
    StoreDesign draft(@PathVariable UUID merchantId, @PathVariable StoreChannel channel,
                      Authentication authentication) {
        authorize(authentication, merchantId);
        return notFound(() -> service.draft(merchantId, channel));
    }

    @PutMapping("/{channel}/draft")
    StoreDesign saveDraft(@PathVariable UUID merchantId, @PathVariable StoreChannel channel,
                          @Valid @RequestBody SaveDraftRequest request, Authentication authentication) {
        authorize(authentication, merchantId);
        return notFound(() -> service.saveDraft(merchantId, channel, request.expectedVersion(), request.config()));
    }

    @PostMapping("/{channel}/publish")
    StoreDesign publish(@PathVariable UUID merchantId, @PathVariable StoreChannel channel,
                        Authentication authentication) {
        authorize(authentication, merchantId);
        return notFound(() -> service.publish(merchantId, channel));
    }

    private void authorize(Authentication authentication, UUID merchantId) {
        authorization.requireMerchant(authentication, merchantId);
    }

    private <T> T notFound(java.util.function.Supplier<T> action) {
        try {
            return action.get();
        } catch (NoSuchElementException exception) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, exception.getMessage(), exception);
        }
    }

    public record SaveDraftRequest(@jakarta.validation.constraints.PositiveOrZero long expectedVersion,
                                   @NotNull JsonNode config) { }
}
