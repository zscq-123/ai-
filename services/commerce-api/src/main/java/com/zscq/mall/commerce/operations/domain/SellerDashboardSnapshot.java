package com.zscq.mall.commerce.operations.domain;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record SellerDashboardSnapshot(
        Instant generatedAt,
        OperationsSnapshot.MerchantSummary merchant,
        SellerMetrics metrics,
        OperationsSnapshot.SupportSnapshot support,
        List<OperationsSnapshot.OrderSummary> recentOrders,
        List<OperationsSnapshot.ProductSummary> products,
        List<OperationsSnapshot.SupportConversationSummary> conversations) {

    public record SellerMetrics(
            BigDecimal todayRevenue,
            long pendingFulfillment,
            long activeProducts,
            long lowStockProducts) {}
}
