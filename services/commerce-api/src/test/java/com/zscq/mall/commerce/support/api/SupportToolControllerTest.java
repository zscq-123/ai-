package com.zscq.mall.commerce.support.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.support.application.SupportToolService;
import com.zscq.mall.commerce.support.domain.SupportEvidence;
import com.zscq.mall.commerce.support.domain.SupportToolQuery;
import com.zscq.mall.commerce.support.domain.SupportToolRepository;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.Optional;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class SupportToolControllerTest {
    @Test
    void acceptsMatchingHmacAndRejectsInvalidSignature() throws Exception {
        SupportToolRepository repository = new InventoryRepository();
        SupportToolController controller = new SupportToolController(
                new SupportToolService(repository), "test-secret");
        var request = new SupportToolController.SupportToolRequest(
                "这款有库存吗", null, UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID());
        String signature = sign("test-secret", SupportToolController.canonical(request));

        assertThat(controller.evidence(request, signature))
                .extracting(SupportEvidence::reference)
                .containsExactly("inventory://sku");
        assertThatThrownBy(() -> controller.evidence(request, "00"))
                .isInstanceOfSatisfying(ResponseStatusException.class,
                        exception -> assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED));
    }

    private static String sign(String secret, String value) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return HexFormat.of().formatHex(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
    }

    private static final class InventoryRepository implements SupportToolRepository {
        @Override
        public Optional<SupportEvidence> inventory(SupportToolQuery query) {
            return Optional.of(new SupportEvidence("库存3件", "库存", "inventory://sku"));
        }

        @Override public Optional<SupportEvidence> order(SupportToolQuery query) { return Optional.empty(); }
        @Override public Optional<SupportEvidence> logistics(SupportToolQuery query) { return Optional.empty(); }
        @Override public Optional<SupportEvidence> payment(SupportToolQuery query) { return Optional.empty(); }
    }
}
