CREATE TABLE orders (
    id UUID PRIMARY KEY,
    order_no VARCHAR(40) NOT NULL UNIQUE,
    customer_id UUID NOT NULL,
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    status VARCHAR(24) NOT NULL,
    total_amount NUMERIC(14,2) NOT NULL CHECK (total_amount >= 0),
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    paid_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku_id UUID NOT NULL REFERENCES product_skus(id),
    product_name VARCHAR(180) NOT NULL,
    sku_title VARCHAR(160) NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    line_amount NUMERIC(14,2) NOT NULL
);

CREATE TABLE payment_callbacks (
    callback_id VARCHAR(120) PRIMARY KEY,
    order_no VARCHAR(40) NOT NULL,
    provider VARCHAR(30) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload_hash VARCHAR(128) NOT NULL
);

CREATE INDEX idx_orders_customer_created ON orders(customer_id, created_at DESC);
CREATE INDEX idx_orders_merchant_created ON orders(merchant_id, created_at DESC);
