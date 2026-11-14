-- REQ-PAY-230: speed up retry lookups.
CREATE INDEX idx_transfers_idem ON transfers (idempotency_key);
