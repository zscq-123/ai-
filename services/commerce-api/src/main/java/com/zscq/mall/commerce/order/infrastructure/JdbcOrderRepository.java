package com.zscq.mall.commerce.order.infrastructure;
import com.zscq.mall.commerce.order.domain.*;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.sql.Types;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcOrderRepository implements OrderRepository {
    private final JdbcClient jdbc;
    JdbcOrderRepository(JdbcClient jdbc) { this.jdbc=jdbc; }
    public PurchaseOrder save(PurchaseOrder o) {
        if (findByOrderNo(o.orderNo()).isPresent()) {
            jdbc.sql("update orders set status=:status, paid_at=:paidAt, completed_at=:completedAt where order_no=:no")
                    .param("status",o.status().name())
                    .param("paidAt",timestamp(o.paidAt()), Types.TIMESTAMP)
                    .param("completedAt",timestamp(o.completedAt()), Types.TIMESTAMP)
                    .param("no",o.orderNo()).update();
            return o;
        }
        jdbc.sql("insert into orders(id,order_no,customer_id,merchant_id,status,total_amount,idempotency_key,created_at) values(:id,:no,:customer,:merchant,:status,:total,:key,:created)")
                .param("id",o.id()).param("no",o.orderNo()).param("customer",o.customerId()).param("merchant",o.merchantId()).param("status",o.status().name()).param("total",o.totalAmount()).param("key",o.idempotencyKey()).param("created",timestamp(o.createdAt()), Types.TIMESTAMP).update();
        o.lines().forEach(line -> jdbc.sql("insert into order_items(id,order_id,sku_id,product_name,sku_title,unit_price,quantity,line_amount) values(:id,:order,:sku,:product,:title,:price,:qty,:amount)")
                .param("id",line.id()).param("order",o.id()).param("sku",line.skuId()).param("product",line.productName()).param("title",line.skuTitle()).param("price",line.unitPrice()).param("qty",line.quantity()).param("amount",line.lineAmount()).update());
        return o;
    }
    public Optional<PurchaseOrder> findByCustomerIdAndIdempotencyKey(UUID customerId, String key) {
        return jdbc.sql("select * from orders where customer_id=:customerId and idempotency_key=:key")
                .param("customerId", customerId)
                .param("key", key)
                .query(this::map)
                .optional();
    }
    public Optional<PurchaseOrder> findByOrderNo(String no) { return find("select * from orders where order_no=:value", no); }
    private Optional<PurchaseOrder> find(String sql, String value) { return jdbc.sql(sql).param("value",value).query(this::map).optional(); }
    private PurchaseOrder map(ResultSet rs, int row) throws SQLException {
        UUID orderId=rs.getObject("id",UUID.class);
        List<OrderLine> lines=jdbc.sql("select * from order_items where order_id=:id").param("id",orderId).query((r,n)->new OrderLine(r.getObject("id",UUID.class),r.getObject("sku_id",UUID.class),r.getString("product_name"),r.getString("sku_title"),r.getBigDecimal("unit_price"),r.getInt("quantity"))).list();
        return new PurchaseOrder(orderId,rs.getString("order_no"),rs.getObject("customer_id",UUID.class),rs.getObject("merchant_id",UUID.class),OrderStatus.valueOf(rs.getString("status")),rs.getBigDecimal("total_amount"),rs.getString("idempotency_key"),lines,rs.getTimestamp("created_at").toInstant(),rs.getTimestamp("paid_at") == null ? null : rs.getTimestamp("paid_at").toInstant(),rs.getTimestamp("completed_at") == null ? null : rs.getTimestamp("completed_at").toInstant());
    }

    private static Timestamp timestamp(Instant value) {
        return value == null ? null : Timestamp.from(value);
    }
}
