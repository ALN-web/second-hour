# Second Hour: Database Implementation & Migration Plan

This document outlines the phased migration strategy, object storage abstraction, backward compatibility guarantees, and execution sequencing for the Neon PostgreSQL database schema.

---

## 1. Migration Overview & Sequencing

The schema rollout is partitioned into **5 ordered, atomic migration phases**. Each phase is self-contained, enforces strict referential integrity, and depends strictly on the preceding phases.

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation (Profiles, Addresses, Contacts, Medical)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Vehicles, Central Documents & Version Management   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Cases, Multi-Vehicle, Involved People, Evidence    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Reports & Approvals, Claims, External Submissions  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: AI Assistance, Governance, Consent & Audit Trail   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Migration Breakdown

### Phase 1: Foundation Layer
- **Goal:** Establish core identity, contact hierarchy, physical residences, and medical emergency profiles.
- **Dependencies:** None.
- **Tables Created / Enhanced:**
  1. `users` (Core authentication identity, verified badges, language).
  2. `user_addresses` (Current and permanent Indian residences).
  3. `emergency_contacts` (Prioritized family contacts and notification channels).
  4. `emergency_contact_permissions` (Granular capability switches per contact).
  5. `medical_information` (Quarantined blood group, allergies, conditions, and explicit EMS sharing flags).
- **Invariants Enforced:**
  - Phone and email verification flags reset on credential change.
  - `emergency_contact_permissions` created atomically with every emergency contact.
  - Zero sensitive medical fields exposed to third parties by default.

### Phase 2: Vehicles & Central Documents Management
- **Goal:** Establish centralized document wallet and vehicle profile registry without file duplication.
- **Dependencies:** `users` (Phase 1).
- **Tables Created / Enhanced:**
  6. `vehicles` (Four-wheelers, two-wheelers, commercial vehicles).
  7. `vehicle_photos` (Condition photos with `storage_key`).
  8. `central_documents` (Single source of truth document repository).
  9. `document_versions` (Historical revision archive for renewals/re-uploads).
  10. `vehicle_insurance_policies` (Insurance metadata linked to wallet document).
- **Invariants Enforced:**
  - Files reference `storage_key` in private object storage; no database binary blobs.
  - Sensitive document numbers stored only as masked strings (`XXXX-XXXX-4912`).
  - Central document query views dynamically support `USER`, `VEHICLE`, and `ACCIDENT_CASE` resources.

### Phase 3: Accident Cases, Multi-Vehicle & Evidence
- **Goal:** Support complex accident coordination, multi-vehicle collisions, multi-casualty tracking, and telemetry evidence.
- **Dependencies:** `users` (Phase 1), `vehicles` (Phase 2).
- **Tables Created / Enhanced:**
  11. `cases` (Accident incident master record, PM-RAHAT flags, hospital status, police draft).
  12. `case_status_transitions` (Audit trail for every case status change).
  13. `case_members` (Collaborative workspace permissions).
  14. `case_vehicles` (Normalized support for insured vehicle and third-party involved cars).
  15. `case_involved_people` (Normalized driver, passenger, pedestrian, and witness tracking).
  16. `case_evidence` (Crash scene photos, dashcam footage, audio recordings with geo-telemetry).
  17. `tasks` (Actionable post-accident milestones with statutory timers).
  18. `timeline_events` (Real-time chronological incident activity stream).
- **Invariants Enforced:**
  - Multi-vehicle support eliminates legacy single-vehicle limitations.
  - Multi-victim tracking connects hospital treatment directly to involved persons.
  - Traceable status transitions prevent unauthorized or unrecorded state changes.

### Phase 4: Reports, Claims & External Submissions
- **Goal:** Implement formal PDF dossier generation with human-in-the-loop approvals, insurance claim tracking, and statutory portal integration.
- **Dependencies:** `cases` (Phase 3), `users` (Phase 1).
- **Tables Created / Enhanced:**
  19. `reports` (Case summary and FIR dossier envelopes).
  20. `report_versions` (Versioned PDF files with cryptographic SHA-256 digests).
  21. `insurance_claims` (Motor own-damage, third-party liability, surveyor inspection).
  22. `external_submissions` (PM-RAHAT portal, Traffic Police, and insurer dispatch logs).
- **Invariants Enforced:**
  - AI-generated statements and reports remain in `draft` status until explicitly approved by human coordinator.
  - External submissions require API confirmation before marking status as `acknowledged` or `submitted`.

### Phase 5: AI Assistance, Governance, Consent & Auditing
- **Goal:** Supervised AI assistant interactions, data processing boundaries, statutory consent records, and immutable security audit logs.
- **Dependencies:** `cases` (Phase 3), `users` (Phase 1).
- **Tables Created / Enhanced:**
  23. `conversations` (Context-aware chat threads).
  24. `conversation_messages` (Turn-by-turn prompts, citations, action cards).
  25. `ai_action_logs` (Proposed tool actions requiring user consent before execution).
  26. `user_privacy_preferences` (AI data access boundary switches).
  27. `user_notification_preferences` (Multi-channel subscription toggles).
  28. `consent_records` (Legal consent tracking for data processing and emergency dispatch).
  29. `audit_log` (System-wide immutable security and mutation log).
- **Invariants Enforced:**
  - Second Hour AI cannot inspect medical or vehicle records if corresponding privacy preference is disabled.
  - Mutating tools propose actions to `ai_action_logs` and execute only upon human approval.

---

## 3. Object Storage Abstraction Strategy

To prevent PostgreSQL database bloat and ensure private, secure file handling:

### 3.1 Architecture
```
FastAPI / Services Layer
          │
          ├──> Metadata & Storage Key ──> Neon PostgreSQL (central_documents)
          │
          └──> Binary Stream ──> Object Storage Provider (S3 / GCS / Local Storage)
```

### 3.2 Storage Interface Contract
```python
class ObjectStorageService:
    def upload_file(self, file_bytes: bytes, storage_key: str, mime_type: str) -> str:
        """Upload binary data and return immutable storage URI / key."""
        ...

    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> str:
        """Generate a short-lived pre-signed URL for authenticated access."""
        ...

    def delete_file(self, storage_key: str) -> bool:
        """Permanently delete file from private bucket."""
        ...
```

### 3.3 Storage Key Convention
- Personal Documents: `documents/{user_id}/personal/{doc_id}.pdf`
- Vehicle Documents: `documents/{user_id}/vehicles/{vehicle_id}/{doc_id}.pdf`
- Accident Evidence: `cases/{case_id}/evidence/{evidence_id}.jpg`
- Dossier Reports: `cases/{case_id}/reports/{report_id}_v{version}.pdf`

*Zero-Vendor Lock-in:* In development, the storage adapter maps to local private directory `data/storage/`. In production, the adapter maps to S3/Cloudflare R2/GCS using standard S3 API credentials.

---

## 4. Backward Compatibility & Data Preservation

### 4.1 Preservation of Existing Demo State
- Seeded identity `u_priya` (Priya Sharma) and `u_arjun` (Arjun Sharma) will map directly into the normalized schema.
- Existing seeded case `case_demo` (`SH-2026-0001`) will map cleanly into `cases`, with its vehicle automatically populated in `case_vehicles` and victim populated in `case_involved_people`.
- Existing centralized documents in `central_documents` map directly into the wallet without schema disruption.

### 4.2 SQLite Local Development Fallback
- All models use standard SQLAlchemy Declarative 2.0 constructs.
- In-memory / file-based SQLite fallback remains functional for test suites (`pytest -q tests`) using standard JSON/text serializations.

---

## 5. Verification & Rollback Procedures

### Pre-Deployment Verification Checklist
1. Connect to target Neon branch (`development` first).
2. Execute migration script inside a transaction (`BEGIN ... COMMIT`).
3. Verify table presence and constraints via `information_schema`.
4. Run test seed script (`python -m scripts.seed`).
5. Run full test suite (`pytest -q tests`).
6. Verify live health endpoint (`GET /api/health`).

### Safe Rollback Strategy
- Every migration step is accompanied by an inverse `DOWN` migration (`DROP TABLE IF EXISTS ... CASCADE`).
- Because migrations are phased and transactionally wrapped, any constraint violation triggers an immediate automatic `ROLLBACK`, leaving existing tables unharmed.
