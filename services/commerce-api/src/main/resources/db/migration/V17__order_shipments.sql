CREATE TABLE order_shipments (
    order_id UUID PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    carrier_code VARCHAR(40) NOT NULL,
    carrier_name VARCHAR(100) NOT NULL,
    tracking_no VARCHAR(100) NOT NULL,
    status VARCHAR(40) NOT NULL,
    latest_event VARCHAR(500),
    shipped_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX idx_order_shipments_tracking
    ON order_shipments(carrier_code, tracking_no);
