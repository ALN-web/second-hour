-- Second Hour — Phase 3: Accident Cases & Case Management Migration
-- Database: Neon PostgreSQL
-- Safe, non-destructive migration applying Domain 3 schema additions and refinements.

-- 1. Enforce cases table refinements
ALTER TABLE cases ADD COLUMN IF NOT EXISTS title VARCHAR(200);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS owner_id VARCHAR(64) REFERENCES users(id);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS primary_vehicle_id VARCHAR(64) REFERENCES vehicles(id) ON DELETE SET NULL;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ NULL;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;

-- Backfill cases owner_id and primary_vehicle_id where applicable
UPDATE cases SET owner_id = created_by WHERE owner_id IS NULL;
UPDATE cases SET primary_vehicle_id = vehicle_id WHERE primary_vehicle_id IS NULL AND vehicle_id IS NOT NULL;
UPDATE cases SET title = COALESCE(title, accident_type || ' — ' || approximate_location) WHERE title IS NULL;

CREATE INDEX IF NOT EXISTS ix_cases_owner ON cases(owner_id);
CREATE INDEX IF NOT EXISTS ix_cases_status_active ON cases(status, is_active);
CREATE INDEX IF NOT EXISTS ix_cases_number ON cases(case_number);

-- 2. Create case_status_transitions table
CREATE TABLE IF NOT EXISTS case_status_transitions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    from_status VARCHAR(32) NOT NULL,
    to_status VARCHAR(32) NOT NULL,
    changed_by VARCHAR(64) NOT NULL REFERENCES users(id),
    transition_trigger VARCHAR(64) DEFAULT 'manual_user_action' NOT NULL,
    reason TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_case_status_trans_case ON case_status_transitions(case_id, created_at);

-- 3. Refine case_members table
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS id VARCHAR(64);
UPDATE case_members SET id = 'cm_' || case_id || '_' || user_id WHERE id IS NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS member_name VARCHAR(120);
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS member_email VARCHAR(120);
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS member_phone VARCHAR(32);
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS invitation_status VARCHAR(32) DEFAULT 'active' NOT NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS can_view_case BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS can_upload_evidence BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS can_view_documents BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS can_manage_tasks BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS can_approve_reports BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE case_members ADD COLUMN IF NOT EXISTS can_view_medical BOOLEAN DEFAULT FALSE NOT NULL;

CREATE INDEX IF NOT EXISTS ix_case_members_user ON case_members(user_id);
CREATE INDEX IF NOT EXISTS ix_case_members_case ON case_members(case_id);

-- 4. Create case_vehicles table (normalized multi-vehicle collision support)
CREATE TABLE IF NOT EXISTS case_vehicles (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    vehicle_id VARCHAR(64) NULL REFERENCES vehicles(id) ON DELETE SET NULL,
    user_id VARCHAR(64) NULL REFERENCES users(id) ON DELETE SET NULL,
    registration_number VARCHAR(32) NOT NULL,
    vehicle_involvement_type VARCHAR(32) DEFAULT 'primary_subject' NOT NULL, -- 'primary_subject' | 'third_party' | 'witness_vehicle'
    damage_description TEXT NULL,
    damage_severity VARCHAR(64) DEFAULT 'Moderate' NOT NULL,
    make_model VARCHAR(120) NULL,
    color VARCHAR(50) NULL,
    driver_name VARCHAR(120) NULL,
    driver_contact VARCHAR(32) NULL,
    insurance_company VARCHAR(150) NULL,
    insurance_policy_no VARCHAR(100) NULL,
    is_third_party BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_case_vehicles_case ON case_vehicles(case_id);
CREATE INDEX IF NOT EXISTS ix_case_vehicles_vehicle ON case_vehicles(vehicle_id);

-- 5. Create case_involved_people table
CREATE TABLE IF NOT EXISTS case_involved_people (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    case_vehicle_id VARCHAR(64) NULL REFERENCES case_vehicles(id) ON DELETE SET NULL,
    associated_user_id VARCHAR(64) NULL REFERENCES users(id) ON DELETE SET NULL,
    full_name VARCHAR(120) NOT NULL,
    involvement_type VARCHAR(32) DEFAULT 'driver' NOT NULL, -- 'driver' | 'passenger' | 'pedestrian' | 'witness' | 'other'
    relationship_to_coordinator VARCHAR(64) NULL,
    contact_number VARCHAR(32) NULL,
    reported_injury_status VARCHAR(32) DEFAULT 'uninjured' NOT NULL, -- 'uninjured' | 'minor' | 'moderate' | 'severe' | 'critical' | 'fatal'
    injury_description TEXT NULL,
    hospital_name VARCHAR(150) NULL,
    treatment_summary TEXT NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_case_people_case ON case_involved_people(case_id);
CREATE INDEX IF NOT EXISTS ix_case_people_vehicle ON case_involved_people(case_vehicle_id);

-- 6. Create case_evidence table
CREATE TABLE IF NOT EXISTS case_evidence (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    uploaded_by VARCHAR(64) NOT NULL REFERENCES users(id),
    evidence_category VARCHAR(64) DEFAULT 'scene_photo' NOT NULL, -- 'scene_photo' | 'vehicle_damage' | 'dashcam_footage' | 'cctv' | 'skid_marks' | 'road_condition' | 'other'
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    storage_key TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT DEFAULT 0 NOT NULL,
    sha256 VARCHAR(64) NULL,
    evidence_source VARCHAR(64) DEFAULT 'user_upload' NOT NULL, -- 'user_upload' | 'dashcam' | 'traffic_cam' | 'police_provided'
    associated_case_vehicle_id VARCHAR(64) NULL REFERENCES case_vehicles(id) ON DELETE SET NULL,
    associated_person_id VARCHAR(64) NULL REFERENCES case_involved_people(id) ON DELETE SET NULL,
    verification_status VARCHAR(32) DEFAULT 'pending' NOT NULL, -- 'pending' | 'verified' | 'rejected'
    capture_timestamp TIMESTAMPTZ NULL,
    geo_latitude DOUBLE PRECISION NULL,
    geo_longitude DOUBLE PRECISION NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_case_evidence_case ON case_evidence(case_id);
CREATE INDEX IF NOT EXISTS ix_case_evidence_vehicle ON case_evidence(associated_case_vehicle_id);
CREATE INDEX IF NOT EXISTS ix_case_evidence_person ON case_evidence(associated_person_id);

-- 7. Refine tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category VARCHAR(64) DEFAULT 'general' NOT NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL;

CREATE INDEX IF NOT EXISTS ix_tasks_case_status ON tasks(case_id, status);
CREATE INDEX IF NOT EXISTS ix_tasks_assignee ON tasks(assignee_id);

-- 8. Refine timeline_events table
ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS title VARCHAR(200);
ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS related_entity_type VARCHAR(64);
ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS related_entity_id VARCHAR(64);
ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'::jsonb NOT NULL;
ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL;

UPDATE timeline_events SET title = kind WHERE title IS NULL;
CREATE INDEX IF NOT EXISTS ix_timeline_case_at ON timeline_events(case_id, at);
