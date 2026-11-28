-- Migration 007: OTP Security Hardening (Purpose Binding & Pending Contact Changes)
-- Date: 2026-11-27
-- Applies to: Neon PostgreSQL

-- 1. Add purpose column to otp_verifications with check constraint and index
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS purpose VARCHAR(32) NOT NULL DEFAULT 'email_verify';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_otp_purpose'
    ) THEN
        ALTER TABLE otp_verifications ADD CONSTRAINT chk_otp_purpose 
            CHECK (purpose IN ('email_verify', 'phone_verify', 'step_up', 'email_change', 'phone_change'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_otp_verifications_user_purpose ON otp_verifications(user_id, purpose, is_used);
CREATE INDEX IF NOT EXISTS ix_otp_verifications_user_channel_purpose ON otp_verifications(user_id, channel, purpose, is_used);

-- 2. Add pending contact fields to users to prevent silent replacement of verified contacts
ALTER TABLE users ADD COLUMN IF NOT EXISTS pending_email VARCHAR(128);
ALTER TABLE users ADD COLUMN IF NOT EXISTS pending_phone VARCHAR(32);
