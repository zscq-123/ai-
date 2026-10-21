package com.zscq.mall.commerce.customer.application;

import java.time.Duration;

public record AuthSession(AuthenticatedCustomer customer, String token, Duration maxAge) {}
