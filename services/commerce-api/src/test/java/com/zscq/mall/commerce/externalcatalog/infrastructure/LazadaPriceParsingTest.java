package com.zscq.mall.commerce.externalcatalog.infrastructure;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProduct;
import com.zscq.mall.commerce.externalcatalog.domain.ExternalCatalogProviderException;
import java.net.URI;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import tools.jackson.databind.json.JsonMapper;

class LazadaPriceParsingTest {
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Instant FETCHED_AT = Instant.parse("2026-10-21T03:00:00Z");

    @ParameterizedTest
    @CsvSource(value = {
            "lazada.sg|1,234.56|2,000.00|1234.56|2000.00|SGD",
            "lazada.com.my|1,234.50|2,500.00|1234.50|2500.00|MYR",
            "lazada.co.th|1,011.00|2,000.00|1011.00|2000.00|THB",
            "lazada.com.ph|1,234.00|2,000.00|1234.00|2000.00|PHP",
            "lazada.co.id|60.300|75.000|60300.00|75000.00|IDR",
            "lazada.vn|217.728|300.000|217728.00|300000.00|VND",
            "lazada.co.id|60.300,50|75.000,25|60300.50|75000.25|IDR",
            "lazada.vn|217.728,25|300.000,50|217728.25|300000.50|VND",
            "lazada.co.id|1.234.567,89|2.000.000,00|1234567.89|2000000.00|IDR",
            "lazada.sg|1,234,567.89|2,000,000.00|1234567.89|2000000.00|SGD"
    }, delimiter = '|')
    void parsesDisplayPricesWithTheMarketLocale(String host, String sale, String original,
            String expectedSale, String expectedOriginal, String currency) {
        var product = homepageProduct(host, JSON.writeValueAsString(sale), JSON.writeValueAsString(original));
        assertThat(product.salePrice()).isEqualByComparingTo(expectedSale);
        assertThat(product.marketPrice()).isEqualByComparingTo(expectedOriginal);
        assertThat(product.currency()).isEqualTo(currency);
    }

    @ParameterizedTest
    @ValueSource(strings = {"lazada.sg", "lazada.com.my", "lazada.co.th", "lazada.com.ph", "lazada.co.id", "lazada.vn"})
    void preservesJsonNumericValuesInsteadOfApplyingDisplayGrouping(String host) {
        var product = homepageProduct(host, "60.300", "217.728");
        assertThat(product.salePrice()).isEqualByComparingTo("60.30");
        assertThat(product.marketPrice()).isEqualByComparingTo("217.73");
        assertThat(homepageProduct(host, "60300", "217728").salePrice()).isEqualByComparingTo("60300.00");
    }

    @ParameterizedTest
    @CsvSource(value = {
            "lazada.co.id|60,300", "lazada.vn|217,728", "lazada.co.id|60.30",
            "lazada.vn|21.77.728", "lazada.co.id|1,234.56", "lazada.vn|1.234.56",
            "lazada.co.id|0.001", "lazada.vn|217.728,123", "lazada.sg|1.234,56",
            "lazada.com.my|1,23.45", "lazada.co.th|10,11.00", "lazada.com.ph|1,000,00",
            "lazada.sg|1.234", "lazada.sg|1,234.567", "lazada.sg|1 234.56",
            "lazada.co.id|Rp60.300", "lazada.sg|$1,000.00", "lazada.vn|NaN",
            "lazada.co.id|6e4", "lazada.sg|-1.00", "lazada.co.th|1,011."
    }, delimiter = '|')
    void rejectsMalformedOrMixedLocaleSalePricesWithoutFallingBackToOriginal(String host, String sale) {
        assertThatThrownBy(() -> homepageProduct(host, JSON.writeValueAsString(sale), "1000000"))
                .isInstanceOf(ExternalCatalogProviderException.class)
                .hasMessageContaining("no supported public product data");
    }

    @ParameterizedTest
    @ValueSource(strings = {"null", "true", "{}", "[]", "\"\"", "-1"})
    void rejectsInvalidOriginalPricesWhenNoDiscountExists(String rawPrice) {
        String html = homepageHtml("lazada.sg", null, rawPrice);
        assertThatThrownBy(() -> LazadaPageParser.parse(URI.create("https://www.lazada.sg/"), html, FETCHED_AT))
                .isInstanceOf(ExternalCatalogProviderException.class);
    }

    @Test
    void fallsBackOnlyWhenDiscountIsMissingOrNullAndOmitsInvalidOriginalComparison() {
        var absentDiscount = LazadaPageParser.parse(URI.create("https://www.lazada.co.id/"),
                homepageHtml("lazada.co.id", null, "\"60.300\""), FETCHED_AT).getFirst();
        assertThat(absentDiscount.salePrice()).isEqualByComparingTo("60300.00");
        assertThat(homepageProduct("lazada.vn", "null", "\"217.728\"").salePrice()).isEqualByComparingTo("217728.00");
        var invalidOriginal = homepageProduct("lazada.co.th", "\"1,011.00\"", "\"2,00.00\"");
        assertThat(invalidOriginal.salePrice()).isEqualByComparingTo("1011.00");
        assertThat(invalidOriginal.marketPrice()).isNull();
    }

    @ParameterizedTest
    @CsvSource(value = {"lazada.co.id|IDR", "lazada.vn|VND"}, delimiter = '|')
    void jsonLdKeepsMachinePriceSemanticsForBothNumericAndStringValues(String host, String currency) {
        for (String price : new String[] {"60.300", "\"60.300\""}) {
            String html = "<script type='application/ld+json'>{\"@type\":\"Product\",\"name\":\"Machine price\","
                    + "\"offers\":{\"price\":" + price + ",\"priceCurrency\":\"" + currency + "\"}}</script>";
            var product = LazadaPageParser.parse(URI.create("https://www." + host + "/products/pdp-i123-s456.html"), html, FETCHED_AT).getFirst();
            assertThat(product.salePrice()).isEqualByComparingTo("60.30");
        }
    }

    private static ExternalCatalogProduct homepageProduct(String host, String saleJson, String originalJson) {
        return LazadaPageParser.parse(URI.create("https://www." + host + "/"),
                homepageHtml(host, saleJson, originalJson), FETCHED_AT).getFirst();
    }

    private static String homepageHtml(String host, String saleJson, String originalJson) {
        return "<script>window.__FIRST_SCREEN_DATA={\"items\":[{\"itemTitle\":\"Locale product\","
                + "\"itemUrl\":\"https://www." + host + "/products/pdp-i123-s456.html\","
                + (saleJson == null ? "" : "\"itemDiscountPrice\":" + saleJson + ",")
                + "\"itemPrice\":" + originalJson + "}]};</script>";
    }
}
