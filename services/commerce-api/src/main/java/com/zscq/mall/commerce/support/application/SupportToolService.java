package com.zscq.mall.commerce.support.application;

import com.zscq.mall.commerce.support.domain.SupportEvidence;
import com.zscq.mall.commerce.support.domain.SupportToolQuery;
import com.zscq.mall.commerce.support.domain.SupportToolRepository;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SupportToolService {
    private static final List<String> INVENTORY_SIGNALS = List.of("库存", "有货", "现货", "能拍", "能下单");
    private static final List<String> ORDER_SIGNALS = List.of(
            "订单", "买的", "下单", "退款", "退钱", "取消", "改地址", "货呢", "发货", "物流", "快递", "到哪", "签收");
    private static final List<String> LOGISTICS_SIGNALS = List.of(
            "物流", "快递", "发货", "到哪", "派送", "签收", "运单", "单号", "还没到", "什么时候到");
    private static final List<String> PAYMENT_SIGNALS = List.of(
            "支付状态", "付款状态", "支付成功", "付款成功", "扣款", "付过", "待付款", "退款", "退钱", "到账");

    private final SupportToolRepository repository;

    public SupportToolService(SupportToolRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<SupportEvidence> lookup(SupportToolQuery query) {
        String message = query.message().strip().toLowerCase();
        List<SupportEvidence> evidence = new ArrayList<>();
        boolean asksLogistics = containsAny(message, LOGISTICS_SIGNALS);
        boolean asksPayment = containsAny(message, PAYMENT_SIGNALS);
        if (containsAny(message, INVENTORY_SIGNALS)) {
            repository.inventory(query).ifPresent(evidence::add);
        }
        if (query.customerId() != null && asksPayment) {
            repository.payment(query).ifPresent(evidence::add);
        }
        if (query.customerId() != null && asksLogistics) {
            repository.logistics(query).ifPresent(evidence::add);
        }
        if (query.customerId() != null && containsAny(message, ORDER_SIGNALS)) {
            repository.order(query).ifPresent(evidence::add);
        }
        return List.copyOf(evidence);
    }

    private static boolean containsAny(String message, List<String> signals) {
        return signals.stream().anyMatch(message::contains);
    }
}
