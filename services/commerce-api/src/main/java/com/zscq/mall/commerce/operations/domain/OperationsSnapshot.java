package com.zscq.mall.commerce.operations.domain;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record OperationsSnapshot(
        Instant generatedAt,
        MetricSnapshot metrics,
        SupportSnapshot support,
        List<RevenuePoint> revenueTrend,
        List<OrderSummary> recentOrders,
        List<ProductSummary> products,
        List<CustomerSummary> customers) {

    public record MetricSnapshot(
            BigDecimal todayRevenue,
            BigDecimal yesterdayRevenue,
            long pendingFulfillment,
            long newCustomers,
            long activeProducts,
            long pendingMerchants) {}

    public record SupportSnapshot(
            long conversationsToday,
            long resolvedToday,
            long handedOffToday,
            double resolutionRate,
            double satisfactionRate) {}

    public record RevenuePoint(Instant bucket, BigDecimal amount) {}

    public record OrderSummary(
            UUID id,
            String orderNo,
            UUID customerId,
            String customerName,
            String customerEmail,
            BigDecimal totalAmount,
            String status,
            Instant createdAt) {}

    public record ProductSummary(
            UUID id,
            String name,
            String subtitle,
            String brand,
            String description,
            BigDecimal weightKg,
            String status,
            String merchantName,
            String categoryName,
            UUID categoryId,
            String skuCode,
            String skuTitle,
            BigDecimal salePrice,
            BigDecimal marketPrice,
            int availableStock,
            long version,
            Instant updatedAt,
            String coverImageUrl,
            String currency) {}

    public record CustomerSummary(
            UUID id,
            String displayName,
            String email,
            String status,
            Instant createdAt,
            Instant lastLoginAt,
            long orderCount,
            BigDecimal totalSpend) {}

    public record MerchantSummary(UUID id, String storeName, String legalName, String status) {}

    public record SupportConversationSummary(
            UUID id,
            UUID merchantId,
            UUID customerId,
            String status,
            Instant startedAt,
            Instant handedOffAt,
            Instant resolvedAt,
            BigDecimal satisfactionScore,
            long messageCount,
            Instant lastMessageAt,
            String lastIntent) {}
}
