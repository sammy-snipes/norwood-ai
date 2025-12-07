-- Add payment type to distinguish donations from premium purchases
ALTER TABLE payments ADD COLUMN type VARCHAR(20) NOT NULL DEFAULT 'premium';

-- Update index for querying by type
CREATE INDEX idx_payments_type ON payments(type);
