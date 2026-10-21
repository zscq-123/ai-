CREATE TABLE store_designs (
    id UUID PRIMARY KEY,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    channel VARCHAR(16) NOT NULL CHECK (channel IN ('WEB', 'MOBILE')),
    draft_version BIGINT NOT NULL DEFAULT 1 CHECK (draft_version > 0),
    published_version BIGINT CHECK (published_version IS NULL OR published_version > 0),
    draft_config JSONB NOT NULL,
    published_config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    CONSTRAINT uq_store_design_merchant_channel UNIQUE (merchant_id, channel)
);

CREATE INDEX idx_store_designs_public
    ON store_designs(merchant_id, channel)
    WHERE published_config IS NOT NULL;

INSERT INTO store_designs (
    id, merchant_id, channel, draft_version, published_version,
    draft_config, published_config, published_at
)
SELECT
    CASE channel
        WHEN 'WEB' THEN '51000000-0000-0000-0000-000000000001'::uuid
        ELSE '51000000-0000-0000-0000-000000000002'::uuid
    END,
    '20000000-0000-0000-0000-000000000001'::uuid,
    channel,
    1,
    1,
    config,
    config,
    CURRENT_TIMESTAMP
FROM (VALUES
    ('WEB', '{"theme":{"primaryColor":"#e1251b","backgroundColor":"#f5f5f7","textColor":"#1d1d1f"},"modules":[{"id":"hero","type":"BANNER","visible":true,"data":{"title":"NOVA 数字办公旗舰店","subtitle":"专注企业协作与数字化办公","imageUrl":""}},{"id":"profile","type":"STORE_INFO","visible":true,"data":{"title":"NOVA 数字办公旗舰店","description":"企业级商品与服务"}},{"id":"notice","type":"ANNOUNCEMENT","visible":true,"data":{"text":"工作日 16:00 前下单当日发货"}},{"id":"products","type":"PRODUCT_GRID","visible":true,"data":{"title":"店铺精选","limit":6}},{"id":"coupon","type":"COUPON","visible":true,"data":{"title":"新客礼遇","description":"首单满 999 减 100"}}]}'::jsonb),
    ('MOBILE', '{"theme":{"primaryColor":"#e1251b","backgroundColor":"#f5f5f7","textColor":"#1d1d1f"},"modules":[{"id":"hero","type":"BANNER","visible":true,"data":{"title":"NOVA 数字办公旗舰店","subtitle":"企业级好物","imageUrl":""}},{"id":"notice","type":"ANNOUNCEMENT","visible":true,"data":{"text":"工作日 16:00 前下单当日发货"}},{"id":"products","type":"PRODUCT_GRID","visible":true,"data":{"title":"店铺精选","limit":4}},{"id":"coupon","type":"COUPON","visible":true,"data":{"title":"新客礼遇","description":"首单满 999 减 100"}}]}'::jsonb)
) AS defaults(channel, config);
