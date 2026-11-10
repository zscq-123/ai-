package com.zscq.mall.commerce.support.infrastructure;

import com.zscq.mall.commerce.support.domain.SupportEvidence;
import com.zscq.mall.commerce.support.domain.SupportToolQuery;
import com.zscq.mall.commerce.support.domain.SupportToolRepository;
import java.math.BigDecimal;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSupportToolRepository implements SupportToolRepository {
    private static final Pattern ORDER_NUMBER = Pattern.compile("(?i)\\bNO[A-Z0-9]{8,32}\\b");
    private final JdbcClient jdbc;

    JdbcSupportToolRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<SupportEvidence> inventory(SupportToolQuery query) {
        StringBuilder sql = new StringBuilder("""
                select p.id product_id,p.name,s.id sku_id,s.sku_code,s.title sku_title,s.available_stock
                from products p join product_skus s on s.product_id=p.id
                where p.status='ACTIVE' and s.enabled=true
                """);
        List<Object> parameters = new ArrayList<>();
        if (query.merchantId() != null) {
            sql.append(" and p.merchant_id=?");
            parameters.add(query.merchantId());
        }
        if (query.skuId() != null) {
            sql.append(" and s.id=?");
            parameters.add(query.skuId());
        } else if (query.productId() != null) {
            sql.append(" and p.id=?");
            parameters.add(query.productId());
        } else {
            sql.append(" and (position(lower(p.name) in lower(?))>0"
                    + " or position(lower(s.sku_code) in lower(?))>0"
                    + " or position(lower(s.title) in lower(?))>0)");
            parameters.add(query.message());
            parameters.add(query.message());
            parameters.add(query.message());
        }
        sql.append(" order by p.updated_at desc limit 1");
        return jdbc.sql(sql.toString()).params(parameters).query((row, number) -> inventory(row)).optional();
    }

    @Override
    public Optional<SupportEvidence> order(SupportToolQuery query) {
        return orderSnapshot(query).map(order -> new SupportEvidence(
                "订单 " + order.orderNo() + " 当前状态为" + statusLabel(order.status())
                        + "，下单时间 " + order.createdAt() + "，订单金额 " + order.totalAmount() + " 元。",
                "实时订单状态",
                "order://" + order.orderNo()));
    }

    @Override
    public Optional<SupportEvidence> logistics(SupportToolQuery query) {
        Optional<OrderSnapshot> snapshot = orderSnapshot(query);
        if (snapshot.isEmpty()) return Optional.empty();
        OrderSnapshot order = snapshot.get();
        Optional<ShipmentSnapshot> shipment = jdbc.sql("""
                select carrier_code,carrier_name,tracking_no,status,latest_event,updated_at
                from order_shipments where order_id=:orderId
                """).param("orderId", order.id()).query(this::mapShipment).optional();
        if (shipment.isPresent()) {
            ShipmentSnapshot value = shipment.get();
            return Optional.of(new SupportEvidence(
                    "订单 " + order.orderNo() + " 的承运商为" + value.carrierName()
                            + "，物流单号 " + value.trackingNo() + "，当前物流状态为" + shipmentStatusLabel(value.status())
                            + (value.latestEvent() == null ? "。" : "，最新记录：" + value.latestEvent() + "。"),
                    "实时物流状态",
                    "logistics://" + order.orderNo()));
        }
        String content = "SHIPPED".equals(order.status())
                ? "订单 " + order.orderNo() + " 显示已发货，但暂无可核实的承运商或物流单号。"
                : "订单 " + order.orderNo() + " 尚未发货，当前没有物流单号。";
        return Optional.of(new SupportEvidence(content, "实时物流状态", "logistics://" + order.orderNo()));
    }

    @Override
    public Optional<SupportEvidence> payment(SupportToolQuery query) {
        Optional<OrderSnapshot> snapshot = orderSnapshot(query);
        if (snapshot.isEmpty()) return Optional.empty();
        OrderSnapshot order = snapshot.get();
        String content = switch (order.status()) {
            case "PENDING_PAYMENT" -> "订单 " + order.orderNo() + " 的支付状态为待付款。";
            case "REFUND_PENDING" -> "订单 " + order.orderNo() + " 已支付，退款状态为处理中。";
            case "REFUNDED" -> "订单 " + order.orderNo() + " 已退款。";
            case "CANCELLED" -> order.paidAt() == null
                    ? "订单 " + order.orderNo() + " 已取消，未记录成功支付。"
                    : "订单 " + order.orderNo() + " 已取消，曾记录成功支付，退款结果需要继续核对。";
            default -> "订单 " + order.orderNo() + " 的支付状态为已支付"
                    + (order.paidAt() == null ? "。" : "，支付时间 " + order.paidAt() + "。");
        };
        return Optional.of(new SupportEvidence(content, "实时支付状态", "payment-status://" + order.orderNo()));
    }

    private Optional<OrderSnapshot> orderSnapshot(SupportToolQuery query) {
        if (query.customerId() == null) return Optional.empty();
        StringBuilder sql = new StringBuilder("""
                select id,order_no,status,total_amount,created_at,paid_at
                from orders where customer_id=?
                """);
        List<Object> parameters = new ArrayList<>();
        parameters.add(query.customerId());
        if (query.merchantId() != null) {
            sql.append(" and merchant_id=?");
            parameters.add(query.merchantId());
        }
        String requestedOrder = orderNumber(query.message());
        if (requestedOrder != null) {
            sql.append(" and upper(order_no)=?");
            parameters.add(requestedOrder.toUpperCase());
        }
        sql.append(" order by created_at desc limit 1");
        return jdbc.sql(sql.toString()).params(parameters).query(this::mapOrder).optional();
    }

    private static SupportEvidence inventory(ResultSet row) throws SQLException {
        int stock = row.getInt("available_stock");
        String stockText = stock > 0 ? "当前可售库存 " + stock + " 件。" : "当前可售库存 0 件，状态为缺货。";
        return new SupportEvidence(
                "商品「" + row.getString("name") + "」规格「" + row.getString("sku_title") + "」" + stockText,
                "实时库存",
                "inventory://" + row.getObject("sku_id", UUID.class));
    }

    private OrderSnapshot mapOrder(ResultSet row, int number) throws SQLException {
        return new OrderSnapshot(
                row.getObject("id", UUID.class),
                row.getString("order_no"),
                row.getString("status"),
                row.getBigDecimal("total_amount"),
                instant(row.getTimestamp("created_at")),
                instant(row.getTimestamp("paid_at")));
    }

    private ShipmentSnapshot mapShipment(ResultSet row, int number) throws SQLException {
        return new ShipmentSnapshot(
                row.getString("carrier_code"),
                row.getString("carrier_name"),
                row.getString("tracking_no"),
                row.getString("status"),
                row.getString("latest_event"));
    }

    private static String orderNumber(String message) {
        Matcher matcher = ORDER_NUMBER.matcher(message);
        return matcher.find() ? matcher.group() : null;
    }

    private static String statusLabel(String status) {
        return switch (status) {
            case "PENDING_PAYMENT" -> "待付款";
            case "PAID" -> "已付款";
            case "FULFILLING" -> "履约处理中";
            case "SHIPPED" -> "已发货";
            case "COMPLETED" -> "已完成";
            case "CANCELLED" -> "已取消";
            case "REFUND_PENDING" -> "退款处理中";
            case "REFUNDED" -> "已退款";
            default -> status;
        };
    }

    private static String shipmentStatusLabel(String status) {
        return switch (status) {
            case "LABEL_CREATED" -> "已创建运单";
            case "IN_TRANSIT" -> "运输中";
            case "OUT_FOR_DELIVERY" -> "派送中";
            case "DELIVERED" -> "已签收";
            case "EXCEPTION" -> "物流异常";
            default -> status;
        };
    }

    private static Instant instant(Timestamp value) {
        return value == null ? null : value.toInstant();
    }

    private record OrderSnapshot(
            UUID id, String orderNo, String status, BigDecimal totalAmount, Instant createdAt, Instant paidAt) {}
    private record ShipmentSnapshot(
            String carrierCode, String carrierName, String trackingNo, String status, String latestEvent) {}
}
