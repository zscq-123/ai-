package com.zscq.mall.commerce.merchant.infrastructure;

import com.zscq.mall.commerce.merchant.domain.*;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
class MerchantRepositoryAdapter implements MerchantRepository {
    private final JpaMerchantRepository repository;
    MerchantRepositoryAdapter(JpaMerchantRepository repository) { this.repository = repository; }
    public Merchant save(Merchant merchant) { return repository.save(new MerchantEntity(merchant)).toDomain(); }
    public Optional<Merchant> findById(UUID id) { return repository.findById(id).map(MerchantEntity::toDomain); }
    public boolean existsByBusinessLicenseNo(String number) { return repository.existsByBusinessLicenseNo(number); }
    public List<Merchant> findAll() { return repository.findAll().stream().map(MerchantEntity::toDomain).toList(); }
}
