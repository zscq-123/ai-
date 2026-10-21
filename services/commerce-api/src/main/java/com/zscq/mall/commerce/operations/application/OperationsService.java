package com.zscq.mall.commerce.operations.application;

import com.zscq.mall.commerce.operations.domain.OperationsRepository;
import com.zscq.mall.commerce.operations.domain.OperationsSnapshot;
import com.zscq.mall.commerce.operations.domain.SellerDashboardSnapshot;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OperationsService {
    private final OperationsRepository repository;
    private final Clock clock;
    private final ZoneId businessZone;

    @Autowired
    public OperationsService(
            OperationsRepository repository,
            @Value("${commerce.operations.time-zone:Asia/Shanghai}") String timeZone) {
        this(repository, Clock.systemUTC(), ZoneId.of(timeZone));
    }

    OperationsService(OperationsRepository repository, Clock clock, ZoneId businessZone) {
        this.repository = repository;
        this.clock = clock;
        this.businessZone = businessZone;
    }

    @Transactional(readOnly = true)
    public OperationsSnapshot dashboard(UUID merchantId) {
        ZonedDateTime now = ZonedDateTime.now(clock).withZoneSameInstant(businessZone);
        Instant todayStart = now.toLocalDate().atStartOfDay(businessZone).toInstant();
        Instant tomorrowStart = now.toLocalDate().plusDays(1).atStartOfDay(businessZone).toInstant();
        Instant yesterdayStart = now.toLocalDate().minusDays(1).atStartOfDay(businessZone).toInstant();
        return repository.load(merchantId, todayStart, tomorrowStart, yesterdayStart, now.minusHours(11).withMinute(0).withSecond(0).withNano(0).toInstant());
    }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.OrderSummary> orders(UUID merchantId) { return repository.findOrders(merchantId); }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.ProductSummary> products(UUID merchantId) { return repository.findProducts(merchantId); }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.CustomerSummary> customers(UUID merchantId) { return repository.findCustomers(merchantId); }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.MerchantSummary> activeMerchants() { return repository.findActiveMerchants(); }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.SupportConversationSummary> supportConversations(UUID merchantId) {
        return repository.findSupportConversations(merchantId);
    }

    @Transactional(readOnly = true)
    public SellerDashboardSnapshot sellerDashboard(UUID merchantId) {
        OperationsSnapshot.MerchantSummary merchant = activeMerchants().stream()
                .filter(candidate -> candidate.id().equals(merchantId))
                .findFirst()
                .orElseThrow();
        OperationsSnapshot dashboard = dashboard(merchantId);
        List<OperationsSnapshot.SupportConversationSummary> conversations = supportConversations(merchantId);
        long lowStockProducts = dashboard.products().stream()
                .filter(product -> product.availableStock() < 10)
                .count();
        return new SellerDashboardSnapshot(
                dashboard.generatedAt(), merchant,
                new SellerDashboardSnapshot.SellerMetrics(
                        dashboard.metrics().todayRevenue(), dashboard.metrics().pendingFulfillment(),
                        dashboard.metrics().activeProducts(), lowStockProducts),
                dashboard.support(), dashboard.recentOrders(), dashboard.products(), conversations);
    }
}
