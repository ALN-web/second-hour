-- ==============================================================================
-- Second Hour Migration: 001_phase1_user_foundation
-- Description: Phase 1 Foundation Layer (User Profiles, Addresses, Emergency Contacts & Permissions, Medical & Access Logs)
-- Dialect: PostgreSQL (Neon Serverless) / Idempotent & Non-Destructive
-- ==============================================================================

-- 1. Migration History Tracking Table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Users Table (Ensure baseline columns exist without altering existing data)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    role_label VARCHAR(100) DEFAULT '' NOT NULL,
    email VARCHAR(255) NULL,
    email_verified BOOLEAN DEFAULT FALSE NOT NULL,
    phone VARCHAR(32) NULL,
    phone_verified BOOLEAN DEFAULT FALSE NOT NULL,
    date_of_birth DATE NULL,
    gender VARCHAR(32) NULL,
    profile_photo TEXT NULL,
    preferred_language VARCHAR(50) DEFAULT 'English' NOT NULL,
    account_status VARCHAR(32) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email) WHERE email IS NOT NULL AND email != '';
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users(phone) WHERE phone IS NOT NULL AND phone != '';

-- 3. User Addresses Table
CREATE TABLE IF NOT EXISTS user_addresses (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address_type VARCHAR(32) NOT NULL, -- 'current' | 'permanent'
    address_line_1 VARCHAR(255) NOT NULL,
    address_line_2 VARCHAR(255) NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pin_code VARCHAR(12) NOT NULL,
    country VARCHAR(64) DEFAULT 'India' NOT NULL,
    is_same_as_current BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_user_address_type UNIQUE (user_id, address_type)
);

CREATE INDEX IF NOT EXISTS ix_user_addresses_user ON user_addresses(user_id);

-- 4. Emergency Contacts Table
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(120) NOT NULL,
    relationship VARCHAR(64) NOT NULL,
    mobile_number VARCHAR(32) NOT NULL,
    alternate_number VARCHAR(32) NULL,
    email VARCHAR(255) NULL,
    priority INTEGER DEFAULT 1 NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    preferred_contact_method VARCHAR(32) DEFAULT 'phone' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_emergency_contacts_user_prio ON emergency_contacts(user_id, priority);

-- 5. Emergency Contact Permissions Table (1:1 with emergency_contacts)
CREATE TABLE IF NOT EXISTS emergency_contact_permissions (
    id VARCHAR(64) PRIMARY KEY,
    contact_id VARCHAR(64) NOT NULL UNIQUE REFERENCES emergency_contacts(id) ON DELETE CASCADE,
    can_notify_accident_sos BOOLEAN DEFAULT TRUE NOT NULL,
    can_receive_case_sms BOOLEAN DEFAULT TRUE NOT NULL,
    can_receive_whatsapp_updates BOOLEAN DEFAULT FALSE NOT NULL,
    has_workspace_access BOOLEAN DEFAULT FALSE NOT NULL,
    permitted_case_ids VARCHAR(255) DEFAULT '[]' NOT NULL,
    workspace_role VARCHAR(32) DEFAULT 'viewer' NOT NULL,
    can_view_limited_summary_only BOOLEAN DEFAULT TRUE NOT NULL,
    can_view_medical BOOLEAN DEFAULT FALSE NOT NULL,
    can_view_documents BOOLEAN DEFAULT FALSE NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ec_permissions_contact ON emergency_contact_permissions(contact_id);

-- Backward compatibility columns for existing schema instances if needed
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_notify_accident_sos') THEN
        ALTER TABLE emergency_contact_permissions ADD COLUMN can_notify_accident_sos BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_receive_case_sms') THEN
        ALTER TABLE emergency_contact_permissions ADD COLUMN can_receive_case_sms BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_receive_whatsapp_updates') THEN
        ALTER TABLE emergency_contact_permissions ADD COLUMN can_receive_whatsapp_updates BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='has_workspace_access') THEN
        ALTER TABLE emergency_contact_permissions ADD COLUMN has_workspace_access BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='workspace_role') THEN
        ALTER TABLE emergency_contact_permissions ADD COLUMN workspace_role VARCHAR(32) DEFAULT 'viewer' NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_view_limited_summary_only') THEN
        ALTER TABLE emergency_contact_permissions ADD COLUMN can_view_limited_summary_only BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;

    -- Add unique constraint on contact_id if not present
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_ec_permissions_contact'
    ) THEN
        BEGIN
            ALTER TABLE emergency_contact_permissions ADD CONSTRAINT uq_ec_permissions_contact UNIQUE (contact_id);
        EXCEPTION WHEN duplicate_table OR duplicate_object THEN
            NULL;
        END;
    END IF;

    -- Add unique constraint on (user_id, address_type) if not present
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_address_type'
    ) THEN
        BEGIN
            ALTER TABLE user_addresses ADD CONSTRAINT uq_user_address_type UNIQUE (user_id, address_type);
        EXCEPTION WHEN duplicate_table OR duplicate_object THEN
            NULL;
        END;
    END IF;

    -- Clean up legacy column names if present
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_notify_accident') THEN
        ALTER TABLE emergency_contact_permissions DROP COLUMN IF EXISTS can_notify_accident;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_receive_case_updates') THEN
        ALTER TABLE emergency_contact_permissions DROP COLUMN IF EXISTS can_receive_case_updates;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_access_case') THEN
        ALTER TABLE emergency_contact_permissions DROP COLUMN IF EXISTS can_access_case;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='emergency_contact_permissions' AND column_name='can_view_limited_case_info') THEN
        ALTER TABLE emergency_contact_permissions DROP COLUMN IF EXISTS can_view_limited_case_info;
    END IF;
END $$;

-- 6. Medical Information Table (Quarantined, private by default)
CREATE TABLE IF NOT EXISTS medical_information (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    blood_group VARCHAR(10) NULL,
    allergies TEXT NULL,
    medical_conditions TEXT NULL,
    medications TEXT NULL,
    emergency_notes TEXT NULL,
    share_with_ems BOOLEAN DEFAULT FALSE NOT NULL,
    share_with_ai BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_medical_info_user ON medical_information(user_id);

-- 7. Medical Access Logs Table (Append-only audit trail)
CREATE TABLE IF NOT EXISTS medical_access_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actor_id VARCHAR(64) NOT NULL REFERENCES users(id),
    access_purpose VARCHAR(100) NOT NULL,
    authorization_type VARCHAR(64) NOT NULL,
    fields_accessed TEXT DEFAULT '[]' NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_med_access_user_time ON medical_access_logs(user_id, accessed_at);
CREATE INDEX IF NOT EXISTS ix_med_access_actor_time ON medical_access_logs(actor_id, accessed_at);

-- 8. Record Migration
INSERT INTO schema_migrations (version, description)
VALUES ('001_phase1_user_foundation', 'Phase 1: Foundation Layer (user_addresses, emergency_contacts, permissions, medical_info, medical_access_logs)')
ON CONFLICT (version) DO NOTHING;
