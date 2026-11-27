-- Migration 006: Identity & Document Verification System
-- Date: 2026-11-27
-- Applies to: Neon PostgreSQL

-- 1. Create verification_records table for immutable verification tracking
CREATE TABLE IF NOT EXISTS verification_records (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type VARCHAR(32) NOT NULL, -- 'USER_EMAIL', 'USER_PHONE', 'IDENTITY_DOCUMENT', 'VEHICLE_RC', 'VEHICLE_INSURANCE'
    entity_id VARCHAR(64) NOT NULL,   -- user_id, document_id, vehicle_id, policy_id
    provider VARCHAR(32) NOT NULL,    -- 'DIGILOCKER', 'VAHAN_PARIVAHAN', 'IIB_INSURANCE', 'SMS_OTP', 'EMAIL_OTP'
    status VARCHAR(20) NOT NULL,      -- 'PENDING', 'VERIFIED', 'FAILED', 'REVOKED'
    verification_type VARCHAR(32) NOT NULL, -- 'OTP', 'API_MATCH', 'OAUTH_DIGILOCKER'
    verification_reference_id VARCHAR(128),
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    verified_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    consent_record_id VARCHAR(64) REFERENCES consent_records(id),
    raw_response_hash VARCHAR(64),
    verified_metadata JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_verification_records_entity ON verification_records(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_verification_records_user ON verification_records(user_id);
CREATE INDEX IF NOT EXISTS ix_verification_records_ref ON verification_records(verification_reference_id);

-- 2. Create otp_verifications table for salted hashed OTPs (no plaintext OTP storage)
CREATE TABLE IF NOT EXISTS otp_verifications (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(16) NOT NULL,     -- 'email', 'phone'
    target VARCHAR(128) NOT NULL,     -- email address or phone number
    otp_hash VARCHAR(64) NOT NULL,    -- Salted SHA-256 hash
    salt VARCHAR(32) NOT NULL,        -- Cryptographic random salt
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_otp_verifications_user_channel ON otp_verifications(user_id, channel, is_used);

-- 3. Add verification columns to vehicles
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified';
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS verification_provider VARCHAR(32);
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS verification_reference_id VARCHAR(128);

-- 4. Update central_documents verification columns & ensure unverified default
ALTER TABLE central_documents ALTER COLUMN verification_status SET DEFAULT 'unverified';
ALTER TABLE central_documents ADD COLUMN IF NOT EXISTS verification_provider VARCHAR(32);
ALTER TABLE central_documents ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE central_documents ADD COLUMN IF NOT EXISTS verification_reference_id VARCHAR(128);
ALTER TABLE central_documents ADD COLUMN IF NOT EXISTS verification_failure_reason TEXT;
