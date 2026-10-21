ALTER TABLE ai_conversations
    ADD COLUMN IF NOT EXISTS merchant_id UUID REFERENCES merchants(id);

-- Legacy installations only had one merchant, so their existing conversations can
-- be assigned without guessing. Multi-merchant installations keep legacy rows
-- unassigned, while the NOT VALID check still rejects every new unscoped row.
UPDATE ai_conversations
SET merchant_id = (SELECT id FROM merchants ORDER BY created_at, id LIMIT 1)
WHERE merchant_id IS NULL
  AND (SELECT COUNT(*) FROM merchants) = 1;

ALTER TABLE ai_conversations
    ADD CONSTRAINT ai_conversations_merchant_required
    CHECK (merchant_id IS NOT NULL) NOT VALID;

CREATE INDEX IF NOT EXISTS idx_ai_conversations_merchant_started
    ON ai_conversations(merchant_id, started_at DESC);
