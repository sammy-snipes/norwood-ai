-- Create analyses table
DROP TABLE IF EXISTS analyses CASCADE;

CREATE TABLE analyses (
    id CHAR(26) PRIMARY KEY,
    user_id CHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT,
    norwood_stage INTEGER NOT NULL CHECK (norwood_stage >= 0 AND norwood_stage <= 7),
    confidence VARCHAR(20) NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    title VARCHAR(100) NOT NULL,
    analysis_text TEXT NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_created_at ON analyses(created_at DESC);
