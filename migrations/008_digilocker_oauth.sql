-- Migration 008: DigiLocker OAuth 2.0 State and Encrypted Token Management
-- Date: 2026-11-28
-- Applies to: Neon PostgreSQL

-- 1. Create digilocker_oauth_states table for secure state and encrypted PKCE verifiers
CREATE TABLE IF NOT EXISTS digilocker_oauth_states (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state VARCHAR(128) NOT NULL UNIQUE,
    encrypted_code_verifier TEXT NOT NULL,
    code_challenge VARCHAR(128) NOT NULL,
    code_challenge_method VARCHAR(16) NOT NULL DEFAULT 'S256',
    redirect_uri VARCHAR(255) NOT NULL,
    doc_type VARCHAR(64),
    is_consumed BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    consumed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_digilocker_oauth_states_state ON digilocker_oauth_states(state);
CREATE INDEX IF NOT EXISTS ix_digilocker_oauth_states_user_consumed ON digilocker_oauth_states(user_id, is_consumed);

-- 2. Create user_digilocker_connections table for encrypted OAuth access and refresh tokens
CREATE TABLE IF NOT EXISTS user_digilocker_connections (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    digilocker_id VARCHAR(128),
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    token_scope VARCHAR(255),
    token_type VARCHAR(32) DEFAULT 'Bearer',
    access_token_expires_at TIMESTAMP WITH TIME ZONE,
    refresh_token_expires_at TIMESTAMP WITH TIME ZONE,
    connection_status VARCHAR(32) NOT NULL DEFAULT 'connected' CHECK (connection_status IN ('connected', 'disconnected', 'expired', 'revoked')),
    connected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_refreshed_at TIMESTAMP WITH TIME ZONE,
    disconnected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_digilocker_connections_user ON user_digilocker_connections(user_id);
CREATE INDEX IF NOT EXISTS ix_user_digilocker_connections_status ON user_digilocker_connections(user_id, connection_status);

-- 3. Record Migration in schema_migrations
INSERT INTO schema_migrations (version, description)
VALUES ('008_digilocker_oauth', 'DigiLocker OAuth 2.0 PKCE states and encrypted token storage')
ON CONFLICT (version) DO NOTHING;
