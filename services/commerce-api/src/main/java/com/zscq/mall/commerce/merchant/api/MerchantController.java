package com.zscq.mall.commerce.merchant.api;

import com.zscq.mall.commerce.merchant.application.MerchantService;
import com.zscq.mall.commerce.merchant.domain.Merchant;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class MerchantController {
    private final MerchantService service;
    public MerchantController(MerchantService service) { this.service = service; }

    @PostMapping("/public/merchant-applications")
    @ResponseStatus(HttpStatus.CREATED)
    Merchant apply(@Valid @RequestBody ApplyMerchantRequest request) {
        return service.apply(request.legalName(), request.storeName(), request.contactName(), request.contactPhone(), request.businessLicenseNo());
    }

    @GetMapping("/merchants")
    List<Merchant> list() { return service.list(); }

    @PostMapping("/merchants/{id}/review")
    Merchant review(@PathVariable UUID id, @Valid @RequestBody ReviewMerchantRequest request) {
        return service.review(id, request.approved(), request.reason());
    }

    record ApplyMerchantRequest(@NotBlank String legalName, @NotBlank String storeName,
                                @NotBlank String contactName, @NotBlank String contactPhone,
                                @NotBlank String businessLicenseNo) {}
    record ReviewMerchantRequest(boolean approved, String reason) {}
}
