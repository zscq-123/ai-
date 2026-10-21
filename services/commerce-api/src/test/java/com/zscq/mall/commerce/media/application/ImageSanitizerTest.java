package com.zscq.mall.commerce.media.application;

import static org.assertj.core.api.Assertions.*;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.Test;

class ImageSanitizerTest {
    private final ImageSanitizer sanitizer = new ImageSanitizer();

    @Test
    void decodesRealPixelsAndStripsInjectedPayload() throws Exception {
        byte[] png = imageBytes("png", 20, 10);
        byte[] payload = "<script>alert('unsafe metadata')</script>".getBytes(StandardCharsets.UTF_8);
        byte[] poisoned = Arrays.copyOf(png, png.length + payload.length);
        System.arraycopy(payload, 0, poisoned, png.length, payload.length);

        var result = sanitizer.sanitize(poisoned);
        assertThat(result.width()).isEqualTo(20);
        assertThat(result.height()).isEqualTo(10);
        assertThat(result.contentType()).isEqualTo("image/png");
        assertThat(new String(result.bytes(), StandardCharsets.ISO_8859_1)).doesNotContain("script");
        assertThat(ImageIO.read(new ByteArrayInputStream(result.bytes())).getWidth()).isEqualTo(20);
    }

    @Test
    void acceptsJpegAndWebpButNormalizesWebpToPng() throws Exception {
        assertThat(sanitizer.sanitize(imageBytes("jpeg", 12, 12)).contentType()).isEqualTo("image/jpeg");
        byte[] webp = java.util.Base64.getDecoder().decode("UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA");
        var result = sanitizer.sanitize(webp);
        assertThat(result.contentType()).isEqualTo("image/png");
        assertThat(result.width()).isEqualTo(1);
    }

    @Test
    void rejectsFakeImagesSvgGifEmptyAndOversizePayloads() throws Exception {
        assertThatIllegalArgumentException().isThrownBy(() -> sanitizer.sanitize("<svg></svg>".getBytes()));
        assertThatIllegalArgumentException().isThrownBy(() -> sanitizer.sanitize("not an image".getBytes()));
        assertThatIllegalArgumentException().isThrownBy(() -> sanitizer.sanitize(new byte[0]));
        assertThatIllegalArgumentException().isThrownBy(() -> sanitizer.sanitize(new byte[ImageSanitizer.MAX_BYTES + 1]));
        byte[] gif = imageBytes("gif", 10, 10);
        assertThatIllegalArgumentException().isThrownBy(() -> sanitizer.sanitize(gif));
    }

    @Test
    void rejectsOversizeDimensionsBeforePixelDecode() throws Exception {
        byte[] png = imageBytes("png", 6001, 1);
        assertThatIllegalArgumentException().isThrownBy(() -> sanitizer.sanitize(png)).withMessageContaining("6000");
    }

    private static byte[] imageBytes(String format, int width, int height) throws Exception {
        var output = new ByteArrayOutputStream();
        ImageIO.write(new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB), format, output);
        return output.toByteArray();
    }
}
