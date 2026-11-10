package com.zscq.mall.commerce.support.domain;

import java.util.Optional;

public interface SupportToolRepository {
    Optional<SupportEvidence> inventory(SupportToolQuery query);
    Optional<SupportEvidence> order(SupportToolQuery query);
    Optional<SupportEvidence> logistics(SupportToolQuery query);
    Optional<SupportEvidence> payment(SupportToolQuery query);
}
