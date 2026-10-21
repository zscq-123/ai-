package com.zscq.mall.commerce.media.api;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

import com.zscq.mall.commerce.config.MarketplaceAuthorization;
import com.zscq.mall.commerce.media.MediaAssets;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.server.ResponseStatusException;

class ProductMediaControllerTest {
    @Test
    void refusesUploadingIntoOtherMerchantBeforeReadingTheFile() {
        UUID merchant = UUID.randomUUID();
        var assets = mock(MediaAssets.class);
        var controller = new ProductMediaController(assets, new MarketplaceAuthorization(false));
        var jwt = Jwt.withTokenValue("test").header("alg", "none").claim("merchant_id", merchant.toString()).build();
        var authentication = new JwtAuthenticationToken(jwt, List.of(new SimpleGrantedAuthority("ROLE_SELLER")));
        var file = new MockMultipartFile("file", "picture.png", "image/png", new byte[]{1});

        assertThatThrownBy(() -> controller.upload(UUID.randomUUID(), file, authentication))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        org.assertj.core.api.Assertions.assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
        verifyNoInteractions(assets);
    }
}
