CREATE TABLE merchants (
    id UUID PRIMARY KEY,
    legal_name VARCHAR(160) NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(80) NOT NULL,
    contact_phone VARCHAR(40) NOT NULL,
    business_license_no VARCHAR(80) NOT NULL UNIQUE,
    status VARCHAR(24) NOT NULL,
    rejection_reason VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL,
    reviewed_at TIMESTAMPTZ
);

CREATE TABLE categories (
    id UUID PRIMARY KEY,
    parent_id UUID REFERENCES categories(id),
    name VARCHAR(80) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE products (
    id UUID PRIMARY KEY,
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    category_id UUID REFERENCES categories(id),
    name VARCHAR(180) NOT NULL,
    subtitle VARCHAR(300),
    status VARCHAR(24) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE product_skus (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_code VARCHAR(80) NOT NULL UNIQUE,
    title VARCHAR(160) NOT NULL,
    sale_price NUMERIC(14, 2) NOT NULL CHECK (sale_price >= 0),
    market_price NUMERIC(14, 2) CHECK (market_price IS NULL OR market_price >= sale_price),
    available_stock INTEGER NOT NULL DEFAULT 0 CHECK (available_stock >= 0),
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_products_merchant ON products(merchant_id);
CREATE INDEX idx_products_category_status ON products(category_id, status);
CREATE INDEX idx_products_name_search ON products USING gin(to_tsvector('simple', name || ' ' || COALESCE(subtitle, '')));

INSERT INTO categories (id, name, slug, sort_order) VALUES
    ('10000000-0000-0000-0000-000000000001', '办公设备', 'office-equipment', 10),
    ('10000000-0000-0000-0000-000000000002', '工业耗材', 'industrial-supplies', 20),
    ('10000000-0000-0000-0000-000000000003', '员工福利', 'employee-benefits', 30);

INSERT INTO merchants (id, legal_name, store_name, contact_name, contact_phone, business_license_no, status, created_at, reviewed_at)
VALUES ('20000000-0000-0000-0000-000000000001', '诺瓦数字科技有限公司', 'NOVA 数字办公旗舰店', '示例商家', '13800000000', 'DEMO-LICENSE-001', 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO products (id, merchant_id, category_id, name, subtitle, status, created_at, updated_at)
VALUES ('30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '智能协作终端 Pro', '4K 会议、多屏协同、三年企业质保', 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO product_skus (id, product_id, sku_code, title, sale_price, market_price, available_stock)
VALUES ('40000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'NOVA-COLLAB-PRO', '专业版', 6299.00, 6999.00, 120);
