package com.zscq.mall.commerce.operations.api;

import com.zscq.mall.commerce.operations.application.OperationsService;
import com.zscq.mall.commerce.operations.domain.OperationsSnapshot;
import com.zscq.mall.commerce.operations.domain.SellerDashboardSnapshot;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/seller")
public class SellerOperationsController {
    private final OperationsService service;

    public SellerOperationsController(OperationsService service) {
        this.service = service;
    }

    @GetMapping("/merchants")
    List<OperationsSnapshot.MerchantSummary> merchants() {
        return service.activeMerchants();
    }

    @GetMapping("/{merchantId}/dashboard")
    SellerDashboardSnapshot dashboard(@PathVariable UUID merchantId) {
        try {
            return service.sellerDashboard(merchantId);
        } catch (java.util.NoSuchElementException exception) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Active merchant not found", exception);
        }
    }

    @GetMapping("/{merchantId}/products")
    List<OperationsSnapshot.ProductSummary> products(@PathVariable UUID merchantId) {
        return service.products(merchantId);
    }

    @GetMapping("/{merchantId}/orders")
    List<OperationsSnapshot.OrderSummary> orders(@PathVariable UUID merchantId) {
        return service.orders(merchantId);
    }

    @GetMapping("/{merchantId}/support/conversations")
    List<OperationsSnapshot.SupportConversationSummary> supportConversations(@PathVariable UUID merchantId) {
        return service.supportConversations(merchantId);
    }
}
