package com.zscq.mall.commerce.operations.infrastructure;

import com.zscq.mall.commerce.operations.domain.OperationsRepository;
import com.zscq.mall.commerce.operations.domain.OperationsSnapshot;
import java.math.BigDecimal;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcOperationsRepository implements OperationsRepository {
    private static final String PAID_STATUSES = "'PAID','FULFILLING','SHIPPED','COMPLETED'";
    private final JdbcClient jdbc;

    JdbcOperationsRepository(JdbcClient jdbc) { this.jdbc = jdbc; }

    @Override
    public OperationsSnapshot load(Instant todayStart, Instant tomorrowStart, Instant yesterdayStart, Instant trendStart) {
        BigDecimal todayRevenue = money("select coalesce(sum(total_amount),0) from orders where created_at>=:start and created_at<:end and status in (" + PAID_STATUSES + ")", todayStart, tomorrowStart);
        BigDecimal yesterdayRevenue = money("select coalesce(sum(total_amount),0) from orders where created_at>=:start and created_at<:end and status in (" + PAID_STATUSES + ")", yesterdayStart, todayStart);
        long pending = count("select count(*) from orders where status in ('PAID','FULFILLING')");
        long newCustomers = countBetween("select count(*) from customers where created_at>=:start and created_at<:end", todayStart, tomorrowStart);
        long activeProducts = count("select count(*) from products where status='ACTIVE'");
        long pendingMerchants = count("select count(*) from merchants where status='PENDING_REVIEW'");
        OperationsSnapshot.MetricSnapshot metrics = new OperationsSnapshot.MetricSnapshot(todayRevenue, yesterdayRevenue, pending, newCustomers, activeProducts, pendingMerchants);

        OperationsSnapshot.SupportSnapshot support = support(todayStart, tomorrowStart);
        String trendSql = """
                select bucket, coalesce(sum(o.total_amount),0) amount
                from generate_series(:start::timestamptz, date_trunc('hour', current_timestamp), interval '1 hour') bucket
                left join orders o on o.created_at>=bucket and o.created_at<bucket+interval '1 hour'
                    and o.status in (%s)
                group by bucket order by bucket
                """.formatted(PAID_STATUSES);
        List<OperationsSnapshot.RevenuePoint> trend = jdbc.sql(trendSql)
                .param("start", dbTime(trendStart)).query((rs, row) -> new OperationsSnapshot.RevenuePoint(instant(rs, "bucket"), rs.getBigDecimal("amount"))).list();

        return new OperationsSnapshot(Instant.now(), metrics, support, trend, findOrders().stream().limit(5).toList(), findProducts(), findCustomers());
    }

    @Override
    public List<OperationsSnapshot.OrderSummary> findOrders() {
        return jdbc.sql("""
                select o.id,o.order_no,o.customer_id,c.display_name,c.email,o.total_amount,o.status,o.created_at
                from orders o left join customers c on c.id=o.customer_id
                order by o.created_at desc limit 100
                """).query(this::order).list();
    }

    @Override
    public List<OperationsSnapshot.ProductSummary> findProducts() {
        return jdbc.sql("""
                select p.id,p.name,p.subtitle,p.brand,p.description,p.weight_kg,p.status,m.store_name,c.name category_name,p.category_id,
                       s.sku_code,s.title sku_title,s.sale_price,s.market_price,s.available_stock,p.updated_at
                from products p
                join merchants m on m.id=p.merchant_id
                left join categories c on c.id=p.category_id
                join product_skus s on s.product_id=p.id
                order by p.updated_at desc
                """).query(this::product).list();
    }

    @Override
    public List<OperationsSnapshot.CustomerSummary> findCustomers() {
        String sql = """
                select c.id,c.display_name,c.email,c.status,c.created_at,c.last_login_at,
                       count(o.id) order_count,
                       coalesce(sum(o.total_amount) filter (where o.status in (%s)),0) total_spend
                from customers c left join orders o on o.customer_id=c.id
                group by c.id order by c.created_at desc limit 100
                """.formatted(PAID_STATUSES);
        return jdbc.sql(sql).query(this::customer).list();
    }

    private OperationsSnapshot.SupportSnapshot support(Instant start, Instant end) {
        Boolean exists = jdbc.sql("select to_regclass('public.ai_conversations') is not null").query(Boolean.class).single();
        if (!Boolean.TRUE.equals(exists)) return new OperationsSnapshot.SupportSnapshot(0, 0, 0, 0, 0);
        return jdbc.sql("""
                select count(*) conversations,
                       count(*) filter (where status='RESOLVED') resolved,
                       count(*) filter (where handed_off_at is not null) handed_off,
                       coalesce(avg(satisfaction_score) filter (where satisfaction_score is not null),0) satisfaction
                from ai_conversations where started_at>=:start and started_at<:end
                """).param("start", dbTime(start)).param("end", dbTime(end)).query((rs, row) -> {
                    long conversations = rs.getLong("conversations");
                    long resolved = rs.getLong("resolved");
                    double rate = conversations == 0 ? 0 : resolved * 100.0 / conversations;
                    return new OperationsSnapshot.SupportSnapshot(conversations, resolved, rs.getLong("handed_off"), rate, rs.getDouble("satisfaction"));
                }).single();
    }

    private BigDecimal money(String sql, Instant start, Instant end) {
        return jdbc.sql(sql).param("start", dbTime(start)).param("end", dbTime(end)).query(BigDecimal.class).single();
    }

    private long count(String sql) { return jdbc.sql(sql).query(Long.class).single(); }

    private long countBetween(String sql, Instant start, Instant end) {
        return jdbc.sql(sql).param("start", dbTime(start)).param("end", dbTime(end)).query(Long.class).single();
    }

    private OperationsSnapshot.OrderSummary order(ResultSet rs, int row) throws SQLException {
        String name = rs.getString("display_name");
        String email = rs.getString("email");
        return new OperationsSnapshot.OrderSummary(rs.getObject("id", UUID.class), rs.getString("order_no"), rs.getObject("customer_id", UUID.class), name == null ? "未命名客户" : name, email, rs.getBigDecimal("total_amount"), rs.getString("status"), instant(rs, "created_at"));
    }

    private OperationsSnapshot.ProductSummary product(ResultSet rs, int row) throws SQLException {
        return new OperationsSnapshot.ProductSummary(rs.getObject("id", UUID.class), rs.getString("name"), rs.getString("subtitle"), rs.getString("brand"), rs.getString("description"), rs.getBigDecimal("weight_kg"), rs.getString("status"), rs.getString("store_name"), rs.getString("category_name"), rs.getObject("category_id", UUID.class), rs.getString("sku_code"), rs.getString("sku_title"), rs.getBigDecimal("sale_price"), rs.getBigDecimal("market_price"), rs.getInt("available_stock"), instant(rs, "updated_at"));
    }

    private OperationsSnapshot.CustomerSummary customer(ResultSet rs, int row) throws SQLException {
        return new OperationsSnapshot.CustomerSummary(rs.getObject("id", UUID.class), rs.getString("display_name"), rs.getString("email"), rs.getString("status"), instant(rs, "created_at"), nullableInstant(rs, "last_login_at"), rs.getLong("order_count"), rs.getBigDecimal("total_spend"));
    }

    private static Instant instant(ResultSet rs, String column) throws SQLException {
        return rs.getObject(column, OffsetDateTime.class).toInstant();
    }

    private static Instant nullableInstant(ResultSet rs, String column) throws SQLException {
        OffsetDateTime value = rs.getObject(column, OffsetDateTime.class);
        return value == null ? null : value.toInstant();
    }

    private static OffsetDateTime dbTime(Instant value) {
        return OffsetDateTime.ofInstant(value, ZoneOffset.UTC);
    }
}
