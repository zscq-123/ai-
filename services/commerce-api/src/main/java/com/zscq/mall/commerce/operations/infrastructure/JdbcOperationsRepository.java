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
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcOperationsRepository implements OperationsRepository {
    private static final String PAID_STATUSES = "'PAID','FULFILLING','SHIPPED','COMPLETED'";
    private final JdbcClient jdbc;

    JdbcOperationsRepository(JdbcClient jdbc) { this.jdbc = jdbc; }

    @Override
    public OperationsSnapshot load(UUID merchantId, Instant todayStart, Instant tomorrowStart, Instant yesterdayStart, Instant trendStart) {
        String orderScope = scope(merchantId, "merchant_id");
        BigDecimal todayRevenue = money("select coalesce(sum(total_amount),0) from orders where created_at>=:start and created_at<:end and status in (" + PAID_STATUSES + ")" + orderScope, merchantId, todayStart, tomorrowStart);
        BigDecimal yesterdayRevenue = money("select coalesce(sum(total_amount),0) from orders where created_at>=:start and created_at<:end and status in (" + PAID_STATUSES + ")" + orderScope, merchantId, yesterdayStart, todayStart);
        long pending = count("select count(*) from orders where status in ('PAID','FULFILLING')" + orderScope, merchantId);
        String customerScope = merchantId == null ? "" : " and exists (select 1 from orders o where o.customer_id=customers.id and o.merchant_id=:merchantId)";
        long newCustomers = countBetween("select count(*) from customers where created_at>=:start and created_at<:end" + customerScope, merchantId, todayStart, tomorrowStart);
        long activeProducts = count("select count(*) from products where status='ACTIVE'" + scope(merchantId, "merchant_id"), merchantId);
        long pendingMerchants = count("select count(*) from merchants where status='PENDING_REVIEW'" + scope(merchantId, "id"), merchantId);
        OperationsSnapshot.MetricSnapshot metrics = new OperationsSnapshot.MetricSnapshot(todayRevenue, yesterdayRevenue, pending, newCustomers, activeProducts, pendingMerchants);

        OperationsSnapshot.SupportSnapshot support = support(merchantId, todayStart, tomorrowStart);
        String trendSql = """
                select bucket, coalesce(sum(o.total_amount),0) amount
                from generate_series(:start::timestamptz, date_trunc('hour', current_timestamp), interval '1 hour') bucket
                left join orders o on o.created_at>=bucket and o.created_at<bucket+interval '1 hour'
                    and o.status in (%s)
                    %s
                group by bucket order by bucket
                """.formatted(PAID_STATUSES, scope(merchantId, "o.merchant_id"));
        List<OperationsSnapshot.RevenuePoint> trend = jdbc.sql(trendSql)
                .param("start", dbTime(trendStart)).params(scopeParams(merchantId))
                .query((rs, row) -> new OperationsSnapshot.RevenuePoint(instant(rs, "bucket"), rs.getBigDecimal("amount"))).list();

        return new OperationsSnapshot(Instant.now(), metrics, support, trend, findOrders(merchantId).stream().limit(5).toList(), findProducts(merchantId), findCustomers(merchantId));
    }

    @Override
    public List<OperationsSnapshot.OrderSummary> findOrders(UUID merchantId) {
        return jdbc.sql("""
                select o.id,o.order_no,o.customer_id,c.display_name,c.email,o.total_amount,o.status,o.created_at
                from orders o left join customers c on c.id=o.customer_id
                %s
                order by o.created_at desc limit 100
                """.formatted(whereScope(merchantId, "o.merchant_id"))).params(scopeParams(merchantId)).query(this::order).list();
    }

    @Override
    public List<OperationsSnapshot.ProductSummary> findProducts(UUID merchantId) {
        return jdbc.sql("""
                select p.id,p.name,p.subtitle,p.brand,p.description,p.weight_kg,p.status,m.store_name,c.name category_name,p.category_id,
                       s.sku_code,s.title sku_title,s.sale_price,s.market_price,s.available_stock,p.version,p.updated_at,
                       case when p.image_urls is null then p.source_image_url else p.image_urls->>0 end cover_image_url,
                       coalesce(nullif(p.source_currency,''),'CNY') currency
                from products p
                join merchants m on m.id=p.merchant_id
                left join categories c on c.id=p.category_id
                join product_skus s on s.product_id=p.id
                %s
                order by p.updated_at desc
                """.formatted(whereScope(merchantId, "p.merchant_id"))).params(scopeParams(merchantId)).query(this::product).list();
    }

    @Override
    public List<OperationsSnapshot.CustomerSummary> findCustomers(UUID merchantId) {
        String sql = """
                select c.id,c.display_name,c.email,c.status,c.created_at,c.last_login_at,
                       count(o.id) order_count,
                       coalesce(sum(o.total_amount) filter (where o.status in (%s)),0) total_spend
                from customers c left join orders o on o.customer_id=c.id %s
                %s
                group by c.id order by c.created_at desc limit 100
                """.formatted(PAID_STATUSES,
                merchantId == null ? "" : "and o.merchant_id=:merchantId",
                merchantId == null ? "" : "where exists (select 1 from orders scoped_order where scoped_order.customer_id=c.id and scoped_order.merchant_id=:merchantId)");
        return jdbc.sql(sql).params(scopeParams(merchantId)).query(this::customer).list();
    }

    @Override
    public List<OperationsSnapshot.MerchantSummary> findActiveMerchants() {
        return jdbc.sql("select id,store_name,legal_name,status from merchants where status='ACTIVE' order by created_at")
                .query((rs, row) -> new OperationsSnapshot.MerchantSummary(
                        rs.getObject("id", UUID.class), rs.getString("store_name"), rs.getString("legal_name"),
                        rs.getString("status")))
                .list();
    }

    @Override
    public List<OperationsSnapshot.SupportConversationSummary> findSupportConversations(UUID merchantId) {
        return jdbc.sql("""
                select c.id,c.merchant_id,c.customer_id,c.status,c.started_at,c.handed_off_at,c.resolved_at,
                       c.satisfaction_score,count(m.id) message_count,max(m.created_at) last_message_at,
                       (select latest.intent from ai_messages latest
                        where latest.conversation_id=c.id and latest.role='assistant' and latest.intent is not null
                        order by latest.created_at desc limit 1) last_intent
                from ai_conversations c
                left join ai_messages m on m.conversation_id=c.id
                where c.merchant_id=:merchantId
                group by c.id
                order by c.started_at desc
                limit 100
                """).param("merchantId", merchantId).query((rs, row) -> new OperationsSnapshot.SupportConversationSummary(
                        rs.getObject("id", UUID.class), rs.getObject("merchant_id", UUID.class),
                        rs.getObject("customer_id", UUID.class), rs.getString("status"),
                        instant(rs, "started_at"), nullableInstant(rs, "handed_off_at"),
                        nullableInstant(rs, "resolved_at"), rs.getBigDecimal("satisfaction_score"),
                        rs.getLong("message_count"), nullableInstant(rs, "last_message_at"),
                        rs.getString("last_intent"))).list();
    }

    private OperationsSnapshot.SupportSnapshot support(UUID merchantId, Instant start, Instant end) {
        Boolean exists = jdbc.sql("select to_regclass('public.ai_conversations') is not null").query(Boolean.class).single();
        if (!Boolean.TRUE.equals(exists)) return new OperationsSnapshot.SupportSnapshot(0, 0, 0, 0, 0);
        return jdbc.sql("""
                select count(*) conversations,
                       count(*) filter (where status='RESOLVED') resolved,
                       count(*) filter (where handed_off_at is not null) handed_off,
                       coalesce(avg(satisfaction_score) filter (where satisfaction_score is not null),0) satisfaction
                from ai_conversations where started_at>=:start and started_at<:end %s
                """.formatted(scope(merchantId, "merchant_id"))).param("start", dbTime(start)).param("end", dbTime(end)).params(scopeParams(merchantId)).query((rs, row) -> {
                    long conversations = rs.getLong("conversations");
                    long resolved = rs.getLong("resolved");
                    double rate = conversations == 0 ? 0 : resolved * 100.0 / conversations;
                    return new OperationsSnapshot.SupportSnapshot(conversations, resolved, rs.getLong("handed_off"), rate, rs.getDouble("satisfaction"));
                }).single();
    }

    private BigDecimal money(String sql, UUID merchantId, Instant start, Instant end) {
        return jdbc.sql(sql).param("start", dbTime(start)).param("end", dbTime(end)).params(scopeParams(merchantId)).query(BigDecimal.class).single();
    }

    private long count(String sql, UUID merchantId) { return jdbc.sql(sql).params(scopeParams(merchantId)).query(Long.class).single(); }

    private long countBetween(String sql, UUID merchantId, Instant start, Instant end) {
        return jdbc.sql(sql).param("start", dbTime(start)).param("end", dbTime(end)).params(scopeParams(merchantId)).query(Long.class).single();
    }

    private static String scope(UUID merchantId, String column) {
        return merchantId == null ? "" : " and " + column + "=:merchantId";
    }

    private static String whereScope(UUID merchantId, String column) {
        return merchantId == null ? "" : " where " + column + "=:merchantId";
    }

    private static Map<String, ?> scopeParams(UUID merchantId) {
        return merchantId == null ? Map.of() : Map.of("merchantId", merchantId);
    }

    private OperationsSnapshot.OrderSummary order(ResultSet rs, int row) throws SQLException {
        String name = rs.getString("display_name");
        String email = rs.getString("email");
        return new OperationsSnapshot.OrderSummary(rs.getObject("id", UUID.class), rs.getString("order_no"), rs.getObject("customer_id", UUID.class), name == null ? "未命名客户" : name, email, rs.getBigDecimal("total_amount"), rs.getString("status"), instant(rs, "created_at"));
    }

    private OperationsSnapshot.ProductSummary product(ResultSet rs, int row) throws SQLException {
        return new OperationsSnapshot.ProductSummary(rs.getObject("id", UUID.class), rs.getString("name"), rs.getString("subtitle"), rs.getString("brand"), rs.getString("description"), rs.getBigDecimal("weight_kg"), rs.getString("status"), rs.getString("store_name"), rs.getString("category_name"), rs.getObject("category_id", UUID.class), rs.getString("sku_code"), rs.getString("sku_title"), rs.getBigDecimal("sale_price"), rs.getBigDecimal("market_price"), rs.getInt("available_stock"), rs.getLong("version"), instant(rs, "updated_at"), rs.getString("cover_image_url"), rs.getString("currency"));
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
