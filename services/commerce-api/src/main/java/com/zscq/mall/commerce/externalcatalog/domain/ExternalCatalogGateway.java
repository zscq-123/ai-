package com.zscq.mall.commerce.externalcatalog.domain;

import java.net.URI;
import java.util.List;

public interface ExternalCatalogGateway {
    List<ExternalCatalogProduct> fetchLazadaProducts(List<URI> productUrls);
}
