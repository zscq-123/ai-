package com.zscq.mall.commerce.order;
import com.zscq.mall.commerce.order.application.OrderService;
import org.springframework.stereotype.Component;
@Component
class OrderPaymentAdapter implements OrderPaymentFacade {
    private final OrderService service;
    OrderPaymentAdapter(OrderService service) { this.service=service; }
    public void markPaid(String orderNo) { service.markPaid(orderNo); }
}
