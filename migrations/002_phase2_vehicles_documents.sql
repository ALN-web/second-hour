-- ==============================================================================
-- Second Hour Migration: 002_phase2_vehicles_documents
-- Description: Phase 2 Vehicles & Central Documents Management Layer
-- Dialect: PostgreSQL (Neon Serverless) / Idempotent & Non-Destructive
-- ==============================================================================

-- 1. Ensure schema_migrations table exists
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Refine vehicles table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicles' AND column_name='is_primary') THEN
        ALTER TABLE vehicles ADD COLUMN is_primary BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicles' AND column_name='is_active') THEN
        ALTER TABLE vehicles ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicles' AND column_name='registration_date') THEN
        ALTER TABLE vehicles ADD COLUMN registration_date DATE NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicles' AND column_name='deleted_at') THEN
        ALTER TABLE vehicles ADD COLUMN deleted_at TIMESTAMPTZ NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_vehicles_user_active ON vehicles(user_id, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS ix_vehicles_user_reg_active ON vehicles(user_id, registration_number) WHERE deleted_at IS NULL AND is_active IS TRUE;

-- 3. Refine vehicle_photos table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_photos' AND column_name='storage_key') THEN
        ALTER TABLE vehicle_photos ADD COLUMN storage_key TEXT DEFAULT '' NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_photos' AND column_name='file_size_bytes') THEN
        ALTER TABLE vehicle_photos ADD COLUMN file_size_bytes INTEGER DEFAULT 0 NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_photos' AND column_name='sha256') THEN
        ALTER TABLE vehicle_photos ADD COLUMN sha256 VARCHAR(64) NULL;
    END IF;
END $$;

-- Populate storage_key from stored_path if empty
UPDATE vehicle_photos SET storage_key = stored_path WHERE storage_key = '' AND stored_path IS NOT NULL AND stored_path != '';

-- 4. Refine central_documents table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='central_documents' AND column_name='storage_key') THEN
        ALTER TABLE central_documents ADD COLUMN storage_key TEXT DEFAULT '' NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='central_documents' AND column_name='current_version') THEN
        ALTER TABLE central_documents ADD COLUMN current_version INTEGER DEFAULT 1 NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='central_documents' AND column_name='is_active') THEN
        ALTER TABLE central_documents ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='central_documents' AND column_name='deleted_at') THEN
        ALTER TABLE central_documents ADD COLUMN deleted_at TIMESTAMPTZ NULL;
    END IF;
END $$;

-- Populate storage_key from stored_path if empty
UPDATE central_documents SET storage_key = stored_path WHERE storage_key = '' AND stored_path IS NOT NULL AND stored_path != '';

CREATE INDEX IF NOT EXISTS ix_central_docs_user_active ON central_documents(user_id, is_active);

-- 5. Create document_versions table
CREATE TABLE IF NOT EXISTS document_versions (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES central_documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    storage_key TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    uploaded_by VARCHAR(64) NOT NULL REFERENCES users(id),
    change_summary VARCHAR(255) NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_document_version UNIQUE (document_id, version_number)
);

CREATE INDEX IF NOT EXISTS ix_document_versions_doc ON document_versions(document_id);
CREATE INDEX IF NOT EXISTS ix_document_versions_uploader ON document_versions(uploaded_by);

-- 6. Create document_access_logs table
CREATE TABLE IF NOT EXISTS document_access_logs (
    id BIGSERIAL PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES central_documents(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    action VARCHAR(32) NOT NULL, -- 'view', 'download', 'upload', 'replace', 'delete'
    access_channel VARCHAR(32) DEFAULT 'web_dashboard' NOT NULL,
    purpose VARCHAR(100) NULL,
    case_id VARCHAR(64) NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_doc_access_doc_time ON document_access_logs(document_id, accessed_at);
CREATE INDEX IF NOT EXISTS ix_doc_access_user_time ON document_access_logs(user_id, accessed_at);

-- 7. Refine vehicle_insurance_policies table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_insurance_policies' AND column_name='is_current_policy') THEN
        ALTER TABLE vehicle_insurance_policies ADD COLUMN is_current_policy BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_insurance_policies' AND column_name='policy_status') THEN
        ALTER TABLE vehicle_insurance_policies ADD COLUMN policy_status VARCHAR(32) DEFAULT 'active' NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_insurance_policies' AND column_name='superseded_by_policy_id') THEN
        ALTER TABLE vehicle_insurance_policies ADD COLUMN superseded_by_policy_id VARCHAR(64) NULL REFERENCES vehicle_insurance_policies(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_insurance_policies' AND column_name='coverage_details') THEN
        ALTER TABLE vehicle_insurance_policies ADD COLUMN coverage_details TEXT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vehicle_insurance_policies' AND column_name='updated_at') THEN
        ALTER TABLE vehicle_insurance_policies ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_vehicle_insurance_curr ON vehicle_insurance_policies(vehicle_id, is_current_policy);

-- 8. Record Migration in history
INSERT INTO schema_migrations (version, description)
VALUES ('002_phase2_vehicles_documents', 'Phase 2: Vehicles, Central Documents, Document Versions, Access Logs, and Insurance Policies')
ON CONFLICT (version) DO NOTHING;
