CREATE TABLE support_faq_entries (
    id UUID PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id),
    question VARCHAR(240) NOT NULL,
    answer TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL CHECK (status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ
);

CREATE INDEX idx_support_faq_published
    ON support_faq_entries(merchant_id, status, display_order, updated_at DESC);

INSERT INTO support_faq_entries(
    id, merchant_id, question, answer, keywords, status, display_order, published_at
) VALUES
    ('81000000-0000-0000-0000-000000000001', NULL, '多久发货？',
     '现货商品通常在付款后 24 小时内出库，实际时效以订单物流节点为准。',
     '发货|出库|多久发货', 'PUBLISHED', 10, CURRENT_TIMESTAMP),
    ('81000000-0000-0000-0000-000000000002', NULL, '能开发票吗？',
     '能否开票及具体票种以商品详情和店铺开票说明为准。',
     '发票|开票|票种', 'PUBLISHED', 20, CURRENT_TIMESTAMP),
    ('81000000-0000-0000-0000-000000000003', NULL, '包邮吗？',
     '运费以商品详情和结算页展示为准，不同店铺及配送地区可能不同。',
     '包邮|运费|邮费', 'PUBLISHED', 30, CURRENT_TIMESTAMP),
    ('81000000-0000-0000-0000-000000000004', NULL, '怎么申请退货？',
     '可以在订单详情中进入售后入口，具体条件以商品和店铺售后规则为准。',
     '退货|售后|申请退货', 'PUBLISHED', 40, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;
