package com.zscq.mall.commerce.order.api;
import com.zscq.mall.commerce.order.application.OrderService;
import com.zscq.mall.commerce.order.domain.PurchaseOrder;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/orders")
public class OrderController {
    private final OrderService service;
    public OrderController(OrderService service) { this.service=service; }
    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    PurchaseOrder create(@RequestHeader("Idempotency-Key") String key, @Valid @RequestBody CreateOrderRequest r) {
        return service.create(r.customerId(), key, r.items().stream().map(i -> new OrderService.Item(i.skuId(), i.quantity())).toList());
    }
    record CreateOrderRequest(@NotNull UUID customerId, @NotEmpty List<@Valid Item> items) {}
    record Item(@NotNull UUID skuId, @Positive int quantity) {}
}
