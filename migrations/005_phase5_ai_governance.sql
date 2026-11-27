-- Second Hour — Phase 5: AI Conversations, Privacy, Consent & Governance Migration
-- Database: Neon PostgreSQL
-- Safe, non-destructive migration applying Domain 5 schema additions and refinements.

-- 1. Upgrade existing `conversations` table
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS case_id VARCHAR(64) REFERENCES cases(id) ON DELETE SET NULL;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'active' NOT NULL;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(64) DEFAULT 'gemini' NOT NULL;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS model_identifier VARCHAR(64);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_conversations_user_status ON conversations(user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_conversations_case ON conversations(case_id);

-- 2. Upgrade existing `conversation_messages` table
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS sender_type VARCHAR(32) DEFAULT 'user' NOT NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS content_format VARCHAR(32) DEFAULT 'text' NOT NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS sequence_number INTEGER DEFAULT 1 NOT NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS tool_call_id VARCHAR(64);
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS source_references_json JSONB DEFAULT '[]'::jsonb NOT NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS ai_model_metadata JSONB DEFAULT '{}'::jsonb NOT NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS token_usage_metadata JSONB DEFAULT '{}'::jsonb NOT NULL;

CREATE INDEX IF NOT EXISTS ix_conv_msg_seq ON conversation_messages(conversation_id, sequence_number);

-- 3. Create `ai_action_logs` table
CREATE TABLE IF NOT EXISTS ai_action_logs (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(64) REFERENCES conversations(id) ON DELETE SET NULL,
    case_id VARCHAR(64) REFERENCES cases(id) ON DELETE SET NULL,
    action_type VARCHAR(64) NOT NULL,
    action_description TEXT NOT NULL,
    input_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    output_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    action_status VARCHAR(32) DEFAULT 'proposed' NOT NULL,
    approval_required BOOLEAN DEFAULT TRUE NOT NULL,
    approved_by VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    approval_timestamp TIMESTAMPTZ,
    execution_timestamp TIMESTAMPTZ,
    failure_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ai_action_user_status ON ai_action_logs(user_id, action_status);
CREATE INDEX IF NOT EXISTS ix_ai_action_conversation ON ai_action_logs(conversation_id);
CREATE INDEX IF NOT EXISTS ix_ai_action_case ON ai_action_logs(case_id);

-- 4. Upgrade `user_privacy_preferences` table
ALTER TABLE user_privacy_preferences ADD COLUMN IF NOT EXISTS conversation_retention_days INTEGER DEFAULT 365 NOT NULL;
ALTER TABLE user_privacy_preferences ADD COLUMN IF NOT EXISTS personalization_enabled BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE user_privacy_preferences ADD COLUMN IF NOT EXISTS analytics_enabled BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE user_privacy_preferences ADD COLUMN IF NOT EXISTS data_sharing_preferences JSONB DEFAULT '{"anonymized_research": false, "insurer_direct_share": false}'::jsonb NOT NULL;
ALTER TABLE user_privacy_preferences ADD COLUMN IF NOT EXISTS medical_info_sharing_enabled BOOLEAN DEFAULT FALSE NOT NULL;

-- 5. Upgrade `user_notification_preferences` table
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS push_notifications BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS ai_action_notifications BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS quiet_hours_enabled BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS quiet_hours_start VARCHAR(8) DEFAULT '22:00' NOT NULL;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS quiet_hours_end VARCHAR(8) DEFAULT '07:00' NOT NULL;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS quiet_hours_timezone VARCHAR(64) DEFAULT 'Asia/Kolkata' NOT NULL;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(32) DEFAULT 'English' NOT NULL;

-- 6. Create `consent_records` table
CREATE TABLE IF NOT EXISTS consent_records (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(64) NOT NULL,
    consent_status VARCHAR(32) DEFAULT 'granted' NOT NULL,
    policy_version VARCHAR(32) DEFAULT '1.0' NOT NULL,
    consent_source VARCHAR(64) DEFAULT 'web_application' NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    metadata_json JSONB DEFAULT '{}'::jsonb NOT NULL,
    consent_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    revoked_at TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_consent_user_type_status ON consent_records(user_id, consent_type, consent_status);
CREATE INDEX IF NOT EXISTS ix_consent_user_timestamp ON consent_records(user_id, consent_timestamp DESC);

-- 7. Upgrade `audit_log` table
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_type VARCHAR(32) DEFAULT 'user' NOT NULL;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS action_type VARCHAR(64) DEFAULT 'action' NOT NULL;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS resource_type VARCHAR(64) DEFAULT 'general' NOT NULL;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS resource_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS action_outcome VARCHAR(32) DEFAULT 'success' NOT NULL;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS request_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS sanitized_metadata JSONB DEFAULT '{}'::jsonb NOT NULL;

CREATE INDEX IF NOT EXISTS ix_audit_actor_at ON audit_log(actor_id, at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS ix_audit_action_outcome ON audit_log(action_type, action_outcome);
