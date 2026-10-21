package com.zscq.mall.commerce.operations.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public interface OperationsRepository {
    OperationsSnapshot load(UUID merchantId, Instant todayStart, Instant tomorrowStart, Instant yesterdayStart, Instant trendStart);
    List<OperationsSnapshot.OrderSummary> findOrders(UUID merchantId);
    List<OperationsSnapshot.ProductSummary> findProducts(UUID merchantId);
    List<OperationsSnapshot.CustomerSummary> findCustomers(UUID merchantId);
    List<OperationsSnapshot.MerchantSummary> findActiveMerchants();
    List<OperationsSnapshot.SupportConversationSummary> findSupportConversations(UUID merchantId);
}
