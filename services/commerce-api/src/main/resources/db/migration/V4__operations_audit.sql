CREATE TABLE operation_audit_log (
    id UUID PRIMARY KEY,
    actor_id VARCHAR(120) NOT NULL,
    action VARCHAR(80) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(120) NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_resource ON operation_audit_log(resource_type, resource_id, occurred_at DESC);
