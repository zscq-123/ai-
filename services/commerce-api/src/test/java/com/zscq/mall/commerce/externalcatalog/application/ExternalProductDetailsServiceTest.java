package com.zscq.mall.commerce.externalcatalog.application;

import static org.assertj.core.api.Assertions.*;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetails;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalProductDetailsRepository;
import java.time.Instant;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.web.server.ResponseStatusException;

class ExternalProductDetailsServiceTest {
    private static final UUID ID = UUID.randomUUID();
    private static final UUID MERCHANT = UUID.randomUUID();
    private static final String URL = "https://www.lazada.sg/products/visible-product-i123-s456.html";
    private static final String COVER = "https://img.lazcdn.com/g/p/cover.jpg";
    private static final String SECOND = "https://sg-live-01.slatic.net/p/detail.jpg";

    @Test
    void supplementsOnlyNullFieldsFromDirectSourceAndCreatesPlainTextDescription() {
        var repository = new Repository(snapshot("DRAFT", null, null, List.of(COVER), "LAZADA_DIRECT"));
        var result = new ExternalProductDetailsService(repository).supplement(ID, 7, details(URL, List.of()));

        assertThat(result.version()).isEqualTo(8);
        assertThat(result.updatedFields()).containsExactly("brand", "description");
        assertThat(repository.savedBrand).isEqualTo("Observed brand");
        assertThat(repository.savedDescription).isEqualTo("Visible selling point\nMaterial：Cotton");
        assertThat(repository.savedImages).isNull();
        assertThat(repository.savedDetails.provider()).isEqualTo("BROWSER_VISIBLE_DETAIL");
        assertThat(repository.savedDetails.attributes()).containsEntry("Material", "Cotton");
        assertThat(repository.savedDetails.options()).containsEntry("Color", List.of("Black", "White"));
        assertThat(repository.snapshot.merchantId()).isEqualTo(MERCHANT);
    }

    @Test
    void preservesMerchantEmptyStringsAndExplicitlyClearedImages() {
        var repository = new Repository(snapshot("DRAFT", "", "", List.of(), "LAZADA_DIRECT"));
        var result = new ExternalProductDetailsService(repository).supplement(ID, 7, details(URL, List.of(SECOND)));

        assertThat(result.updatedFields()).isEmpty();
        assertThat(repository.savedBrand).isNull();
        assertThat(repository.savedDescription).isNull();
        assertThat(repository.savedImages).isNull();
        assertThat(repository.savedDetails.imageUrls()).containsExactly(SECOND);
    }

    @Test
    void preservesExistingMerchantContentAndImageOrdering() {
        var gallery = List.of("/api/public/media/product-images/" + UUID.randomUUID(), COVER);
        var repository = new Repository(snapshot("DRAFT", "Merchant brand", "Merchant description", gallery, "LAZADA_DIRECT"));
        new ExternalProductDetailsService(repository).supplement(ID, 7, details(URL, List.of(SECOND)));

        assertThat(repository.savedBrand).isNull();
        assertThat(repository.savedDescription).isNull();
        assertThat(repository.savedImages).isNull();
    }

    @Test
    void populatesOnlyASqlNullGalleryAndKeepsItsImportedCoverFirst() {
        var repository = new Repository(snapshot("DRAFT", null, null, null, "LAZADA_DIRECT"));
        new ExternalProductDetailsService(repository).supplement(ID, 7, details(URL, List.of(SECOND, COVER)));
        assertThat(repository.savedImages).containsExactly(COVER, SECOND);
    }

    @Test
    void preservesASingleCoverBecauseTheMerchantMayHaveRemovedOtherDetailImages() {
        var repository = new Repository(snapshot("DRAFT", null, null, List.of(COVER), "LAZADA_DIRECT"));
        var result = new ExternalProductDetailsService(repository).supplement(ID, 7, details(URL, List.of(SECOND, COVER)));

        assertThat(repository.savedImages).isNull();
        assertThat(result.updatedFields()).doesNotContain("imageUrls");
        assertThat(repository.savedDetails.imageUrls()).containsExactly(SECOND, COVER);
    }

    @Test
    void retainsFieldsForNonDirectSourcesWhileStoringTheVisibleEvidence() {
        var repository = new Repository(snapshot("DRAFT", null, null, List.of(COVER), "BRIGHT_DATA"));
        var result = new ExternalProductDetailsService(repository).supplement(ID, 7, details(URL, List.of()));
        assertThat(result.updatedFields()).isEmpty();
        assertThat(repository.savedDetails).isNotNull();
    }

    @Test
    void rejectsPublishedProductsAndStaleEditorVersionsWithoutWriting() {
        var published = new Repository(snapshot("ACTIVE", null, null, List.of(COVER), "LAZADA_DIRECT"));
        assertThatThrownBy(() -> new ExternalProductDetailsService(published).supplement(ID, 7, details(URL, List.of())))
                .isInstanceOf(ResponseStatusException.class).hasMessageContaining("409");
        assertThat(published.savedDetails).isNull();
        var draft = new Repository(snapshot("DRAFT", null, null, List.of(COVER), "LAZADA_DIRECT"));
        assertThatThrownBy(() -> new ExternalProductDetailsService(draft).supplement(ID, 6, details(URL, List.of())))
                .isInstanceOf(OptimisticLockingFailureException.class);
        assertThat(draft.savedDetails).isNull();
    }

    @Test
    void rejectsDifferentItemsMarketsAndUntrustedImageOrSellerDomains() {
        var repository = new Repository(snapshot("DRAFT", null, null, List.of(COVER), "LAZADA_DIRECT"));
        var service = new ExternalProductDetailsService(repository);
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7,
                details("https://www.lazada.sg/products/wrong-i999.html", List.of())));
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7,
                details("https://www.lazada.com.my/products/wrong-i123.html", List.of())));
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7,
                details(URL, List.of("https://lazcdn.com.attacker.example/product.png"))));
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7,
                details(URL, List.of("https://user@img.lazcdn.com/product.png"))));
        var badSeller = new ExternalProductDetails(ExternalProductDetailsService.PROVIDER, URL, Instant.now(), null, null,
                List.of(), Map.of(), Map.of(), "Seller", "https://attacker.example/shop", Map.of(), List.of());
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7, badSeller));
        assertThat(repository.savedDetails).isNull();
    }

    @Test
    void enforcesEvidenceLimitsAndDoesNotPretendBrowserDataIsAnAutomaticCrawler() {
        var service = new ExternalProductDetailsService(new Repository(snapshot("DRAFT", null, null, List.of(COVER), "LAZADA_DIRECT")));
        var oversized = new ExternalProductDetails(ExternalProductDetailsService.PROVIDER, URL, Instant.now(), null, null,
                Collections.nCopies(21, "Highlight"), Map.of(), Map.of(), null, null, Map.of(), List.of());
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7, oversized));
        var wrongProvider = new ExternalProductDetails("LAZADA_DIRECT", URL, Instant.now(), null, null,
                List.of(), Map.of(), Map.of(), null, null, Map.of(), List.of());
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7, wrongProvider));
        var future = new ExternalProductDetails(ExternalProductDetailsService.PROVIDER, URL, Instant.now().plusSeconds(3600), null, null,
                List.of(), Map.of(), Map.of(), null, null, Map.of(), List.of());
        assertThatIllegalArgumentException().isThrownBy(() -> service.supplement(ID, 7, future));
    }

    private static ExternalProductDetails details(String url, List<String> images) {
        return new ExternalProductDetails(ExternalProductDetailsService.PROVIDER, url, Instant.now(), "Observed brand", null,
                List.of("Visible selling point"), Map.of("Material", "Cotton"), Map.of("Color", List.of("Black", "White")),
                "Observed seller", null, Map.of("stock", "Availability shown on the page; quantity unknown"), images);
    }

    private static ExternalProductDetailsRepository.DraftSnapshot snapshot(String status, String brand, String description, List<String> images, String provider) {
        return new ExternalProductDetailsRepository.DraftSnapshot(ID, MERCHANT, 7, status, "LAZADA", "SG:123", URL,
                provider, brand, description, images, COVER);
    }

    private static class Repository implements ExternalProductDetailsRepository {
        private final DraftSnapshot snapshot;
        private ExternalProductDetails savedDetails;
        private String savedBrand;
        private String savedDescription;
        private List<String> savedImages;
        Repository(DraftSnapshot snapshot) { this.snapshot = snapshot; }
        public Optional<DraftSnapshot> findForUpdate(UUID productId) { return Optional.of(snapshot); }
        public long save(UUID productId, long version, ExternalProductDetails details, String brand, String description, List<String> images) {
            savedDetails = details; savedBrand = brand; savedDescription = description; savedImages = images;
            return version + 1;
        }
    }
}
