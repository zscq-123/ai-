package com.zscq.mall.commerce.media.application;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Iterator;
import java.util.Locale;
import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.MemoryCacheImageInputStream;
import org.springframework.stereotype.Component;

@Component
public class ImageSanitizer {
    public static final int MAX_BYTES = 5 * 1024 * 1024;
    private static final long MAX_PIXELS = 16_000_000L;

    public SanitizedImage sanitize(byte[] input) {
        if (input.length == 0) throw new IllegalArgumentException("请选择图片文件");
        if (input.length > MAX_BYTES) throw new IllegalArgumentException("每张商品图片不能超过 5 MB");
        try (var stream = new MemoryCacheImageInputStream(new ByteArrayInputStream(input))) {
            Iterator<ImageReader> readers = ImageIO.getImageReaders(stream);
            if (!readers.hasNext()) throw new IllegalArgumentException("文件不是有效的 PNG、JPEG 或 WebP 图片");
            ImageReader reader = readers.next();
            try {
                String format = reader.getFormatName().toLowerCase(Locale.ROOT);
                if (!java.util.Set.of("png", "jpeg", "jpg", "webp").contains(format)) {
                    throw new IllegalArgumentException("仅支持 PNG、JPEG 或 WebP 图片");
                }
                reader.setInput(stream, true, true);
                int width = reader.getWidth(0);
                int height = reader.getHeight(0);
                if (width < 1 || height < 1 || width > 6000 || height > 6000 || (long) width * height > MAX_PIXELS) {
                    throw new IllegalArgumentException("图片尺寸不能超过 6000 × 6000，且总像素不能超过 1600 万");
                }
                BufferedImage image = reader.read(0);
                if (image == null) throw new IllegalArgumentException("图片无法解码");
                // Encode only decoded pixels: discard EXIF, injected trailing bytes and original filenames.
                String outputFormat = format.equals("jpeg") || format.equals("jpg") ? "jpeg" : "png";
                var output = new ByteArrayOutputStream();
                if (!ImageIO.write(image, outputFormat, output)) throw new IOException("Image encoder unavailable");
                if (output.size() > 20 * 1024 * 1024) throw new IllegalArgumentException("处理后的图片过大，请缩小尺寸后重试");
                return new SanitizedImage(output.toByteArray(), "image/" + outputFormat,
                        outputFormat.equals("jpeg") ? "jpg" : "png", width, height);
            } finally {
                reader.dispose();
            }
        } catch (IOException exception) {
            throw new IllegalArgumentException("图片已损坏或格式不受支持", exception);
        }
    }

    public record SanitizedImage(byte[] bytes, String contentType, String extension, int width, int height) {}
}
