package com.zscq.mall.commerce.merchant.application;

import com.zscq.mall.commerce.merchant.domain.Merchant;
import com.zscq.mall.commerce.merchant.domain.MerchantRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MerchantService {
    private final MerchantRepository repository;
    private final com.zscq.mall.commerce.merchant.domain.MerchantAuditRepository audit;
    public MerchantService(MerchantRepository repository, com.zscq.mall.commerce.merchant.domain.MerchantAuditRepository audit) { this.repository = repository; this.audit = audit; }

    @Transactional
    public Merchant apply(String legalName, String storeName, String contactName, String phone, String licenseNo) {
        if (repository.existsByBusinessLicenseNo(licenseNo)) throw new IllegalArgumentException("Business license already registered");
        return repository.save(Merchant.apply(legalName, storeName, contactName, phone, licenseNo));
    }

    @Transactional
    public Merchant review(UUID id, boolean approved, String reason) {
        Merchant merchant = repository.findById(id).orElseThrow(() -> new IllegalArgumentException("Merchant not found"));
        Merchant reviewed = repository.save(approved ? merchant.approve() : merchant.reject(reason));
        audit.record(approved ? "MERCHANT_APPROVED" : "MERCHANT_REJECTED", id, "{\"status\":\"" + reviewed.status() + "\"}");
        return reviewed;
    }

    @Transactional(readOnly = true)
    public List<Merchant> list() { return repository.findAll(); }
}
