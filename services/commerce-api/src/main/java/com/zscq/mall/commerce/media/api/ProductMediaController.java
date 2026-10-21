package com.zscq.mall.commerce.media.api;

import com.zscq.mall.commerce.config.MarketplaceAuthorization;
import com.zscq.mall.commerce.media.MediaAssets;
import com.zscq.mall.commerce.media.application.ImageSanitizer;
import java.io.IOException;
import java.time.Duration;
import java.util.UUID;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api")
public class ProductMediaController {
    private final MediaAssets assets;
    private final MarketplaceAuthorization authorization;

    public ProductMediaController(MediaAssets assets, MarketplaceAuthorization authorization) {
        this.assets = assets;
        this.authorization = authorization;
    }

    @PostMapping(value = "/seller/{merchantId}/media/product-images", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    MediaAssets.UploadedImage upload(@PathVariable UUID merchantId, @RequestParam("file") MultipartFile file,
                                     Authentication authentication) throws IOException {
        authorization.requireMerchant(authentication, merchantId);
        if (file.getSize() > ImageSanitizer.MAX_BYTES) throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "每张商品图片不能超过 5 MB");
        try (var input = file.getInputStream()) {
            return assets.upload(merchantId, input.readNBytes(ImageSanitizer.MAX_BYTES + 1));
        }
    }

    @GetMapping("/public/media/product-images/{imageId}")
    ResponseEntity<FileSystemResource> image(@PathVariable UUID imageId) {
        var image = assets.read(imageId);
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(image.contentType()))
                .contentLength(image.sizeBytes()).cacheControl(CacheControl.maxAge(Duration.ofDays(365)).cachePublic().immutable())
                .header("X-Content-Type-Options", "nosniff")
                .body(new FileSystemResource(image.path()));
    }
}
