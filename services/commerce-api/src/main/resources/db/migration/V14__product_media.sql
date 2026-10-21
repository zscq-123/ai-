CREATE TABLE product_media (
    id UUID PRIMARY KEY,
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    storage_key VARCHAR(80) NOT NULL UNIQUE,
    content_type VARCHAR(40) NOT NULL,
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_product_media_merchant ON product_media(merchant_id, created_at DESC);
ALTER TABLE products ADD COLUMN image_urls JSONB;
