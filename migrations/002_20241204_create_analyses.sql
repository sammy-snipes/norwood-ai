-- Create analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id CHAR(26) PRIMARY KEY,  -- ULID generated in app
    user_id CHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT,  -- S3 path to uploaded image
    norwood_stage INTEGER NOT NULL CHECK (norwood_stage >= 1 AND norwood_stage <= 7),
    confidence VARCHAR(20) NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    roast TEXT NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
