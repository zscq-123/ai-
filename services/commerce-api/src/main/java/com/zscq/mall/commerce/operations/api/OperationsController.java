package com.zscq.mall.commerce.operations.api;

import com.zscq.mall.commerce.operations.application.OperationsService;
import com.zscq.mall.commerce.operations.domain.OperationsSnapshot;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/operations")
public class OperationsController {
    private final OperationsService service;

    public OperationsController(OperationsService service) { this.service = service; }

    @GetMapping("/dashboard")
    OperationsSnapshot dashboard() { return service.dashboard(); }

    @GetMapping("/orders")
    List<OperationsSnapshot.OrderSummary> orders() { return service.orders(); }

    @GetMapping("/products")
    List<OperationsSnapshot.ProductSummary> products() { return service.products(); }

    @GetMapping("/customers")
    List<OperationsSnapshot.CustomerSummary> customers() { return service.customers(); }
}
