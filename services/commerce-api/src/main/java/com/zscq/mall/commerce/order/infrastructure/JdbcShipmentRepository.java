package com.zscq.mall.commerce.order.infrastructure;

import com.zscq.mall.commerce.order.domain.Shipment;
import com.zscq.mall.commerce.order.domain.ShipmentRepository;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.sql.Types;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcShipmentRepository implements ShipmentRepository {
    private final JdbcClient jdbc;

    JdbcShipmentRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Shipment save(Shipment shipment) {
        jdbc.sql("""
                insert into order_shipments(
                    order_id,carrier_code,carrier_name,tracking_no,status,latest_event,shipped_at,updated_at
                ) values(
                    :orderId,:carrierCode,:carrierName,:trackingNo,:status,:latestEvent,:shippedAt,:updatedAt
                ) on conflict(order_id) do update set
                    carrier_code=excluded.carrier_code,
                    carrier_name=excluded.carrier_name,
                    tracking_no=excluded.tracking_no,
                    status=excluded.status,
                    latest_event=excluded.latest_event,
                    updated_at=excluded.updated_at
                """)
                .param("orderId", shipment.orderId())
                .param("carrierCode", shipment.carrierCode())
                .param("carrierName", shipment.carrierName())
                .param("trackingNo", shipment.trackingNo())
                .param("status", shipment.status())
                .param("latestEvent", shipment.latestEvent(), Types.VARCHAR)
                .param("shippedAt", Timestamp.from(shipment.shippedAt()), Types.TIMESTAMP)
                .param("updatedAt", Timestamp.from(shipment.updatedAt()), Types.TIMESTAMP)
                .update();
        return shipment;
    }

    @Override
    public Optional<Shipment> findByOrderId(UUID orderId) {
        return jdbc.sql("""
                select s.*,o.order_no from order_shipments s
                join orders o on o.id=s.order_id where s.order_id=:orderId
                """)
                .param("orderId", orderId)
                .query(this::map)
                .optional();
    }

    private Shipment map(ResultSet row, int number) throws SQLException {
        return new Shipment(
                row.getObject("order_id", UUID.class),
                row.getString("order_no"),
                row.getString("carrier_code"),
                row.getString("carrier_name"),
                row.getString("tracking_no"),
                row.getString("status"),
                row.getString("latest_event"),
                row.getTimestamp("shipped_at").toInstant(),
                row.getTimestamp("updated_at").toInstant());
    }
}
