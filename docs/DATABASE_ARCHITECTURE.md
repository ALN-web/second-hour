# Second Hour: Database Architecture Specification
**Database Engine:** Neon Serverless PostgreSQL (PostgreSQL 18+)  
**Document Status:** Final Design Specification (Refined & Approved in Principle)  
**Target Environment:** Development & Production Branches  

---

## 1. Architectural Principles & Security Foundations

### 1.1 Object Storage Separation & Reusable Storage Adapter
- **Zero Binary Blobs in PostgreSQL:** Files (PDFs, crash scene photographs, vehicle registration documents, medical bills, FIR reports) are **never** stored as `BYTEA` or binary blobs in the relational database.
- **Pure Metadata Storage:** PostgreSQL stores metadata, file size in bytes, MIME type, cryptographic SHA-256 digest, and an immutable `storage_key`.
- **Reusable Storage Adapter Contract:**
  ```python
  class StorageAdapter(Protocol):
      def put_object(self, storage_key: str, data: bytes, mime_type: str) -> str:
          """Persist file bytes to private storage and return storage key."""
          ...

      def get_object(self, storage_key: str) -> bytes:
          """Retrieve raw file bytes from private storage."""
          ...

      def get_presigned_download_url(self, storage_key: str, expires_in_seconds: int = 900) -> str:
          """Generate a short-lived (default 15 minutes) authorized download URL."""
          ...

      def delete_object(self, storage_key: str) -> bool:
          """Permanently remove an object from storage."""
          ...
  ```
- **Environment Adaptability:**
  - *Local Development:* `LocalStorageAdapter` stores private assets under `data/storage/` (outside git).
  - *Production Cloud:* `S3CompatibleStorageAdapter` communicates with private, encrypted buckets (AWS S3, Cloudflare R2, Google Cloud Storage, or MinIO) via standard S3 API signatures without application code changes.
  - *Durable Storage Guardrail:* Production environments never rely on local ephemeral disks.

### 1.2 Authentication & User Identity Preservation
- **Preserved Existing Columns:** The existing `users` table schema is preserved without breaking changes. Columns (`id`, `name`, `role_label`, `email`, `email_verified`, `phone`, `phone_verified`, `date_of_birth`, `gender`, `profile_photo`, `preferred_language`, `account_status`, `created_at`, `updated_at`) remain 100% compatible.
- **Identity Agnostic Primary Key:** `id VARCHAR(64) PRIMARY KEY` seamlessly accommodates existing demo credentials (`u_priya`, `u_arjun`) as well as production UUIDs (e.g., `usr_0194f48b-821d-79e4-8025-a74e50d68012` or UUID v4/v7).
- **Referential Integrity:** All dependent child tables reference `users(id)` via `VARCHAR(64)`.

### 1.3 Strict Privacy, Medical Isolation & Access Control
- **Notification Permissions vs. Account Access:** Outbound emergency notification dispatch (SOS alerts, SMS/WhatsApp updates to family) is strictly separated from interactive case workspace login access.
- **Quarantined Medical Data:** `medical_information` is isolated in a 1:1 table. Fields are private by default (`share_with_ems = FALSE`, `share_with_ai = FALSE`).
- **Purpose-Specific Medical Access Logging:** Viewing medical records requires an explicit purpose, audited in `medical_access_logs`.
- **Document Access Auditing:** Viewing, downloading, sharing, or exporting central wallet documents is tracked in `document_access_logs`.
- **National Identifier Privacy:** **Never store raw Aadhaar or PAN numbers.** Only masked display representations (e.g. `XXXX-XXXX-4912`, `DL-*****8491`) are stored for verification badges.

### 1.4 Append-Only Auditability & Security Redaction
- **Append-Only Guarantee:** `audit_log`, `case_status_transitions`, `document_access_logs`, and `medical_access_logs` are strictly append-only. Database triggers or application constraints prohibit `UPDATE` and `DELETE` operations on audit tables.
- **Credential & Secret Redaction Policy:** Audit payloads **never** store passwords, database connection strings, authorization tokens, bearer headers, or raw sensitive file contents. All payloads pass through a redaction filter prior to persistence.

### 1.5 Verified Domain Rules
- **Historical Insurance Records:** Vehicle insurance policies are preserved historically. Uploading a renewal policy marks the previous record as superseded rather than deleting or overwriting it.
- **PM-RAHAT Statutory Alignment:** Aligned with MoRTH Gazette S.O. 2489(E) (4 June 2025) and PIB release (11 March 2026):
  - Maximum ₹1,50,000 cashless trauma stabilization for up to 7 days from the incident.
  - Hospital intimation to Police within 24 hours (extended to 48 hours for life-threatening conditions).
  - Configurable policy parameter lookup rather than rigid hardcoded schema locks.
- **Submission Independence:** External authority submissions (PM-RAHAT, Traffic Police) are tracked in `external_submissions` with independent lifecycle states (`draft`, `queued`, `submitted`, `acknowledged`, `rejected`, `failed`), distinct from internal report approval.

---

## 2. Complete Relational Schema Specification

### Domain 1: Users, Profiles & Emergency Readiness

#### 1. `users`
Existing authentication and identity root entity.
```sql
CREATE TABLE users (
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
CREATE UNIQUE INDEX ix_users_email ON users(email) WHERE email IS NOT NULL AND email != '';
CREATE UNIQUE INDEX ix_users_phone ON users(phone) WHERE phone IS NOT NULL AND phone != '';
```

#### 2. `user_addresses`
Current and permanent residences for emergency logistics and legal jurisdiction.
```sql
CREATE TABLE user_addresses (
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
CREATE INDEX ix_user_addresses_user ON user_addresses(user_id);
```

#### 3. `emergency_contacts`
Designated relatives, guardians, and advocates with prioritized escalation order.
```sql
CREATE TABLE emergency_contacts (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(120) NOT NULL,
    relationship VARCHAR(64) NOT NULL,
    mobile_number VARCHAR(32) NOT NULL,
    alternate_number VARCHAR(32) NULL,
    email VARCHAR(255) NULL,
    priority INTEGER DEFAULT 1 NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    preferred_contact_method VARCHAR(32) DEFAULT 'phone' NOT NULL, -- 'phone' | 'whatsapp' | 'sms'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_emergency_contacts_user_prio ON emergency_contacts(user_id, priority);
```

#### 4. `emergency_contact_permissions`
Fine-grained access controls cleanly separating notification dispatch from account and case access.
```sql
CREATE TABLE emergency_contact_permissions (
    id VARCHAR(64) PRIMARY KEY,
    contact_id VARCHAR(64) NOT NULL UNIQUE REFERENCES emergency_contacts(id) ON DELETE CASCADE,
    -- Outbound Notification Dispatch Permissions (SMS / WhatsApp / SOS)
    can_notify_accident_sos BOOLEAN DEFAULT TRUE NOT NULL,
    can_receive_case_sms BOOLEAN DEFAULT TRUE NOT NULL,
    can_receive_whatsapp_updates BOOLEAN DEFAULT FALSE NOT NULL,
    -- Interactive Account & Workspace Access Permissions
    has_workspace_access BOOLEAN DEFAULT FALSE NOT NULL,
    permitted_case_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
    workspace_role VARCHAR(32) DEFAULT 'viewer' NOT NULL, -- 'viewer' | 'editor'
    can_view_limited_summary_only BOOLEAN DEFAULT TRUE NOT NULL,
    -- Explicit Sensitive Resource Overrides (Strictly FALSE by default)
    can_view_medical BOOLEAN DEFAULT FALSE NOT NULL,
    can_view_documents BOOLEAN DEFAULT FALSE NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_ec_permissions_contact ON emergency_contact_permissions(contact_id);
```

#### 5. `medical_information`
Sensitive personal medical profile quarantined from general application access.
```sql
CREATE TABLE medical_information (
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
CREATE INDEX ix_medical_info_user ON medical_information(user_id);
```

#### 6. `medical_access_logs`
Purpose-specific access audit trail for viewing or sharing quarantined medical information.
```sql
CREATE TABLE medical_access_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actor_id VARCHAR(64) NOT NULL REFERENCES users(id),
    access_purpose VARCHAR(100) NOT NULL, -- 'emergency_ems_triage' | 'hospital_intake' | 'user_self_view' | 'ai_assistant_query'
    authorization_type VARCHAR(64) NOT NULL, -- 'explicit_user_consent' | 'ems_emergency_protocol'
    fields_accessed JSONB NOT NULL, -- e.g. ["blood_group", "allergies"]
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_med_access_user_time ON medical_access_logs(user_id, accessed_at);
```

---

### Domain 2: Vehicles & Central Documents Management

#### 7. `vehicles`
Registered motor vehicles managed by the user.
```sql
CREATE TABLE vehicles (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    registration_number VARCHAR(32) NOT NULL,
    category VARCHAR(64) DEFAULT 'Four Wheeler' NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    variant VARCHAR(100) NULL,
    manufacturing_year INTEGER NULL,
    fuel_type VARCHAR(32) DEFAULT 'Petrol' NOT NULL,
    color VARCHAR(50) NULL,
    chassis_number VARCHAR(64) NULL,
    engine_number VARCHAR(64) NULL,
    vin VARCHAR(64) NULL,
    engine_capacity VARCHAR(32) NULL,
    transmission VARCHAR(32) NULL,
    owner_name VARCHAR(120) NULL,
    ownership_type VARCHAR(64) DEFAULT 'Individual' NOT NULL,
    relationship_to_user VARCHAR(64) NULL,
    main_image_url TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_user_vehicle_reg UNIQUE (user_id, registration_number)
);
CREATE INDEX ix_vehicles_user ON vehicles(user_id);
CREATE INDEX ix_vehicles_reg ON vehicles(registration_number);
```

#### 8. `vehicle_photos`
Photographic records of vehicle condition referencing object storage.
```sql
CREATE TABLE vehicle_photos (
    id VARCHAR(64) PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    photo_category VARCHAR(32) DEFAULT 'main' NOT NULL, -- 'main' | 'front' | 'rear' | 'left' | 'right'
    file_name VARCHAR(255) NOT NULL,
    storage_key TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_vehicle_photos_vehicle ON vehicle_photos(vehicle_id);
```

#### 9. `central_documents`
Central document wallet: single source of truth across Personal, Vehicle, and Case views.
```sql
CREATE TABLE central_documents (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(64) NOT NULL, -- 'rc' | 'insurance' | 'puc' | 'driving_licence' | 'hospital_bill' | 'medical_report' | 'fir' | 'other'
    category VARCHAR(64) NOT NULL,      -- 'personal' | 'driving_licence' | 'vehicle' | 'insurance' | 'medical' | 'accident_case' | 'other'
    file_name VARCHAR(255) NOT NULL,
    storage_key TEXT NOT NULL,          -- Private object storage key
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    sha256 VARCHAR(64) NULL,
    document_number_masked VARCHAR(100) NULL, -- Masked identifier (never unmasked Aadhaar)
    issuing_authority VARCHAR(150) NULL,
    issue_date DATE NULL,
    expiry_date DATE NULL,
    verification_status VARCHAR(32) DEFAULT 'verified' NOT NULL,
    notes TEXT NULL,
    resource_type VARCHAR(32) DEFAULT 'USER' NOT NULL, -- 'USER' | 'VEHICLE' | 'ACCIDENT_CASE'
    resource_id VARCHAR(64) NULL,
    current_version INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_central_docs_user_cat ON central_documents(user_id, category);
CREATE INDEX ix_central_docs_resource ON central_documents(resource_type, resource_id);
CREATE INDEX ix_central_docs_expiry ON central_documents(expiry_date);
```

#### 10. `document_versions`
Cryptographically validated historical revisions for re-uploaded or renewed wallet documents.
```sql
CREATE TABLE document_versions (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES central_documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    storage_key TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    uploaded_by VARCHAR(64) NOT NULL REFERENCES users(id),
    change_summary VARCHAR(255) NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_doc_version UNIQUE (document_id, version_number)
);
CREATE INDEX ix_document_versions_doc ON document_versions(document_id);
```

#### 11. `document_access_logs`
Append-only audit trail for viewing, downloading, exporting, or sharing sensitive documents.
```sql
CREATE TABLE document_access_logs (
    id BIGSERIAL PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES central_documents(id) ON DELETE CASCADE,
    actor_id VARCHAR(64) NOT NULL REFERENCES users(id),
    action VARCHAR(32) NOT NULL, -- 'view_metadata' | 'download_file' | 'presigned_url_generated' | 'shared_with_third_party'
    access_channel VARCHAR(32) NOT NULL, -- 'web_dashboard' | 'mobile_api' | 'mcp_assistant' | 'emergency_dispatch'
    purpose VARCHAR(100) NULL,   -- 'claim_processing' | 'police_submission' | 'user_download'
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_doc_access_doc_time ON document_access_logs(document_id, accessed_at);
CREATE INDEX ix_doc_access_actor_time ON document_access_logs(actor_id, accessed_at);
```

#### 12. `vehicle_insurance_policies`
Motor insurance policies preserving complete historical coverage and renewal lineage.
```sql
CREATE TABLE vehicle_insurance_policies (
    id VARCHAR(64) PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    provider VARCHAR(150) NOT NULL,
    policy_number VARCHAR(100) NOT NULL,
    policy_type VARCHAR(64) DEFAULT 'Comprehensive' NOT NULL,
    start_date DATE NULL,
    expiry_date DATE NULL,
    document_id VARCHAR(64) NULL REFERENCES central_documents(id) ON DELETE SET NULL,
    is_current_policy BOOLEAN DEFAULT TRUE NOT NULL,
    policy_status VARCHAR(32) DEFAULT 'active' NOT NULL, -- 'active' | 'expired' | 'renewed' | 'cancelled'
    superseded_by_policy_id VARCHAR(64) NULL REFERENCES vehicle_insurance_policies(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_vehicle_insurance_vehicle ON vehicle_insurance_policies(vehicle_id);
CREATE INDEX ix_vehicle_insurance_active ON vehicle_insurance_policies(vehicle_id, is_current_policy);
```

---

### Domain 3: Accident Cases, Multi-Party Involvement & Evidence

#### 13. `cases`
Master accident incident workspace coordinating hospital, police, PM-RAHAT, and family actions.
```sql
CREATE TABLE cases (
    id VARCHAR(64) PRIMARY KEY,
    case_number VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(32) DEFAULT 'active' NOT NULL, -- 'active' | 'under_review' | 'resolved' | 'closed'
    incident_at TIMESTAMPTZ NOT NULL,
    approximate_location VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION NULL,
    longitude DOUBLE PRECISION NULL,
    location_landmark VARCHAR(255) NULL,
    accident_description TEXT NULL,
    accident_type VARCHAR(100) DEFAULT 'Two-Vehicle Collision' NOT NULL,
    weather_conditions VARCHAR(100) DEFAULT 'Clear & Dry' NOT NULL,
    injury_severity VARCHAR(32) DEFAULT 'Moderate' NOT NULL,
    injury_description TEXT NULL,
    damage_severity VARCHAR(64) DEFAULT 'Moderate Frontal Damage' NOT NULL,
    damage_description TEXT NULL,
    hospital_name VARCHAR(150) NULL,
    hospital_address VARCHAR(255) NULL,
    hospital_contact VARCHAR(50) NULL,
    treating_doctor VARCHAR(120) NULL,
    admission_at TIMESTAMPTZ NULL,
    hospital_treatment_status VARCHAR(100) DEFAULT 'Admitted - General Ward' NOT NULL,
    life_threatening BOOLEAN DEFAULT FALSE NOT NULL,
    pmrahat_status VARCHAR(50) DEFAULT 'eligible_active' NOT NULL,
    pmrahat_reference VARCHAR(100) NULL,
    pmrahat_stage VARCHAR(100) DEFAULT 'Eligible - Cashless Active' NOT NULL,
    police_auth_status VARCHAR(50) DEFAULT 'not_started' NOT NULL,
    police_auth_updated_at TIMESTAMPTZ NULL,
    police_station VARCHAR(150) NULL,
    police_station_address VARCHAR(255) NULL,
    investigating_officer VARCHAR(120) NULL,
    officer_contact VARCHAR(50) NULL,
    fir_number VARCHAR(100) NULL,
    fir_date TIMESTAMPTZ NULL,
    fir_sections VARCHAR(150) NULL,
    police_stage VARCHAR(100) DEFAULT 'Draft Prepared' NOT NULL,
    police_report_draft TEXT NULL,
    police_draft_status VARCHAR(50) DEFAULT 'draft_pending_review' NOT NULL,
    police_draft_approved_by VARCHAR(64) NULL REFERENCES users(id),
    police_draft_approved_at TIMESTAMPTZ NULL,
    demo_clock_offset_hours DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    created_by VARCHAR(64) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_cases_status ON cases(status);
CREATE INDEX ix_cases_incident_at ON cases(incident_at);
CREATE INDEX ix_cases_created_by ON cases(created_by);
```

#### 14. `case_status_transitions`
Append-only log tracing every state transition of an accident case.
```sql
CREATE TABLE case_status_transitions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    from_status VARCHAR(32) NOT NULL,
    to_status VARCHAR(32) NOT NULL,
    changed_by VARCHAR(64) NOT NULL REFERENCES users(id),
    transition_trigger VARCHAR(64) DEFAULT 'manual_user_action' NOT NULL, -- 'manual_user_action' | 'hospital_intimation' | 'police_fir_filed' | 'claim_settled'
    reason TEXT NULL,
    transitioned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_case_status_trans_case ON case_status_transitions(case_id, transitioned_at);
```

#### 15. `case_members`
Collaborative workspace permissions with strict per-resource capability enforcement.
```sql
CREATE TABLE case_members (
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) DEFAULT 'member' NOT NULL, -- 'coordinator' | 'editor' | 'viewer'
    relationship VARCHAR(64) NULL,
    contact_number VARCHAR(32) NULL,
    can_view_all_documents BOOLEAN DEFAULT FALSE NOT NULL,
    can_upload_documents BOOLEAN DEFAULT TRUE NOT NULL,
    can_manage_tasks BOOLEAN DEFAULT TRUE NOT NULL,
    can_approve_reports BOOLEAN DEFAULT FALSE NOT NULL,
    can_view_medical BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (case_id, user_id)
);
CREATE INDEX ix_case_members_user ON case_members(user_id);
```

#### 16. `case_vehicles`
Normalized multi-vehicle collision support.
```sql
CREATE TABLE case_vehicles (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    vehicle_id VARCHAR(64) NULL REFERENCES vehicles(id) ON DELETE SET NULL,
    registration_number VARCHAR(32) NOT NULL,
    vehicle_role VARCHAR(32) DEFAULT 'primary_insured' NOT NULL, -- 'primary_insured' | 'third_party' | 'other'
    make_model VARCHAR(120) NULL,
    driver_name VARCHAR(120) NULL,
    driver_contact VARCHAR(32) NULL,
    insurance_company VARCHAR(150) NULL,
    insurance_policy_no VARCHAR(100) NULL,
    damage_description TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_case_vehicles_case ON case_vehicles(case_id);
```

#### 17. `case_involved_people`
Normalized tracking for drivers, passengers, pedestrians, and witnesses.
```sql
CREATE TABLE case_involved_people (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    case_vehicle_id VARCHAR(64) NULL REFERENCES case_vehicles(id) ON DELETE SET NULL,
    full_name VARCHAR(120) NOT NULL,
    person_role VARCHAR(32) NOT NULL, -- 'driver' | 'passenger' | 'pedestrian' | 'witness'
    relationship_to_coordinator VARCHAR(64) NULL,
    contact_number VARCHAR(32) NULL,
    injury_severity VARCHAR(32) DEFAULT 'None' NOT NULL, -- 'None' | 'Minor' | 'Moderate' | 'Severe' | 'Fatal'
    hospital_name VARCHAR(150) NULL,
    treatment_summary TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_case_people_case ON case_involved_people(case_id);
```

#### 18. `case_evidence`
Incident scene evidence stored in private object storage with geographic coordinates.
```sql
CREATE TABLE case_evidence (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    uploaded_by VARCHAR(64) NOT NULL REFERENCES users(id),
    evidence_type VARCHAR(32) NOT NULL, -- 'photo_scene' | 'photo_damage' | 'dashcam_video' | 'audio_statement' | 'other'
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    storage_key TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    captured_at TIMESTAMPTZ NULL,
    geo_latitude DOUBLE PRECISION NULL,
    geo_longitude DOUBLE PRECISION NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_case_evidence_case ON case_evidence(case_id);
```

#### 19. `tasks`
Actionable milestones with statutory timer triggers.
```sql
CREATE TABLE tasks (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '' NOT NULL,
    priority VARCHAR(32) DEFAULT 'medium' NOT NULL, -- 'low' | 'medium' | 'high'
    status VARCHAR(32) DEFAULT 'open' NOT NULL,     -- 'open' | 'in_progress' | 'completed' | 'cancelled'
    due_at TIMESTAMPTZ NULL,
    due_source VARCHAR(100) NULL,
    assignee_id VARCHAR(64) NULL REFERENCES users(id) ON DELETE SET NULL,
    created_by VARCHAR(64) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_tasks_case_status ON tasks(case_id, status);
CREATE INDEX ix_tasks_assignee ON tasks(assignee_id);
```

#### 20. `timeline_events`
Chronological incident activity stream.
```sql
CREATE TABLE timeline_events (
    id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    actor_id VARCHAR(64) NULL REFERENCES users(id) ON DELETE SET NULL,
    kind VARCHAR(64) NOT NULL,
    summary TEXT NOT NULL,
    metadata_json JSONB DEFAULT '{}'::jsonb NOT NULL,
    at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_timeline_case_at ON timeline_events(case_id, at);
```

---

### Domain 4: Reports, Claims & Statutory Submissions

#### 21. `reports`
Formal PDF dossiers with mandatory human coordinator approval before finalization.
```sql
CREATE TABLE reports (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    report_type VARCHAR(50) DEFAULT 'case_summary' NOT NULL,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(32) DEFAULT 'draft' NOT NULL, -- 'draft' | 'pending_approval' | 'approved' | 'rejected'
    latest_version INTEGER DEFAULT 1 NOT NULL,
    approved_by VARCHAR(64) NULL REFERENCES users(id),
    approved_at TIMESTAMPTZ NULL,
    created_by VARCHAR(64) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_reports_case_status ON reports(case_id, status);
```

#### 22. `report_versions`
Cryptographically verified PDF revisions archived in private object storage.
```sql
CREATE TABLE report_versions (
    id VARCHAR(64) PRIMARY KEY,
    report_id VARCHAR(64) NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    storage_key TEXT NOT NULL,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    generated_by VARCHAR(64) NOT NULL REFERENCES users(id),
    content_summary TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_report_version UNIQUE (report_id, version_number)
);
CREATE INDEX ix_report_versions_report ON report_versions(report_id);
```

#### 23. `insurance_claims`
Insurance claim tracking covering own-damage, personal accident, and third-party liabilities.
```sql
CREATE TABLE insurance_claims (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    insurance_provider VARCHAR(150) NOT NULL,
    policy_number VARCHAR(100) NOT NULL,
    claim_number VARCHAR(100) NULL,
    claim_type VARCHAR(50) DEFAULT 'motor_own_damage' NOT NULL,
    claim_stage VARCHAR(64) DEFAULT 'Claim Intimated' NOT NULL,
    surveyor_name VARCHAR(120) NULL,
    surveyor_phone VARCHAR(32) NULL,
    surveyor_inspection_at TIMESTAMPTZ NULL,
    estimated_amount NUMERIC(12, 2) NULL,
    approved_amount NUMERIC(12, 2) NULL,
    settlement_status VARCHAR(64) DEFAULT 'In Progress - Cashless Assessment' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_claims_case ON insurance_claims(case_id);
```

#### 24. `external_submissions`
Outbound filings to statutory authorities, kept strictly distinct from internal report approval.
```sql
CREATE TABLE external_submissions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    target_authority VARCHAR(64) NOT NULL, -- 'pm_rahat' | 'traffic_police' | 'insurance_portal' | 'hospital_desk'
    submission_payload_json JSONB NOT NULL,
    status VARCHAR(32) DEFAULT 'draft' NOT NULL, -- 'draft' | 'queued' | 'submitted' | 'acknowledged' | 'rejected' | 'failed'
    external_reference_no VARCHAR(100) NULL,
    submitted_by VARCHAR(64) NOT NULL REFERENCES users(id),
    submitted_at TIMESTAMPTZ NULL,
    acknowledged_at TIMESTAMPTZ NULL,
    response_payload_json JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_ext_sub_case_status ON external_submissions(case_id, status);
```

---

### Domain 5: AI Assistance, Governance & Audit Trail

#### 25. `conversations`
Ask Second Hour AI chat threads linked to users and optional case contexts.
```sql
CREATE TABLE conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_id VARCHAR(64) NULL REFERENCES cases(id) ON DELETE SET NULL,
    title VARCHAR(200) DEFAULT 'New Conversation' NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE NOT NULL,
    context_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_conversations_user ON conversations(user_id, updated_at DESC);
```

#### 26. `conversation_messages`
Chat messages with structured citations, action proposals, and followups.
```sql
CREATE TABLE conversation_messages (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender VARCHAR(32) NOT NULL, -- 'user' | 'assistant'
    content TEXT NOT NULL,
    citations_json JSONB DEFAULT '[]'::jsonb NOT NULL,
    action_cards_json JSONB DEFAULT '[]'::jsonb NOT NULL,
    suggested_followups_json JSONB DEFAULT '[]'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_conv_msg_conv_time ON conversation_messages(conversation_id, created_at);
```

#### 27. `ai_action_logs`
Supervised AI tool execution tracking with explicit human-in-the-loop approval verification.
```sql
CREATE TABLE ai_action_logs (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NULL REFERENCES conversations(id) ON DELETE SET NULL,
    case_id VARCHAR(64) NULL REFERENCES cases(id) ON DELETE CASCADE,
    actor_id VARCHAR(64) NOT NULL REFERENCES users(id),
    tool_name VARCHAR(100) NOT NULL,
    arguments_json JSONB NOT NULL,
    preview_description TEXT NOT NULL,
    requires_approval BOOLEAN DEFAULT TRUE NOT NULL,
    approval_status VARCHAR(32) DEFAULT 'proposed' NOT NULL, -- 'proposed' | 'approved' | 'rejected' | 'auto_read_only'
    approved_by VARCHAR(64) NULL REFERENCES users(id),
    approved_at TIMESTAMPTZ NULL,
    result_json JSONB NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_ai_action_case_status ON ai_action_logs(case_id, approval_status);
```

#### 28. `user_privacy_preferences`
Data access boundary switches governing AI data inclusion.
```sql
CREATE TABLE user_privacy_preferences (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    ai_data_access_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    ai_include_medical BOOLEAN DEFAULT FALSE NOT NULL,
    ai_include_documents BOOLEAN DEFAULT TRUE NOT NULL,
    ai_include_vehicles BOOLEAN DEFAULT TRUE NOT NULL,
    ai_include_cases BOOLEAN DEFAULT TRUE NOT NULL,
    allow_emergency_broadcast BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_privacy_pref_user ON user_privacy_preferences(user_id);
```

#### 29. `user_notification_preferences`
Multi-channel delivery preferences across SMS, WhatsApp, Email, and Push notifications.
```sql
CREATE TABLE user_notification_preferences (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT TRUE NOT NULL,
    sms_notifications BOOLEAN DEFAULT TRUE NOT NULL,
    in_app_notifications BOOLEAN DEFAULT TRUE NOT NULL,
    whatsapp_notifications BOOLEAN DEFAULT FALSE NOT NULL,
    accident_alerts BOOLEAN DEFAULT TRUE NOT NULL,
    case_updates BOOLEAN DEFAULT TRUE NOT NULL,
    document_expiry_reminders BOOLEAN DEFAULT TRUE NOT NULL,
    insurance_renewal_reminders BOOLEAN DEFAULT TRUE NOT NULL,
    pending_task_reminders BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_notif_pref_user ON user_notification_preferences(user_id);
```

#### 30. `consent_records`
Immutable legal consent logs for data processing, emergency dispatch, and PM-RAHAT intake.
```sql
CREATE TABLE consent_records (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(64) NOT NULL, -- 'ai_data_processing' | 'ems_medical_share' | 'emergency_contact_dispatch' | 'pm_rahat_claim_intake'
    granted BOOLEAN NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_consent_user_type ON consent_records(user_id, consent_type);
```

#### 31. `audit_log`
Strictly append-only system-wide security, mutation, and MCP tool execution log.
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(64) NULL REFERENCES cases(id) ON DELETE SET NULL,
    actor_id VARCHAR(64) NULL REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NULL,
    payload_json JSONB DEFAULT '{}'::jsonb NOT NULL, -- Strictly redacted of credentials and raw tokens
    result_summary TEXT NOT NULL,
    approval_state VARCHAR(64) DEFAULT 'standard' NOT NULL,
    at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_audit_case_time ON audit_log(case_id, at);
CREATE INDEX ix_audit_actor_time ON audit_log(actor_id, at);
```
