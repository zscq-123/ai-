package com.zscq.mall.commerce.externalcatalog.infrastructure;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import java.math.BigDecimal;
import java.sql.ResultSet;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

class JdbcExternalCatalogRepositoryTest {
    @Test
    void resyncsActualSkuIdentityAfterMerchantChangesSkuCodeWithoutInsertingAnotherSku() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        UUID productId = UUID.randomUUID();
        UUID actualSkuId = UUID.randomUUID();
        when(jdbc.query(contains("FROM product_skus WHERE product_id=?"),
                org.mockito.ArgumentMatchers.<RowMapper<UUID>>any(), eq(productId)))
                .thenReturn(List.of(actualSkuId));
        var source = new ExternalCatalogProduct("LAZADA", "SG:123", "NEW-EXTERNAL-SKU",
                "https://www.lazada.sg/products/pdp-i123-s456.html", "Updated source title", null, null, null,
                "Seller", new BigDecimal("9.90"), null, "SGD", 8, 0, null, null, "{}");

        new JdbcExternalCatalogRepository(jdbc).synchronizeSku(productId, source);

        var sql = ArgumentCaptor.forClass(String.class);
        verify(jdbc).query(contains("FOR UPDATE"), org.mockito.ArgumentMatchers.<RowMapper<UUID>>any(), eq(productId));
        verify(jdbc).update(sql.capture(), eq("Updated source title"), eq(new BigDecimal("9.90")), isNull(), eq(8),
                eq("NEW-EXTERNAL-SKU"), eq(actualSkuId));
        assertThat(sql.getValue()).contains("UPDATE product_skus", "WHERE id=?").doesNotContain("sku_code", "INSERT");
        verifyNoMoreInteractions(jdbc);
    }

    @Test
    void locksPublishedProductThenSkipsWithoutMutatingMerchantProductOrSku() throws Exception {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        ResultSet row = mock(ResultSet.class);
        UUID productId = UUID.randomUUID();
        UUID merchantId = UUID.randomUUID();
        when(row.getObject("id", UUID.class)).thenReturn(productId);
        when(row.getObject("merchant_id", UUID.class)).thenReturn(merchantId);
        when(row.getString("status")).thenReturn("ACTIVE");
        doAnswer(invocation -> {
            RowMapper<?> mapper = invocation.getArgument(1);
            return List.of(mapper.mapRow(row, 0));
        }).when(jdbc).query(any(String.class), org.mockito.ArgumentMatchers.<RowMapper<Object>>any(), eq("LAZADA"), eq("SG:123"));

        var product = new ExternalCatalogProduct("LAZADA", "SG:123", "SKU-1",
                "https://www.lazada.sg/products/pdp-i123-s456.html", "Changed title", null, null, null,
                "Changed seller", new BigDecimal("1.00"), null, "SGD", 5, 0, null, null, "{}");
        var result = new JdbcExternalCatalogRepository(jdbc).upsert(product);

        assertThat(result.skipped()).isTrue();
        assertThat(result.skipReason()).contains("ACTIVE", "retained existing content");
        assertThat(result.productId()).isEqualTo(productId);
        assertThat(result.merchantId()).isEqualTo(merchantId);
        verify(jdbc).query(contains("FOR UPDATE"), org.mockito.ArgumentMatchers.<RowMapper<Object>>any(), eq("LAZADA"), eq("SG:123"));
        verifyNoMoreInteractions(jdbc);
    }
}
