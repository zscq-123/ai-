ALTER TABLE products ADD COLUMN IF NOT EXISTS source_platform VARCHAR(32);
ALTER TABLE products ADD COLUMN IF NOT EXISTS external_product_id VARCHAR(180);
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_image_url TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_currency VARCHAR(12);
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_sold_count BIGINT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_rating NUMERIC(4, 2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_payload JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS source_last_synced_at TIMESTAMPTZ;

ALTER TABLE product_skus ADD COLUMN IF NOT EXISTS external_sku_id VARCHAR(180);

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_source_external_id
    ON products(source_platform, external_product_id)
    WHERE source_platform IS NOT NULL AND external_product_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_source_last_synced
    ON products(source_platform, source_last_synced_at DESC)
    WHERE source_platform IS NOT NULL;
