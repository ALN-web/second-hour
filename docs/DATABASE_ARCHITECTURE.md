# Second Hour: Database Architecture Specification
**Database Engine:** Neon Serverless PostgreSQL (PostgreSQL 18+)  
**Document Status:** Final Design Proposal (Pending Implementation Approval)  
**Target Environment:** Development & Production Branches  

---

## 1. Architectural Principles & Standards

### 1.1 Object Storage Separation
- **No Binary Columns in PostgreSQL:** Files (PDFs, crash scene photos, vehicle RC copies, medical bills) are **never** stored as `BYTEA` or binary blobs in the relational database.
- **Reference by Storage Key:** The database stores metadata, file size, MIME type, cryptographic SHA-256 digest, and an immutable `storage_key` pointing to private cloud object storage (e.g. S3-compatible or local private media volume in development).
- **Access Control:** File downloads and uploads are mediated exclusively via backend authentication or short-lived pre-signed URLs.

### 1.2 Identifier Conventions
- **Primary Keys:** Prefixed UUID / alphanumeric identifiers (`u_`, `case_`, `veh_`, `cdoc_`, `rpt_`, `act_`, `cmsg_`) to ensure type safety, unambiguous logging, and complete cross-environment predictability without sequence collisions.
- **Foreign Keys:** Explicit referential integrity with strict cascading rules:
  - User-owned dependent records (`user_addresses`, `medical_information`, `emergency_contacts`, `vehicles`) use `ON DELETE CASCADE`.
  - Referential references (`case_vehicles.vehicle_id`, `central_documents.resource_id`) use `ON DELETE SET NULL` to preserve historical post-accident audit trails.

### 1.3 Timestamps & Timezones
- **Universal UTC:** All timestamp columns use `TIMESTAMPTZ` (SQLAlchemy `DateTime(timezone=True)`) with server-side default `CURRENT_TIMESTAMP`.
- **Soft Deletion:** Sensitive resources such as Central Documents implement `deleted_at TIMESTAMPTZ NULL` to support recovery and statutory motor-accident evidence retention.

### 1.4 PII & Data Privacy Protections
- **No Full Aadhaar Numbers:** Highly sensitive national identifiers (Aadhaar, PAN) are **never** stored unmasked. Only masked display tokens (e.g., `XXXX-XXXX-4912`, `DL-*****8491`) are stored for verification badges.
- **Quarantined Medical Data:** `medical_information` is isolated in a 1-to-1 table with explicit boolean gates (`share_with_ems`, `share_with_ai`) defaulting to `FALSE`.
- **Granular Emergency Contact Permissions:** Emergency contacts do not inherit case or document access. Each contact has a dedicated row in `emergency_contact_permissions` defining explicit capabilities.

---

## 2. Complete Relational Schema Specification

### Domain 1: Users, Profiles & Emergency Readiness

#### 1. `users`
Central user entity representing accident victims, family coordinators, or authorized members.
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
    profile_photo_url TEXT NULL,
    preferred_language VARCHAR(50) DEFAULT 'English' NOT NULL,
    account_status VARCHAR(32) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE UNIQUE INDEX ix_users_email ON users(email) WHERE email IS NOT NULL AND email != '';
CREATE UNIQUE INDEX ix_users_phone ON users(phone) WHERE phone IS NOT NULL AND phone != '';
```

#### 2. `user_addresses`
Physical and permanent residences for emergency logistics and legal jurisdiction.
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
Designated relatives, guardians, and advocates with prioritized notification hierarchy.
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
Fine-grained access control boundaries enforced per emergency contact.
```sql
CREATE TABLE emergency_contact_permissions (
    id VARCHAR(64) PRIMARY KEY,
    contact_id VARCHAR(64) NOT NULL UNIQUE REFERENCES emergency_contacts(id) ON DELETE CASCADE,
    can_notify_accident BOOLEAN DEFAULT TRUE NOT NULL,
    can_receive_case_updates BOOLEAN DEFAULT TRUE NOT NULL,
    can_access_case BOOLEAN DEFAULT FALSE NOT NULL,
    permitted_case_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
    can_view_limited_case_info BOOLEAN DEFAULT TRUE NOT NULL,
    can_view_medical BOOLEAN DEFAULT FALSE NOT NULL,
    can_view_documents BOOLEAN DEFAULT FALSE NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_ec_permissions_contact ON emergency_contact_permissions(contact_id);
```

#### 5. `medical_information`
Sensitive medical profile used for emergency triage and PM-RAHAT hospital intake.
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

---

### Domain 2: Vehicles & Central Documents Management

#### 6. `vehicles`
Registered vehicles managed by users for instant crash assistance and document association.
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

#### 7. `vehicle_photos`
Vehicle condition photos for insurance underwriting and post-accident damage baseline.
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

#### 8. `central_documents`
Unified document wallet serving as the single source of truth for personal, vehicle, and accident documents.
```sql
CREATE TABLE central_documents (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(64) NOT NULL, -- 'rc' | 'insurance' | 'puc' | 'driving_licence' | 'hospital_bill' | 'medical_report' | 'fir' | 'other'
    category VARCHAR(64) NOT NULL,      -- 'personal' | 'driving_licence' | 'vehicle' | 'insurance' | 'medical' | 'accident_case' | 'other'
    file_name VARCHAR(255) NOT NULL,
    storage_key TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER DEFAULT 0 NOT NULL,
    sha256 VARCHAR(64) NULL,
    document_number_masked VARCHAR(100) NULL,
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

#### 9. `document_versions`
Audit log of document revisions, re-uploads, and renewal replacements.
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

#### 10. `vehicle_insurance_policies`
Active motor insurance records linking directly to verified central documents.
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_vehicle_insurance_vehicle ON vehicle_insurance_policies(vehicle_id);
```

---

### Domain 3: Accident Cases, Multi-Party Involvement & Evidence

#### 11. `cases`
Central accident incident management record coordinating hospital, police, PM-RAHAT, and family actions.
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

#### 12. `case_status_transitions`
Immutable audit log recording every transition of case status with author and rationale.
```sql
CREATE TABLE case_status_transitions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    from_status VARCHAR(32) NOT NULL,
    to_status VARCHAR(32) NOT NULL,
    changed_by VARCHAR(64) NOT NULL REFERENCES users(id),
    reason TEXT NULL,
    transitioned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_case_status_trans_case ON case_status_transitions(case_id, transitioned_at);
```

#### 13. `case_members`
Collaborative workspace permissions designating coordinators, editors, and family viewers.
```sql
CREATE TABLE case_members (
    case_id VARCHAR(64) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) DEFAULT 'member' NOT NULL, -- 'coordinator' | 'editor' | 'viewer'
    relationship VARCHAR(64) NULL,
    contact_number VARCHAR(32) NULL,
    permissions_summary VARCHAR(255) NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (case_id, user_id)
);
CREATE INDEX ix_case_members_user ON case_members(user_id);
```

#### 14. `case_vehicles`
Multi-vehicle tracking: captures user vehicle and third-party involved vehicles.
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

#### 15. `case_involved_people`
Multi-victim and witness tracking: associates individuals with vehicles, triage status, and care.
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

#### 16. `case_evidence`
Photographic, video, and audio records collected from the scene with geographic telemetry.
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

#### 17. `tasks`
Actionable checklist items with deadlines, assigned family members, and statutory timers.
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

#### 18. `timeline_events`
Chronological activity timeline displaying hospital admission, police draft, and insurer intimations.
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

### Domain 4: Reports, Claims & External Submissions

#### 19. `reports`
Generated formal dossier packages (PDFs) with human-in-the-loop approval workflow.
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

#### 20. `report_versions`
Immutable file versions of generated reports stored in object storage.
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

#### 21. `insurance_claims`
Insurance claim tracking covering own damage, third-party liability, and surveyor inspections.
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

#### 22. `external_submissions`
Outbound integration tracking for statutory portals (PM-RAHAT, Traffic Police, Insurer Desk).
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

#### 23. `conversations`
Ask Second Hour AI interactive session sessions linked to users and optional case contexts.
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

#### 24. `conversation_messages`
Turn-by-turn chat messages with structured citations, action proposals, and followups.
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

#### 25. `ai_action_logs`
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

#### 26. `user_privacy_preferences`
Data access boundaries defining whether AI and external services may inspect sensitive records.
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

#### 27. `user_notification_preferences`
Multi-channel delivery preferences across SMS, WhatsApp, Email, and Push alerts.
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

#### 28. `consent_records`
Immutable audit log recording user consent grants and revocations for legal and regulatory compliance.
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

#### 29. `audit_log`
Comprehensive immutable system-wide security, mutation, and MCP tool execution log.
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(64) NULL REFERENCES cases(id) ON DELETE SET NULL,
    actor_id VARCHAR(64) NULL REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NULL,
    payload_json JSONB DEFAULT '{}'::jsonb NOT NULL,
    result_summary TEXT NOT NULL,
    approval_state VARCHAR(64) DEFAULT 'standard' NOT NULL,
    at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX ix_audit_case_time ON audit_log(case_id, at);
CREATE INDEX ix_audit_actor_time ON audit_log(actor_id, at);
```
