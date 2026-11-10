package com.zscq.mall.commerce.support.api;

import com.zscq.mall.commerce.support.application.SupportToolService;
import com.zscq.mall.commerce.support.domain.SupportEvidence;
import com.zscq.mall.commerce.support.domain.SupportToolQuery;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/internal/support")
public class SupportToolController {
    private final SupportToolService service;
    private final byte[] secret;

    public SupportToolController(
            SupportToolService service,
            @Value("${commerce.support.tool-secret:local-support-tool-secret}") String secret) {
        this.service = service;
        this.secret = secret.getBytes(StandardCharsets.UTF_8);
    }

    @PostMapping("/evidence")
    List<SupportEvidence> evidence(
            @Valid @RequestBody SupportToolRequest request,
            @RequestHeader("X-Nova-Tool-Signature") String signature) {
        if (!validSignature(request, signature)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid support tool signature");
        }
        return service.lookup(new SupportToolQuery(
                request.message(), request.customerId(), request.merchantId(), request.productId(), request.skuId()));
    }

    boolean validSignature(SupportToolRequest request, String suppliedSignature) {
        byte[] supplied;
        try {
            supplied = HexFormat.of().parseHex(suppliedSignature);
        } catch (IllegalArgumentException exception) {
            return false;
        }
        return MessageDigest.isEqual(hmac(canonical(request)), supplied);
    }

    static String canonical(SupportToolRequest request) {
        return value(request.customerId()) + "\n"
                + value(request.merchantId()) + "\n"
                + value(request.productId()) + "\n"
                + value(request.skuId()) + "\n"
                + request.message();
    }

    private byte[] hmac(String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret, "HmacSHA256"));
            return mac.doFinal(value.getBytes(StandardCharsets.UTF_8));
        } catch (Exception exception) {
            throw new IllegalStateException("HMAC unavailable", exception);
        }
    }

    private static String value(UUID value) {
        return value == null ? "" : value.toString();
    }

    record SupportToolRequest(
            @NotBlank @Size(max = 2000) String message,
            UUID customerId,
            UUID merchantId,
            UUID productId,
            UUID skuId) {}
}
