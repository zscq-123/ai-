package com.zscq.mall.commerce.order.api;
import com.zscq.mall.commerce.order.application.OrderService;
import com.zscq.mall.commerce.order.domain.PurchaseOrder;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import com.zscq.mall.commerce.config.MarketplaceAuthorization;

@RestController @RequestMapping("/api/orders")
public class OrderController {
    private final OrderService service;
    private final MarketplaceAuthorization authorization;
    public OrderController(OrderService service, MarketplaceAuthorization authorization) { this.service=service; this.authorization=authorization; }
    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    PurchaseOrder create(@RequestHeader("Idempotency-Key") String key, @Valid @RequestBody CreateOrderRequest r,
                         Authentication authentication) {
        UUID customerId = authorization.customerId(authentication);
        return service.create(customerId, key, r.items().stream().map(i -> new OrderService.Item(i.skuId(), i.quantity())).toList());
    }
    record CreateOrderRequest(@NotEmpty List<@Valid Item> items) {}
    record Item(@NotNull UUID skuId, @Positive int quantity) {}
}
