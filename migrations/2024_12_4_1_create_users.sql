-- Active: 1764959920144@@norwood-db1.cmxc44w2iyxs.us-east-1.rds.amazonaws.com@5432@postgres@public
-- Create users table
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id CHAR(26) PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    is_premium BOOLEAN DEFAULT FALSE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    free_analyses_remaining INTEGER DEFAULT 1 NOT NULL,
    options JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_users_google_id ON users(google_id);

CREATE INDEX idx_users_email ON users(email);