ALTER TABLE products ADD COLUMN IF NOT EXISTS brand VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(10,3) CHECK (weight_kg IS NULL OR weight_kg >= 0);

UPDATE products
SET brand = COALESCE(brand, 'NOVA'),
    description = COALESCE(description, subtitle),
    weight_kg = COALESCE(weight_kg, 0);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY,
    customer_id UUID,
    status VARCHAR(24) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    handed_off_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    satisfaction_score NUMERIC(3,1) CHECK (satisfaction_score BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(40),
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_name VARCHAR(100),
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_started ON ai_conversations(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation ON ai_messages(conversation_id, created_at);
