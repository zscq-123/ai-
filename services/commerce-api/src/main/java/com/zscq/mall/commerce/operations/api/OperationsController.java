package com.zscq.mall.commerce.operations.api;

import com.zscq.mall.commerce.operations.application.OperationsService;
import com.zscq.mall.commerce.operations.domain.OperationsSnapshot;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/operations")
public class OperationsController {
    private final OperationsService service;

    public OperationsController(OperationsService service) { this.service = service; }

    @GetMapping("/dashboard")
    OperationsSnapshot dashboard(@RequestParam(required = false) UUID merchantId) { return service.dashboard(merchantId); }

    @GetMapping("/orders")
    List<OperationsSnapshot.OrderSummary> orders(@RequestParam(required = false) UUID merchantId) { return service.orders(merchantId); }

    @GetMapping("/products")
    List<OperationsSnapshot.ProductSummary> products(@RequestParam(required = false) UUID merchantId) { return service.products(merchantId); }

    @GetMapping("/customers")
    List<OperationsSnapshot.CustomerSummary> customers(@RequestParam(required = false) UUID merchantId) { return service.customers(merchantId); }
}
