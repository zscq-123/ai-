package com.zscq.mall.commerce.merchant.infrastructure;
import com.zscq.mall.commerce.merchant.domain.MerchantAuditRepository;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
@Repository
class JdbcMerchantAuditRepository implements MerchantAuditRepository {
    private final JdbcClient jdbc;
    JdbcMerchantAuditRepository(JdbcClient jdbc) { this.jdbc=jdbc; }
    public void record(String action, UUID merchantId, String detail) { jdbc.sql("insert into operation_audit_log(id,actor_id,action,resource_type,resource_id,detail) values(:id,'authenticated-operator',:action,'MERCHANT',:resource,cast(:detail as jsonb))").param("id",UUID.randomUUID()).param("action",action).param("resource",merchantId.toString()).param("detail",detail).update(); }
}
