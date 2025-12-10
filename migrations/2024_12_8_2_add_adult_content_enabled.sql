-- Add adult_content_enabled column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS adult_content_enabled BOOLEAN NOT NULL DEFAULT FALSE;
