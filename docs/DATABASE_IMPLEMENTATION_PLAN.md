# Second Hour: Database Implementation & Migration Plan

This document outlines the phased migration strategy, object storage adapter implementation, backward compatibility guarantees, and execution sequencing for the Neon PostgreSQL database schema.

---

## 1. Migration Overview & Sequencing

The schema rollout is partitioned into **5 ordered, atomic migration phases**. Each phase is self-contained, transactionally wrapped, and enforces strict referential integrity.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation Layer                                              │
│ - Users (Authentication & Identity compatibility)                      │
│ - User Addresses (Current & Permanent)                                 │
│ - Emergency Contacts & Permissions (Notification vs Workspace Access) │
│ - Medical Information & Medical Access Logs                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Vehicles & Central Documents Management                       │
│ - Vehicles & Vehicle Photos (Object Storage Keys)                      │
│ - Central Documents Wallet & Document Versions                         │
│ - Document Access Logs (View / Download / Share audit)                 │
│ - Historical Vehicle Insurance Policies (Superseded Lineage)           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Accident Cases, Multi-Vehicle & Telemetry Evidence            │
│ - Cases (Master Accident Workspace & PM-RAHAT flags)                  │
│ - Case Status Transitions (Append-only state audit)                    │
│ - Case Members (Resource-scoped collaborative roles)                   │
│ - Case Vehicles (Normalized multi-vehicle support)                     │
│ - Case Involved People (Multi-casualty / witness tracking)             │
│ - Case Evidence (Scene photos, dashcam, audio telemetry)               │
│ - Tasks & Timeline Events                                              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Reports, Approvals, Claims & Statutory Submissions            │
│ - Reports & Versioned PDF Dossiers (Human approval required)           │
│ - Insurance Claims (Own-damage, personal accident, surveyor notes)     │
│ - External Submissions (PM-RAHAT, Traffic Police dispatch logs)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 5: AI Assistance, Governance, Consent & Auditing                 │
│ - Conversations & Messages (Citations & Action Cards)                  │
│ - AI Action Logs (Supervised tool approval logs)                       │
│ - User Privacy & Notification Preferences                              │
│ - Consent Records (Legal and emergency dispatch consent)               │
│ - Append-Only System Audit Log (Redacted of credentials)               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Migration Breakdown

### Phase 1: Foundation Layer
- **Goal:** Establish core identity, physical residences, emergency contact hierarchy, and quarantined medical emergency profiles.
- **Dependencies:** None.
- **Tables (6 Tables):**
  1. `users` (Preserves existing schema: `id`, `name`, `role_label`, `email`, `email_verified`, `phone`, `phone_verified`, `date_of_birth`, `gender`, `profile_photo`, `preferred_language`, `account_status`, timestamps).
  2. `user_addresses` (Current and permanent Indian residences).
  3. `emergency_contacts` (Prioritized family contacts, mobile and alternate numbers).
  4. `emergency_contact_permissions` (Explicit separation of notification dispatch vs. case workspace login).
  5. `medical_information` (Quarantined blood group, allergies, conditions, medications, emergency notes).
  6. `medical_access_logs` (Append-only purpose-specific audit trail for viewing medical information).
- **Invariants Enforced:**
  - Phone and email verification flags reset on credential change.
  - `emergency_contact_permissions` created atomically with every emergency contact.
  - Zero sensitive medical fields exposed to third parties without explicit user consent.

### Phase 2: Vehicles & Central Documents Management
- **Goal:** Establish centralized document wallet and vehicle profile registry without file duplication.
- **Dependencies:** `users` (Phase 1).
- **Tables (6 Tables):**
  7. `vehicles` (Four-wheelers, two-wheelers, commercial vehicles).
  8. `vehicle_photos` (Condition photos with `storage_key`).
  9. `central_documents` (Single source of truth document repository across Personal, Vehicle, and Case views).
  10. `document_versions` (Historical revision archive for renewals/re-uploads with SHA-256).
  11. `document_access_logs` (Append-only audit trail for viewing, downloading, exporting, or sharing documents).
  12. `vehicle_insurance_policies` (Historical motor insurance policies with `is_current_policy` and `superseded_by_policy_id`).
- **Invariants Enforced:**
  - Binary files stored in private object storage; database stores only metadata and `storage_key`.
  - Sensitive document numbers stored only as masked strings (`XXXX-XXXX-4912`).
  - Historical policies are preserved indefinitely rather than deleted or overwritten upon renewal.

### Phase 3: Accident Cases, Multi-Vehicle & Telemetry Evidence
- **Goal:** Support complex accident coordination, multi-vehicle collisions, multi-casualty tracking, and telemetry evidence.
- **Dependencies:** `users` (Phase 1), `vehicles` (Phase 2).
- **Tables (8 Tables):**
  13. `cases` (Accident incident master record, PM-RAHAT flags, hospital status, police draft).
  14. `case_status_transitions` (Append-only audit trail for every case status change).
  15. `case_members` (Collaborative workspace permissions with resource-scoped capabilities).
  16. `case_vehicles` (Normalized support for insured vehicle and third-party involved cars).
  17. `case_involved_people` (Normalized driver, passenger, pedestrian, and witness tracking).
  18. `case_evidence` (Crash scene photos, dashcam footage, audio recordings with geo-telemetry).
  19. `tasks` (Actionable post-accident milestones with statutory timers).
  20. `timeline_events` (Real-time chronological incident activity stream).
- **Invariants Enforced:**
  - Multi-vehicle support eliminates legacy single-vehicle limitations.
  - Multi-victim tracking connects hospital treatment directly to involved persons.
  - Traceable status transitions prevent unauthorized or unrecorded state changes.

### Phase 4: Reports, Claims & Statutory Submissions
- **Goal:** Implement formal PDF dossier generation with human-in-the-loop approvals, insurance claim tracking, and statutory portal integration.
- **Dependencies:** `cases` (Phase 3), `users` (Phase 1).
- **Tables (4 Tables):**
  21. `reports` (Case summary and FIR dossier envelopes; default `status = 'draft'`).
  22. `report_versions` (Versioned PDF files with cryptographic SHA-256 digests in object storage).
  23. `insurance_claims` (Motor own-damage, third-party liability, surveyor inspection).
  24. `external_submissions` (PM-RAHAT portal, Traffic Police, and insurer dispatch logs).
- **Invariants Enforced:**
  - AI-generated statements and reports remain in `draft` status until explicitly approved by human coordinator.
  - External submissions require API confirmation before marking status as `acknowledged` or `submitted`.

### Phase 5: AI Assistance, Governance, Consent & Auditing
- **Goal:** Supervised AI assistant interactions, data processing boundaries, statutory consent records, and immutable security audit logs.
- **Dependencies:** `cases` (Phase 3), `users` (Phase 1).
- **Tables (7 Tables):**
  25. `conversations` (Context-aware chat threads).
  26. `conversation_messages` (Turn-by-turn prompts, citations, action cards).
  27. `ai_action_logs` (Proposed tool actions requiring user consent before execution).
  28. `user_privacy_preferences` (AI data access boundary switches).
  29. `user_notification_preferences` (Multi-channel subscription toggles).
  30. `consent_records` (Legal consent tracking for data processing and emergency dispatch).
  31. `audit_log` (System-wide immutable security and mutation log).
- **Invariants Enforced:**
  - Second Hour AI cannot inspect medical or vehicle records if corresponding privacy preference is disabled.
  - Mutating tools propose actions to `ai_action_logs` and execute only upon human approval.
  - Audit log is strictly append-only and redacted of credentials, tokens, and raw documents.

---

## 3. Storage Architecture: Reusable Storage Adapter

To ensure binary files are completely decoupled from PostgreSQL and avoid durable local disk assumptions in production:

### 3.1 Interface Definition (`app/storage/base.py`)
```python
from typing import Protocol, BinaryIO

class StorageAdapter(Protocol):
    def put_object(self, storage_key: str, data: bytes, mime_type: str) -> str:
        """Store binary data at storage_key and return canonical key."""
        ...

    def get_object(self, storage_key: str) -> bytes:
        """Fetch raw bytes for a stored object."""
        ...

    def get_presigned_download_url(self, storage_key: str, expires_in_seconds: int = 900) -> str:
        """Return temporary, authenticated download URL (15 minutes)."""
        ...

    def delete_object(self, storage_key: str) -> bool:
        """Delete object from storage."""
        ...
```

### 3.2 Dual Environment Implementations
1. **Local Development (`LocalStorageAdapter`):**
   - Rooted at `data/storage/` (outside version control).
   - Generates local authenticated proxy URLs via `/api/storage/{storage_key}` with session token validation.
2. **Cloud Production (`S3CompatibleStorageAdapter`):**
   - Compatible with AWS S3, Cloudflare R2, MinIO, or Google Cloud Storage via standard S3 API.
   - Generates authentic pre-signed S3 download URLs without routing heavy binary traffic through the FastAPI backend process.
   - Encrypted at rest via AES-256 (SSE-S3).

---

## 4. Recommended Phase 1 Migration Scope

When approval is granted to begin execution, **Phase 1 (Foundation)** will be executed as the initial migration:

### Phase 1 Execution Steps:
1. Verify `users` table compatibility with existing database records (`u_priya`, `u_arjun`).
2. Create `user_addresses` table and unique constraint (`user_id`, `address_type`).
3. Create `emergency_contacts` table and index on (`user_id`, `priority`).
4. Create `emergency_contact_permissions` table (1:1 with `emergency_contacts`, separating notification dispatch from workspace access).
5. Create `medical_information` table (quarantined 1:1 with `users`, private by default).
6. Create `medical_access_logs` table (append-only purpose-specific audit trail).
7. Seed default permissions and addresses for existing demo users.
8. Run connectivity and test suite validation (`pytest -q tests`).

---

## 5. Rollback & Verification Procedures

### Pre-Deployment Verification Checklist
1. Connect to target Neon branch (`development` first).
2. Execute migration inside an explicit SQL transaction block:
   ```sql
   BEGIN;
   -- Phase DDL
   COMMIT;
   ```
3. Verify table presence and constraints via `information_schema`.
4. Run connectivity test (`python -m scripts.test_db_connection`).
5. Run test suite (`pytest -q tests`).
6. Verify live health endpoint (`GET /api/health`).

### Safe Rollback Strategy
- Every migration step is accompanied by an inverse `DOWN` migration (`DROP TABLE IF EXISTS ... CASCADE`).
- Any error during `BEGIN ... COMMIT` automatically issues `ROLLBACK`, leaving existing database state completely intact.
