package com.zscq.mall.commerce.support.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.zscq.mall.commerce.support.domain.SupportEvidence;
import com.zscq.mall.commerce.support.domain.SupportToolQuery;
import com.zscq.mall.commerce.support.domain.SupportToolRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class SupportToolServiceTest {
    @Test
    void anonymousProductQuestionOnlyReadsPublicInventory() {
        RecordingRepository repository = new RecordingRepository();
        SupportToolService service = new SupportToolService(repository);

        List<SupportEvidence> evidence = service.lookup(new SupportToolQuery(
                "这款有现货吗", null, UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID()));

        assertThat(repository.calls).containsExactly("inventory");
        assertThat(evidence).extracting(SupportEvidence::reference).containsExactly("inventory://sku");
    }

    @Test
    void authenticatedOrderQuestionReadsOrderLogisticsAndPaymentEvidence() {
        RecordingRepository repository = new RecordingRepository();
        SupportToolService service = new SupportToolService(repository);

        List<SupportEvidence> evidence = service.lookup(new SupportToolQuery(
                "我的订单物流到哪了，退款到账没有", UUID.randomUUID(), UUID.randomUUID(), null, null));

        assertThat(repository.calls).containsExactly("payment", "logistics", "order");
        assertThat(evidence).extracting(SupportEvidence::reference)
                .containsExactly("payment-status://NO1", "logistics://NO1", "order://NO1");
        assertThat(evidence).hasSize(3);
    }

    private static final class RecordingRepository implements SupportToolRepository {
        private final List<String> calls = new ArrayList<>();

        @Override
        public Optional<SupportEvidence> inventory(SupportToolQuery query) {
            calls.add("inventory");
            return Optional.of(new SupportEvidence("库存3件", "库存", "inventory://sku"));
        }

        @Override
        public Optional<SupportEvidence> order(SupportToolQuery query) {
            calls.add("order");
            return Optional.of(new SupportEvidence("订单已付款", "订单", "order://NO1"));
        }

        @Override
        public Optional<SupportEvidence> logistics(SupportToolQuery query) {
            calls.add("logistics");
            return Optional.of(new SupportEvidence("正在运输", "物流", "logistics://NO1"));
        }

        @Override
        public Optional<SupportEvidence> payment(SupportToolQuery query) {
            calls.add("payment");
            return Optional.of(new SupportEvidence("已支付", "支付", "payment-status://NO1"));
        }
    }
}
