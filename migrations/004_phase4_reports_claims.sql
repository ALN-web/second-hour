-- Second Hour — Phase 4: Reports, Insurance Claims & External Submissions Migration
-- Database: Neon PostgreSQL
-- Safe, non-destructive migration applying Domain 4 schema additions and refinements.

-- 1. Upgrade existing `reports` table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS title VARCHAR(255) DEFAULT 'Accident Case Summary Report' NOT NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_type VARCHAR(64) DEFAULT 'accident_summary' NOT NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'draft' NOT NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS current_version_id VARCHAR(64);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS generation_source VARCHAR(32) DEFAULT 'ai_generated' NOT NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS approved_by VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE reports ALTER COLUMN path DROP NOT NULL;

CREATE INDEX IF NOT EXISTS ix_reports_case_id ON reports(case_id);
CREATE INDEX IF NOT EXISTS ix_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS ix_reports_case_status ON reports(case_id, status);

-- 2. Create `report_versions` table
CREATE TABLE IF NOT EXISTS report_versions (
    id VARCHAR(64) PRIMARY KEY,
    report_id VARCHAR(64) NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    content_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    storage_key TEXT,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    sha256 VARCHAR(64),
    generated_by VARCHAR(64) NOT NULL REFERENCES users(id),
    generation_method VARCHAR(32) DEFAULT 'ai_assisted' NOT NULL,
    ai_model VARCHAR(64),
    source_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    version_status VARCHAR(32) DEFAULT 'draft' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_report_version UNIQUE (report_id, version_number)
);

CREATE INDEX IF NOT EXISTS ix_report_versions_report ON report_versions(report_id);
CREATE INDEX IF NOT EXISTS ix_report_versions_created ON report_versions(created_at DESC);

-- Add foreign key constraint for current_version_id if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_reports_current_version'
    ) THEN
        ALTER TABLE reports ADD CONSTRAINT fk_reports_current_version 
        FOREIGN KEY (current_version_id) REFERENCES report_versions(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 3. Create `insurance_claims` table
CREATE TABLE IF NOT EXISTS insurance_claims (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    vehicle_id VARCHAR(64) REFERENCES vehicles(id) ON DELETE SET NULL,
    policy_id VARCHAR(64) REFERENCES vehicle_insurance_policies(id) ON DELETE SET NULL,
    created_by VARCHAR(64) NOT NULL REFERENCES users(id),
    insurer_name VARCHAR(150) NOT NULL,
    policy_number VARCHAR(100) NOT NULL,
    claim_reference_number VARCHAR(100),
    claim_type VARCHAR(64) DEFAULT 'own_damage' NOT NULL,
    incident_date TIMESTAMPTZ NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    estimated_amount NUMERIC(12, 2),
    approved_amount NUMERIC(12, 2),
    claim_status VARCHAR(64) DEFAULT 'draft' NOT NULL,
    filed_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ,
    surveyor_name VARCHAR(120),
    surveyor_phone VARCHAR(32),
    cashless_garage VARCHAR(200),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_claims_case ON insurance_claims(case_id);
CREATE INDEX IF NOT EXISTS ix_claims_status ON insurance_claims(claim_status);
CREATE INDEX IF NOT EXISTS ix_claims_created_by ON insurance_claims(created_by);

-- 4. Create `external_submissions` table
CREATE TABLE IF NOT EXISTS external_submissions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    report_id VARCHAR(64) REFERENCES reports(id) ON DELETE SET NULL,
    claim_id VARCHAR(64) REFERENCES insurance_claims(id) ON DELETE SET NULL,
    submitted_by VARCHAR(64) NOT NULL REFERENCES users(id),
    external_org_name VARCHAR(150) NOT NULL,
    external_org_type VARCHAR(64) DEFAULT 'insurer' NOT NULL,
    external_reference_number VARCHAR(100),
    submission_method VARCHAR(64) DEFAULT 'manual_user_submission' NOT NULL,
    submission_status VARCHAR(32) DEFAULT 'draft' NOT NULL,
    submitted_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    response_at TIMESTAMPTZ,
    failure_reason TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ext_sub_case ON external_submissions(case_id);
CREATE INDEX IF NOT EXISTS ix_ext_sub_status ON external_submissions(case_id, submission_status);
CREATE INDEX IF NOT EXISTS ix_ext_sub_submitted_by ON external_submissions(submitted_by);

-- 5. Record migrations in schema_migrations
INSERT INTO schema_migrations (version, description, applied_at)
VALUES
    ('003_phase3_case_management', 'Phase 3: Accident Cases & Case Management', CURRENT_TIMESTAMP),
    ('004_phase4_reports_claims', 'Phase 4: Reports, Insurance Claims & External Submissions', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;
