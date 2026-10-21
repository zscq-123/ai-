package com.zscq.mall.commerce.media;

import static org.assertj.core.api.Assertions.*;

import com.zscq.mall.commerce.media.application.ImageSanitizer;
import com.zscq.mall.commerce.media.domain.ProductImage;
import com.zscq.mall.commerce.media.domain.ProductImageRepository;
import com.zscq.mall.commerce.media.infrastructure.LocalImageStorage;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;

class MediaAssetsTest {
    @TempDir Path directory;

    @Test
    void storesImageAndKeepsSelectedOrdering() throws Exception {
        UUID merchant = UUID.randomUUID();
        var repository = new MemoryImages(merchant);
        var assets = assets(repository);
        var first = assets.upload(merchant, image());
        var second = assets.upload(merchant, image());
        var order = List.of(second.url(), first.url());

        assertThat(assets.validateProductImages(merchant, order, List.of())).containsExactly(second.url(), first.url());
        assertThat(Files.readAllBytes(assets.read(first.id()).path())).isNotEmpty();
        assertThat(repository.images).hasSize(2);
    }

    @Test
    void preventsOtherMerchantsMediaAndUnknownMediaFromBeingAttached() throws Exception {
        UUID owner = UUID.randomUUID();
        var assets = assets(new MemoryImages(owner));
        var image = assets.upload(owner, image());
        assertThatThrownBy(() -> assets.validateProductImages(UUID.randomUUID(), List.of(image.url()), List.of()))
                .isInstanceOf(ResponseStatusException.class).hasMessageContaining("403");
        assertThatIllegalArgumentException().isThrownBy(() -> assets.validateProductImages(owner,
                List.of("/api/public/media/product-images/" + UUID.randomUUID()), List.of()));
        assertThatThrownBy(() -> assets.upload(UUID.randomUUID(), image())).isInstanceOf(NoSuchElementException.class);
    }

    @Test
    void rejectsDuplicatesMoreThanNineAndNewRemoteUrlsButRetainsExistingImportedImages() {
        UUID merchant = UUID.randomUUID();
        var assets = assets(new MemoryImages(merchant));
        String imported = "https://images.example.com/existing.jpg";
        assertThat(assets.validateProductImages(merchant, List.of(imported), List.of(imported))).containsExactly(imported);
        assertThat(assets.validateProductImages(merchant, null, List.of(imported))).containsExactly(imported);
        assertThat(assets.validateProductImages(merchant, List.of(), List.of(imported))).isEmpty();
        assertThatIllegalArgumentException().isThrownBy(() -> assets.validateProductImages(merchant, List.of(imported), List.of()));
        assertThatIllegalArgumentException().isThrownBy(() -> assets.validateProductImages(merchant, List.of(imported, imported), List.of(imported)));
        assertThatIllegalArgumentException().isThrownBy(() -> assets.validateProductImages(merchant, Collections.nCopies(10, imported), List.of(imported)));
    }

    @Test
    void rejectsStorageTraversalAndDoesNotKeepFilesWhenMetadataSaveFails() throws Exception {
        var storage = new LocalImageStorage(directory.toString());
        assertThatIllegalArgumentException().isThrownBy(() -> storage.path("../../test.png"));
        UUID merchant = UUID.randomUUID();
        var repository = new MemoryImages(merchant) {
            @Override public void save(ProductImage image) { throw new IllegalStateException("Database unavailable"); }
        };
        assertThatThrownBy(() -> assets(repository).upload(merchant, image())).isInstanceOf(IllegalStateException.class);
        try (var files = Files.list(directory)) { assertThat(files.count()).isZero(); }
    }

    private MediaAssets assets(ProductImageRepository repository) {
        return new MediaAssets(repository, new ImageSanitizer(), new LocalImageStorage(directory.toString()));
    }

    private static byte[] image() throws Exception {
        var output = new ByteArrayOutputStream();
        ImageIO.write(new BufferedImage(10, 10, BufferedImage.TYPE_INT_RGB), "png", output);
        return output.toByteArray();
    }

    private static class MemoryImages implements ProductImageRepository {
        private final UUID merchant;
        private final Map<UUID, ProductImage> images = new HashMap<>();
        MemoryImages(UUID merchant) { this.merchant = merchant; }
        public boolean activeMerchantExists(UUID merchantId) { return merchant.equals(merchantId); }
        public void save(ProductImage image) { images.put(image.id(), image); }
        public Optional<ProductImage> find(UUID id) { return Optional.ofNullable(images.get(id)); }
    }
}
