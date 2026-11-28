-- Migration 009: OTP Delivery Tracking & Status Pipeline
-- Date: 2026-11-28
-- Applies to: Neon PostgreSQL / SQLite

-- 1. Add delivery tracking fields to otp_verifications
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(32) NOT NULL DEFAULT 'GENERATED';
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS delivery_provider VARCHAR(32);
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS delivery_reference_id VARCHAR(128);
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS delivery_error TEXT;

-- 2. Add index for delivery status lookups and audit queries
CREATE INDEX IF NOT EXISTS ix_otp_verifications_delivery_status ON otp_verifications(delivery_status);
CREATE INDEX IF NOT EXISTS ix_otp_verifications_channel_status ON otp_verifications(channel, delivery_status);
