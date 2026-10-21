package com.zscq.mall.commerce.catalog.domain;

import java.util.UUID;

public record Category(UUID id, UUID parentId, String name, String slug) {}
