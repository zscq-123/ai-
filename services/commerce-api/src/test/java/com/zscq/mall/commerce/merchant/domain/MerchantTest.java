package com.zscq.mall.commerce.merchant.domain;

import static org.assertj.core.api.Assertions.*;
import org.junit.jupiter.api.Test;

class MerchantTest {
    @Test void applicationStartsPendingAndCanBeApproved() {
        Merchant merchant = Merchant.apply("Legal", "Store", "Owner", "13800000000", "L-1");
        assertThat(merchant.status()).isEqualTo(MerchantStatus.PENDING_REVIEW);
        assertThat(merchant.approve().status()).isEqualTo(MerchantStatus.ACTIVE);
    }
    @Test void activeMerchantCannotBeReviewedTwice() {
        Merchant merchant = Merchant.apply("Legal", "Store", "Owner", "13800000000", "L-1").approve();
        assertThatThrownBy(merchant::approve).isInstanceOf(IllegalStateException.class);
    }
}
