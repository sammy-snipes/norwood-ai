-- Game 2048 scores table
CREATE TABLE IF NOT EXISTS game_2048_scores (
    id VARCHAR(26) PRIMARY KEY,
    user_id VARCHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    highest_tile INTEGER NOT NULL,
    is_win BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_2048_scores_user_id ON game_2048_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_game_2048_scores_score ON game_2048_scores(score DESC);
CREATE INDEX IF NOT EXISTS idx_game_2048_scores_created_at ON game_2048_scores(created_at);
