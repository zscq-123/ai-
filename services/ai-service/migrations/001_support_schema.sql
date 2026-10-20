CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY,
    customer_id UUID,
    status VARCHAR(24) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    handed_off_at TIMESTAMPTZ
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
