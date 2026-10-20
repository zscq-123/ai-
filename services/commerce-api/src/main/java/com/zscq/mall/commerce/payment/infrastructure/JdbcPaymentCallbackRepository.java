package com.zscq.mall.commerce.payment.infrastructure;
import com.zscq.mall.commerce.payment.domain.PaymentCallbackRepository;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcPaymentCallbackRepository implements PaymentCallbackRepository {
    private final JdbcClient jdbc;
    JdbcPaymentCallbackRepository(JdbcClient jdbc) { this.jdbc=jdbc; }
    public boolean register(String id,String orderNo,String provider,String hash) {
        try { jdbc.sql("insert into payment_callbacks(callback_id,order_no,provider,payload_hash) values(:id,:orderNo,:provider,:hash)").param("id",id).param("orderNo",orderNo).param("provider",provider).param("hash",hash).update(); return true; }
        catch (DuplicateKeyException ignored) { return false; }
    }
}
