-- Sandstone Memory Schema (PostgreSQL) — v2.1
-- Variable renames: aahs→lcs, tds_score→lds_score


CREATE TABLE IF NOT EXISTS memory_nodes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    sdv DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cscv DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    lcs DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    swv DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    pdv DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    base_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    current_salience DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    lds_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    corrected_salience DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    processing_count INTEGER DEFAULT 0,
    last_processed TIMESTAMP,
    decay_rate DOUBLE PRECISION DEFAULT 0.01,
    spike_coefficient DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_ratings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    exchange_number INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    response_a_text TEXT NOT NULL,
    response_b_text TEXT NOT NULL,
    response_a_attunement INTEGER CHECK(response_a_attunement BETWEEN 1 AND 7),
    response_a_contextual_accuracy INTEGER CHECK(response_a_contextual_accuracy BETWEEN 1 AND 7),
    response_a_naturalness INTEGER CHECK(response_a_naturalness BETWEEN 1 AND 7),
    response_b_attunement INTEGER CHECK(response_b_attunement BETWEEN 1 AND 7),
    response_b_contextual_accuracy INTEGER CHECK(response_b_contextual_accuracy BETWEEN 1 AND 7),
    response_b_naturalness INTEGER CHECK(response_b_naturalness BETWEEN 1 AND 7),
    preference TEXT CHECK(preference IN ('A', 'B', 'none')),
    which_is_sandstone TEXT CHECK(which_is_sandstone IN ('A', 'B')),
    memory_state_snapshot TEXT,
    model_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_participants (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    display_name TEXT,
    password_hash TEXT,
    sandstone_panel TEXT CHECK(sandstone_panel IN ('A', 'B')),
    consent_given_at TIMESTAMP,
    session_count INTEGER DEFAULT 0,
    total_exchanges INTEGER DEFAULT 0,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    panel TEXT CHECK(panel IN ('sandstone', 'baseline')),
    role TEXT CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    exchange_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_nodes_user_id ON memory_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_nodes_salience ON memory_nodes(corrected_salience DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user ON study_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_history_user_session ON conversation_history(user_id, session_number);
CREATE INDEX IF NOT EXISTS idx_history_panel ON conversation_history(user_id, panel);
CREATE INDEX IF NOT EXISTS idx_participants_email ON study_participants(email);
