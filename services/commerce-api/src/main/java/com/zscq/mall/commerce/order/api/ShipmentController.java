package com.zscq.mall.commerce.order.api;

import com.zscq.mall.commerce.config.MarketplaceAuthorization;
import com.zscq.mall.commerce.order.application.ShipmentService;
import com.zscq.mall.commerce.order.domain.Shipment;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.UUID;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/seller/{merchantId}/orders")
public class ShipmentController {
    private final ShipmentService service;
    private final MarketplaceAuthorization authorization;

    public ShipmentController(ShipmentService service, MarketplaceAuthorization authorization) {
        this.service = service;
        this.authorization = authorization;
    }

    @PutMapping("/{orderNo}/shipment")
    Shipment record(
            @PathVariable UUID merchantId,
            @PathVariable String orderNo,
            @Valid @RequestBody ShipmentRequest request,
            Authentication authentication) {
        authorization.requireMerchant(authentication, merchantId);
        return service.record(
                merchantId,
                orderNo,
                request.carrierCode(),
                request.carrierName(),
                request.trackingNo(),
                request.status(),
                request.latestEvent());
    }

    record ShipmentRequest(
            @NotBlank @Size(max = 40) String carrierCode,
            @NotBlank @Size(max = 100) String carrierName,
            @NotBlank @Size(max = 100) String trackingNo,
            @NotBlank @Pattern(regexp = "LABEL_CREATED|IN_TRANSIT|OUT_FOR_DELIVERY|DELIVERED|EXCEPTION") String status,
            @Size(max = 500) String latestEvent) {}
}
