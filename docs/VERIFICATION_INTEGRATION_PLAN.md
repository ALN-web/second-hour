# Second Hour — Identity & Document Verification Integration Plan
**Document Version:** 1.0.0  
**Phase:** Core Identity & Trust Layer  
**Date:** November 2026  
**Status:** Approved Architecture Plan  

---

## 1. Executive Summary

Second Hour assists accident victims and their families in critical post-accident hours. Trust, speed, and accuracy are paramount. This document outlines the architectural plan for a centralized, privacy-first **Identity & Document Verification System**.

The verification system establishes cryptographic and institutional verification across three core pillars:
1. **User Identity & Contact Verification:** Email and mobile number OTP verification, plus government identity verification.
2. **Vehicle Verification:** Verification of vehicle registration certificates (RC) via authorized VAHAN/Parivahan gateways.
3. **Document & Insurance Verification:** Verification of central documents, driving licences, and vehicle insurance policies via DigiLocker and IRDAI/IIB-backed services.

---

## 2. Guiding Principles & Compliance

1. **Explicit Consent First (DPDP Act, 2023):**  
   External providers are never contacted without explicit, purpose-specific, timestamped user consent recorded in the `consent_records` audit table.
2. **Never Auto-Verify Uploads:**  
   User-uploaded documents and self-declared vehicle records receive `unverified` status by default. Only cryptographically verified proofs or provider-confirmed responses transition status to `verified`.
3. **No PII/Credential Storage:**  
   Passwords, API keys, raw OTPs, and 12-digit Aadhaar numbers are never stored in the database. OTPs are hashed using salted SHA-256; Aadhaar numbers are strictly masked (showing only the last 4 digits).
4. **Resilience & Emergency Non-Blocking:**  
   Verification failures or pending checks **never block emergency assistance, accident case creation, or SOS notifications**. The system degrades gracefully to self-declared emergency mode.
5. **Full Auditability:**  
   Every verification attempt, provider reference ID, retry, failure code, and timestamp is stored immutably in `verification_records` and mirrored in the central `audit_log`.

---

## 3. Authorized Provider Ecosystem & Integration Analysis

### 3.1. Government & Authorized Verification Channels in India

| Domain | Institutional Authority | Authorized Access Mode | Recommended Gateway / Partner | Cost per Check | SLA / Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Identity & DL** | DigiLocker (NeGD / MeitY) | OAuth 2.0 PKCE / API Setu / GSP | Setu (Pine Labs) / Surepass / Signzy | ₹1.50 – ₹3.00 | ~1.5s – 3.0s |
| **Vehicle RC** | MoRTH / NIC (VAHAN 4.0) | Authorized API Setu / Aggregator | Surepass / Signzy / Karza (Perfios) | ₹1.00 – ₹2.50 | ~600ms – 1.2s |
| **Insurance** | IIB / IRDAI / GIC | Insurer Registry & Aggregators | Surepass / Perfios / Direct Insurer API | ₹1.50 – ₹3.50 | ~800ms – 1.8s |
| **Mobile SMS** | TRAI DLT Gateways | SMPP / REST API (DLT Entity ID) | Fast2SMS / MSG91 / Twilio India | ₹0.15 – ₹0.25 | ~2s – 5s |
| **Email OTP** | SMTP / RFC 5322 | REST API / TLS SMTP | SendGrid / AWS SES / Postmark | ₹0.005 – ₹0.02 | ~1s – 3s |

---

### 3.2. DigiLocker Integration Deep-Dive

#### Overview
DigiLocker is the Government of India's flagship digital document wallet platform under MeitY. It allows citizens to share authentic, digitally signed electronic documents directly from issuing authorities (UIDAI, MoRTH, State Transport Departments).

#### Integration Mechanics
1. **Consent Redirection / Modal:** Second Hour displays an explicit consent screen detailing the purpose (Accident Case Verification & Identity Assurance) and requested doc types (`DRVLC` for Driving Licence, `RGCERT` for Vehicle RC).
2. **OAuth 2.0 Authorization Code Grant:**
   - Redirect to DigiLocker Auth: `GET https://digilocker.meripehchaan.gov.in/public/oauth2/1/authorize`
   - Client ID, Response Type (`code`), Redirect URI, State (CSRF token), Scope.
3. **Token Exchange:**
   - Exchange code for access token via secure server-to-server call.
4. **Document Retrieval:**
   - Query issued documents: `GET /public/oauth2/1/xml/eaadhaar`, `GET /public/oauth2/1/xml/in.gov.transport-DRVLC`.
   - Validate XML digital signature against the DigiLocker public certificate.
   - Extract and mask sensitive identity attributes (e.g. `DL-1420110012345` -> `DL-14********345`).

#### Development & Testing Strategy
In development/demo mode, an authorized Mock Provider (`DigiLockerMockAdapter`) replicates the full OAuth exchange and XML payload structure without making external network calls, returning pre-verified demo credentials for `u_priya` and realistic edge cases (expired licence, name mismatch, rate limit).

---

### 3.3. VAHAN / Parivahan Integration Deep-Dive

#### Overview
VAHAN is the centralized vehicle registry managed by the National Informatics Centre (NIC) under MoRTH.

#### Integration Mechanics
1. **Input Parameters:** Vehicle Registration Number (e.g., `DL 01 AB 1234`), optional Chassis Number (last 5 digits for high-assurance matching).
2. **Query:** Server sends request to authorized VAHAN gateway.
3. **Returned Payload Attributes:**
   - Vehicle class (e.g., `Motor Car (LMV)`), Manufacturer, Model, Fuel Type, Registration Date.
   - Owner Name (partially masked by the gateway, e.g., `P**** S*****`).
   - Fitness Expiry Date, Road Tax Validity, PUC Certificate Expiry Date.
   - Insurance Policy Number, Insurer Name, and Policy Expiry Date.
   - Financer / Hypothecation details.
4. **Matching Logic:**
   - Compare entered registration number, chassis/engine matching.
   - If verified, update `vehicles.verification_status = 'verified'` and store provider transaction ID in `vehicles.verification_reference_id`.

---

### 3.4. Insurance Policy Verification Deep-Dive

#### Overview
Ensures third-party and comprehensive motor insurance policies are active at the time of an incident.

#### Integration Mechanics
- Queries the Insurance Information Bureau (IIB) database or authorized insurer gateway using Registration Number + Policy Number.
- Confirms cover start date, expiry date, active claim status, and zero-depreciation endorsements.
- Updates `vehicle_insurance_policies.verification_status` and alerts user if insurance is within 30 days of expiry.

---

## 4. Database Schema Design (Phase 6)

### 4.1. New Table: `verification_records`
Stores immutable records of all verification attempts across all entity types.

```sql
CREATE TABLE verification_records (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type VARCHAR(32) NOT NULL, -- 'USER_EMAIL', 'USER_PHONE', 'IDENTITY_DOCUMENT', 'VEHICLE_RC', 'VEHICLE_INSURANCE'
    entity_id VARCHAR(64) NOT NULL,   -- user_id, document_id, vehicle_id, policy_id
    provider VARCHAR(32) NOT NULL,    -- 'DIGILOCKER', 'VAHAN_PARIVAHAN', 'IIB_INSURANCE', 'SMS_OTP', 'EMAIL_OTP'
    status VARCHAR(20) NOT NULL,      -- 'PENDING', 'VERIFIED', 'FAILED', 'REVOKED'
    verification_type VARCHAR(32) NOT NULL, -- 'OTP', 'API_MATCH', 'OAUTH_DIGILOCKER'
    verification_reference_id VARCHAR(128), -- external transaction/request ID
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    verified_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    consent_record_id VARCHAR(64) REFERENCES consent_records(id),
    raw_response_hash VARCHAR(64),    -- SHA-256 hash of response for tamper-evidence without storing raw PII
    verified_metadata JSONB DEFAULT '{}'::jsonb, -- Masked details: {"masked_id": "DL-14****345", "match_confidence": 0.98}
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_verification_records_entity ON verification_records(entity_type, entity_id);
CREATE INDEX ix_verification_records_user ON verification_records(user_id);
CREATE INDEX ix_verification_records_ref ON verification_records(verification_reference_id);
```

### 4.2. New Table: `otp_verifications`
Manages secure OTP lifecycles without storing plaintext codes.

```sql
CREATE TABLE otp_verifications (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(16) NOT NULL,     -- 'email', 'phone'
    target VARCHAR(128) NOT NULL,     -- email or phone number
    otp_hash VARCHAR(64) NOT NULL,    -- Salted SHA-256 hash of the 6-digit code
    salt VARCHAR(32) NOT NULL,        -- Cryptographic random salt
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_otp_verifications_user_channel ON otp_verifications(user_id, channel, is_used);
```

### 4.3. Schema Adjustments to Existing Tables
1. **`vehicles` Table:**
   - Add `verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'`
   - Add `verification_provider VARCHAR(32)`
   - Add `verified_at TIMESTAMP WITH TIME ZONE`
   - Add `verification_reference_id VARCHAR(128)`
2. **`central_documents` Table:**
   - Alter default `verification_status` from `'verified'` to `'unverified'` (Requirement #8).
   - Add `verification_provider VARCHAR(32)`
   - Add `verified_at TIMESTAMP WITH TIME ZONE`
   - Add `verification_reference_id VARCHAR(128)`
   - Add `verification_failure_reason TEXT`

---

## 5. Security & Privacy Guarantees

1. **OTP Cryptographic Design:**
   - Generated with `secrets.SystemRandom().randint(100000, 999999)`.
   - `salt = secrets.token_hex(16)`
   - `otp_hash = hashlib.sha256((salt + otp).encode('utf-8')).hexdigest()`
   - Validated in constant-time using `hmac.compare_digest`.
   - 10-minute expiry; maximum 5 invalid attempts before auto-invalidation; 60-second resend cooldown.
2. **Data Minimization:**
   - Identity documents only store masked numbers (e.g., `XXXX-XXXX-1234`).
   - Raw verification provider payloads are hashed with SHA-256; only sanitized summary metadata is retained.
3. **Audit Trail:**
   - All verification requests, successful validations, and failed attempts write an entry to both `verification_records` and `audit_log`.

---

## 6. Implementation Stages & Roadmap

- **Stage 1:** Architectural inspection, integration research, and implementation plan.
- **Stage 2:** Email & Mobile verification with secure keyed HMAC-SHA256 OTP hashing, rate-limiting, and profile synchronization.
- **Stage 3:** Central document verification framework, schema updates, unverified default status, and retry workflows.
- **Stage 4:** Pluggable Provider Adapters (DigiLocker, VAHAN, IIB Insurance) with sandbox simulation and consent checks.
- **Stage 5:** Frontend integration across My Profile, My Vehicles, and Documents with verification badges, modals, and retry triggers.
- **Stage 6 (Step 2 Hardening):** Strict provider trust levels (`MOCK`, `SANDBOX`, `PRODUCTION`), centralized status transitions, vehicle registration invalidation, and fail-closed credential checks.

---

## 7. Strict Provider Trust Levels & Execution Modes

To prevent development or mock adapters from conferring authentic `verified` status on production documents, vehicles, or insurance policies, Second Hour standardizes three explicit execution modes:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Provider Trust Levels                                │
├───────────────────┬─────────────────────────────────────────────────────────────┤
│ Mode              │ Permitted Status Transitions & Guarantees                   │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ MOCK              │ - MUST NEVER grant 'verified' status.                       │
│ (Default)         │ - Status always remains 'pending'.                          │
│                   │ - Provider prefixed with 'MOCK_' (e.g. MOCK_VAHAN_PARIVAHAN)│
│                   │ - Simulated reference ID prefixed with 'MOCK-SIMULATED-'    │
│                   │ - verified_at is always NULL.                               │
│                   │ - Safe for offline development and local UI testing.        │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ SANDBOX           │ - Explicitly distinguishable from production verification.   │
│                   │ - Status remains 'pending'.                                 │
│                   │ - Provider prefixed with 'SANDBOX_'                         │
│                   │ - Reference ID prefixed with 'SANDBOX-'                     │
│                   │ - verified_at is always NULL.                               │
│                   │ - Cannot mark real user documents/vehicles verified.        │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ PRODUCTION        │ - Requires live, authorized institutional credentials.      │
│                   │ - Only mode permitted to grant 'verified' status.           │
│                   │ - Missing credentials FAIL CLOSED immediately with error.   │
│                   │ - Timeouts, malformed responses, errors NEVER grant status. │
│                   │ - Persists real provider reference and UTC timestamp.       │
└───────────────────┴─────────────────────────────────────────────────────────────┘
```

### Why User Uploads & Mock Responses Are Not Proof of Authenticity
1. **Self-Uploaded Documents:** Any user can upload an arbitrary PDF or image file claiming to be a Government DL or RC. Self-uploaded files default to `unverified` and can only transition after authorized institutional verification.
2. **Mock & Sandbox Responses:** In local development or automated test environments, mock adapters return synthetic JSON structures for predictable UI demonstration. These synthetic responses represent simulated workflows, NOT institutional validation. Conferring `verified` status based on mock data would represent a critical security vulnerability.

---

## 8. Centralized Verification Status Transitions

All status changes on `CentralDocument`, `Vehicle`, and `VehicleInsurancePolicy` MUST pass through `transition_verification_status()`. Individual provider adapters and direct API endpoints are strictly forbidden from modifying verification columns directly.

### Central Transition Invariants:
1. Direct updates via `PATCH /api/documents/{id}` or `PUT /api/vehicles/{id}` cannot modify `verification_status`.
2. `transition_verification_status` enforces trust mode checks before any database commit.
3. Every verification attempt (whether mock, sandbox, production success, or failure) writes an immutable record to `verification_records` and logs to `audit_log`.

---

## 9. Vehicle Registration Change Invalidation Rules

When a vehicle's registration number is modified in `update_vehicle`:

1. **Normalized String Comparison:** Registration numbers are normalized using `normalize_registration_number()` (stripping all whitespace, hyphens, and punctuation, and uppercasing).
2. **Genuinely Changed Registration:**
   - If `new_normalized != old_normalized`:
     - Existing `verification_status` is immediately reset to `'unverified'`.
     - `verification_provider`, `verification_reference_id`, and `verified_at` are cleared to `NULL`.
     - `verification_failure_reason` is set indicating that the registration number changed and re-verification is required.
     - An audit log entry (`vehicle_verification_invalidated`) is recorded.
3. **Harmless Formatting Difference:**
   - If `new_normalized == old_normalized` (e.g., `"ka 01 mj 4012"` vs `"KA-01-MJ-4012"`):
     - The formatted string is updated.
     - `verification_status`, `verification_provider`, `verification_reference_id`, and `verified_at` are **strictly preserved**.

---

## 10. Provider Status Inventory

| Provider Adapter | Target Entity | Auth / Verification Mechanism | Current Implementation Status |
| :--- | :--- | :--- | :--- |
| **DigiLockerAdapter** | Driving Licence / Identity Doc | OAuth 2.0 PKCE / Issued XML | Stubbed/Mock (production requires client credentials) |
| **VahanAdapter** | Vehicle RC | VAHAN 4.0 API Match | Stubbed/Mock (production requires VAHAN API key) |
| **InsuranceAdapter**| Vehicle Insurance Policy | IIB / Insurer Registry API | Stubbed/Mock (production requires IIB API key) |
| **OtpVerification** | User Email & Phone | Keyed HMAC-SHA256 OTP | **Live Implementation** (fail-closed demo mode, HMAC-secured) |

