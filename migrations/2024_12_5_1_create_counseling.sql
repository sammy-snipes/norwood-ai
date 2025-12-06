-- Drop existing tables and types if they exist
DROP TABLE IF EXISTS counseling_messages CASCADE;

DROP TABLE IF EXISTS counseling_sessions CASCADE;

DROP TYPE IF EXISTS message_role CASCADE;

DROP TYPE IF EXISTS message_status CASCADE;

-- Create enums for counseling
CREATE TYPE message_role AS ENUM ('user', 'assistant');

CREATE TYPE message_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- Create counseling sessions table
CREATE TABLE counseling_sessions (
    id CHAR(26) PRIMARY KEY,
    user_id CHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_counseling_sessions_user_id ON counseling_sessions(user_id);

-- Create counseling messages table
CREATE TABLE counseling_messages (
    id CHAR(26) PRIMARY KEY,
    session_id CHAR(26) NOT NULL REFERENCES counseling_sessions(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT,
    status message_status NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_counseling_messages_session_id ON counseling_messages(session_id);

CREATE INDEX idx_counseling_messages_status ON counseling_messages(status);