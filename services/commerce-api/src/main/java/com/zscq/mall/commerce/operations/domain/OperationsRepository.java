package com.zscq.mall.commerce.operations.domain;

import java.time.Instant;
import java.util.List;

public interface OperationsRepository {
    OperationsSnapshot load(Instant todayStart, Instant tomorrowStart, Instant yesterdayStart, Instant trendStart);
    List<OperationsSnapshot.OrderSummary> findOrders();
    List<OperationsSnapshot.ProductSummary> findProducts();
    List<OperationsSnapshot.CustomerSummary> findCustomers();
}
