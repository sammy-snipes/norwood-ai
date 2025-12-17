-- Create forum tables for message board feature

-- Create enums
CREATE TYPE agent_type AS ENUM ('expert', 'comedian', 'kind', 'jerk');
CREATE TYPE forum_reply_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- Create forum threads table
CREATE TABLE forum_threads (
    id CHAR(26) PRIMARY KEY,
    user_id CHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_forum_threads_user_id ON forum_threads(user_id);
CREATE INDEX idx_forum_threads_created_at ON forum_threads(created_at DESC);
CREATE INDEX idx_forum_threads_updated_at ON forum_threads(updated_at DESC);
CREATE INDEX idx_forum_threads_pinned ON forum_threads(is_pinned) WHERE is_pinned = TRUE;

-- Create forum replies table
CREATE TABLE forum_replies (
    id CHAR(26) PRIMARY KEY,
    thread_id CHAR(26) NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
    user_id CHAR(26) REFERENCES users(id) ON DELETE SET NULL,
    parent_id CHAR(26) REFERENCES forum_replies(id) ON DELETE CASCADE,
    content TEXT,
    status forum_reply_status NOT NULL DEFAULT 'completed',
    agent_type agent_type,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_forum_replies_thread_id ON forum_replies(thread_id);
CREATE INDEX idx_forum_replies_parent_id ON forum_replies(parent_id);
CREATE INDEX idx_forum_replies_user_id ON forum_replies(user_id);
CREATE INDEX idx_forum_replies_status ON forum_replies(status) WHERE status != 'completed';
CREATE INDEX idx_forum_replies_created_at ON forum_replies(created_at);

-- Create agent schedules table for exponential backoff
CREATE TABLE forum_agent_schedules (
    id CHAR(26) PRIMARY KEY,
    thread_id CHAR(26) NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
    agent_type agent_type NOT NULL,
    next_reply_at TIMESTAMPTZ,
    reply_count INTEGER DEFAULT 0 NOT NULL,
    last_replied_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_agent_schedule_thread_agent UNIQUE (thread_id, agent_type)
);

CREATE INDEX idx_forum_agent_schedules_thread_id ON forum_agent_schedules(thread_id);
CREATE INDEX idx_forum_agent_schedules_next_reply ON forum_agent_schedules(next_reply_at)
    WHERE is_active = TRUE AND next_reply_at IS NOT NULL;
