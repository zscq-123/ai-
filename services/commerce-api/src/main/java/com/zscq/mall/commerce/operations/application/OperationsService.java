package com.zscq.mall.commerce.operations.application;

import com.zscq.mall.commerce.operations.domain.OperationsRepository;
import com.zscq.mall.commerce.operations.domain.OperationsSnapshot;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
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
    public OperationsSnapshot dashboard() {
        ZonedDateTime now = ZonedDateTime.now(clock).withZoneSameInstant(businessZone);
        Instant todayStart = now.toLocalDate().atStartOfDay(businessZone).toInstant();
        Instant tomorrowStart = now.toLocalDate().plusDays(1).atStartOfDay(businessZone).toInstant();
        Instant yesterdayStart = now.toLocalDate().minusDays(1).atStartOfDay(businessZone).toInstant();
        return repository.load(todayStart, tomorrowStart, yesterdayStart, now.minusHours(11).withMinute(0).withSecond(0).withNano(0).toInstant());
    }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.OrderSummary> orders() { return repository.findOrders(); }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.ProductSummary> products() { return repository.findProducts(); }

    @Transactional(readOnly = true)
    public List<OperationsSnapshot.CustomerSummary> customers() { return repository.findCustomers(); }
}
