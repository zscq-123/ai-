package com.zscq.mall.commerce.catalog.infrastructure;

import com.zscq.mall.commerce.catalog.domain.ProductStatus;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface JpaCatalogRepository extends JpaRepository<ProductEntity, UUID> {
    @Query("select p from ProductEntity p where p.status = :status and (:categoryId is null or p.categoryId = :categoryId) and (lower(p.name) like lower(concat('%', :query, '%')) or lower(coalesce(p.subtitle, '')) like lower(concat('%', :query, '%'))) order by p.updatedAt desc")
    List<ProductEntity> search(@Param("status") ProductStatus status, @Param("query") String query, @Param("categoryId") UUID categoryId);
    Optional<ProductEntity> findByIdAndStatus(UUID id, ProductStatus status);
}
