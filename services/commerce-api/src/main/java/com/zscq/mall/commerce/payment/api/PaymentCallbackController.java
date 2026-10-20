package com.zscq.mall.commerce.payment.api;
import com.zscq.mall.commerce.payment.application.PaymentCallbackService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/public/payment-callbacks")
public class PaymentCallbackController {
    private final PaymentCallbackService service;
    public PaymentCallbackController(PaymentCallbackService service) { this.service=service; }
    @PostMapping("/{provider}")
    Result accept(@PathVariable String provider,@RequestHeader("X-Payment-Signature") String signature,@Valid @RequestBody Callback body) {
        return new Result(service.accept(body.callbackId(),body.orderNo(),provider,signature,body.payload()));
    }
    record Callback(@NotBlank String callbackId,@NotBlank String orderNo,@NotBlank String payload) {}
    record Result(boolean processed) {}
}
