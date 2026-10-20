package com.zscq.mall.commerce.shared.domain;

import java.time.Instant;

/** Marker contract for immutable events exchanged between business modules. */
public interface DomainEvent {

    Instant occurredAt();
}
