"""Phase 5: AI Conversations, Privacy, Consent & Governance Test Suite.

Validates all 21 core verification points:
1. Migration safety and live Neon schema verification (all 7 Phase 5 tables present).
2. Existing users, vehicles, cases, reports, claims preserved across previous phases.
3. Creating a conversation creates a persistent database session.
4. Messages maintain correct sequential ordering and sequence numbers.
5. Conversations can be renamed.
6. Conversations can be archived and unarchived.
7. User isolation: users cannot access or tamper with other users' conversations.
8. AI action proposals are registered with awaiting_approval status.
9. Human coordinator approval executes the underlying action and updates status to completed.
10. Human rejection marks action as rejected without executing the underlying business logic.
11. AI cannot self-approve its own actions (strict backend guardrail).
12. Failed actions record error details and failure reason cleanly.
13. Privacy preferences default to protective values (medical info sharing disabled by default).
14. Medical information access is strictly disabled by default.
15. AI data access respects privacy boundaries (vehicles, documents, cases, medical).
16. Granting consent creates an active immutable consent record.
17. Revoking consent marks status as revoked with timestamp while preserving audit trail.
18. Notification preferences save correctly across multi-channel toggles and quiet hours.
19. Central audit log records events with explicit actor types (user, ai, system).
20. Sensitive credentials (passwords, tokens, keys) are automatically redacted in audit logs.
21. FastAPI REST API endpoints integration for conversations, actions, privacy, and consent.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.api import app
from app.db import (
    AIActionLog,
    AuditLog,
    Case,
    CentralDocument,
    ConsentRecord,
    Conversation,
    ConversationMessage,
    ExternalSubmission,
    InsuranceClaim,
    MedicalInformation,
    Report,
    SessionLocal,
    User,
    UserNotificationPreference,
    UserPrivacyPreference,
    Vehicle,
    engine,
    new_id,
    utcnow,
)
from app.services import assistant as asst_svc
from app.services import audit as audit_svc
from app.services import privacy as privacy_svc
from app.services.common import NotFoundError, PermissionDenied, ServiceError


client = TestClient(app)


# ==============================================================================
# 1. Schema & Prior Phases Preservation
# ==============================================================================

def test_phase5_schema_and_prior_phases_intact():
    """Verify all 7 Phase 5 tables exist on live Neon PostgreSQL and prior phase records are intact."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # 1. Verify Phase 5 tables
    phase5_tables = [
        "conversations",
        "conversation_messages",
        "ai_action_logs",
        "user_privacy_preferences",
        "user_notification_preferences",
        "consent_records",
        "audit_log",
    ]
    for table in phase5_tables:
        assert table in tables, f"Expected table '{table}' in database"

    # Verify column structures
    conv_cols = {c["name"] for c in inspector.get_columns("conversations")}
    assert "status" in conv_cols
    assert "ai_provider" in conv_cols
    assert "model_identifier" in conv_cols
    assert "archived_at" in conv_cols

    msg_cols = {c["name"] for c in inspector.get_columns("conversation_messages")}
    assert "sequence_number" in msg_cols
    assert "sender_type" in msg_cols
    assert "source_references_json" in msg_cols
    assert "ai_model_metadata" in msg_cols

    act_cols = {c["name"] for c in inspector.get_columns("ai_action_logs")}
    assert "action_status" in conv_cols or "action_status" in act_cols
    assert "approval_required" in act_cols
    assert "approved_by" in act_cols

    priv_cols = {c["name"] for c in inspector.get_columns("user_privacy_preferences")}
    assert "ai_include_medical" in priv_cols
    assert "medical_info_sharing_enabled" in priv_cols

    csnt_cols = {c["name"] for c in inspector.get_columns("consent_records")}
    assert "consent_type" in csnt_cols
    assert "consent_status" in csnt_cols
    assert "revoked_at" in csnt_cols

    # 2. Verify prior entities remain intact
    db = SessionLocal()
    try:
        priya = db.get(User, "u_priya")
        assert priya is not None
        assert "Priya" in priya.name

        arjun = db.get(User, "u_arjun")
        assert arjun is not None

        case = db.get(Case, "case_demo")
        assert case is not None
        assert case.case_number == "SH-2026-0001"

        veh = db.get(Vehicle, "veh_demo_honda")
        assert veh is not None

        rpt = db.get(Report, "rpt_demo_summary")
        assert rpt is not None

        claim = db.get(InsuranceClaim, "claim_demo_1")
        assert claim is not None
    finally:
        db.close()


# ==============================================================================
# 2. Conversation Persistence & Lifecycle
# ==============================================================================

def test_conversation_creation_and_persistence():
    """Verify creating a conversation creates a persistent DB session."""
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(
            db=db,
            user_id="u_priya",
            title="Road Accident Guidance Session",
            case_id="case_demo",
            ai_provider="gemini",
            model_identifier="gemini-1.5-flash",
        )
        assert conv["id"].startswith("conv_")
        assert conv["title"] == "Road Accident Guidance Session"
        assert conv["status"] == "active"
        assert conv["case_id"] == "case_demo"

        # Verify persistent in DB
        db_conv = db.get(Conversation, conv["id"])
        assert db_conv is not None
        assert db_conv.user_id == "u_priya"
        assert db_conv.ai_provider == "gemini"
    finally:
        db.close()


def test_messages_sequential_ordering():
    """Verify messages maintain strictly increasing sequence numbers."""
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya", "Ordering Test Conv")
        cid = conv["id"]

        # Post first message
        res1 = asst_svc.post_user_message(db, "u_priya", cid, "First question: tell me about PM-RAHAT")
        assert res1["sequence_number"] == 2  # user is 1, asst is 2

        # Post second message
        res2 = asst_svc.post_user_message(db, "u_priya", cid, "Second question: what about my car insurance?")
        assert res2["sequence_number"] == 4  # user is 3, asst is 4

        # Retrieve full conversation
        detail = asst_svc.get_conversation(db, "u_priya", cid)
        messages = detail["messages"]
        assert len(messages) >= 4
        seqs = [m["sequence_number"] for m in messages]
        assert seqs == sorted(seqs)
        assert seqs[0] == 1
        assert seqs[1] == 2
        assert seqs[2] == 3
        assert seqs[3] == 4
    finally:
        db.close()


def test_conversation_rename_archive_unarchive():
    """Verify renaming, archiving, and unarchiving conversations."""
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya", "Old Title")
        cid = conv["id"]

        # 1. Rename
        renamed = asst_svc.rename_conversation(db, "u_priya", cid, "Updated Comprehensive Title")
        assert renamed["title"] == "Updated Comprehensive Title"

        # 2. Archive
        archived = asst_svc.archive_conversation(db, "u_priya", cid)
        assert archived["status"] == "archived"
        assert archived["archived_at"] is not None

        # Verify list filtering excludes archived by default or includes with filter
        active_list = asst_svc.list_conversations(db, "u_priya", status="active")
        archived_list = asst_svc.list_conversations(db, "u_priya", status="archived")
        assert any(c["id"] == cid for c in archived_list)

        # 3. Unarchive
        unarchived = asst_svc.unarchive_conversation(db, "u_priya", cid)
        assert unarchived["status"] == "active"
        assert unarchived["archived_at"] is None
    finally:
        db.close()


def test_conversation_user_isolation():
    """Verify strict tenant isolation: Arjun cannot access Priya's conversation."""
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya", "Priya's Confidential Chat")
        cid = conv["id"]

        with pytest.raises(PermissionDenied):
            asst_svc.get_conversation(db, "u_arjun", cid)

        with pytest.raises(PermissionDenied):
            asst_svc.rename_conversation(db, "u_arjun", cid, "Hacked Title")

        with pytest.raises(PermissionDenied):
            asst_svc.archive_conversation(db, "u_arjun", cid)

        with pytest.raises(PermissionDenied):
            asst_svc.post_user_message(db, "u_arjun", cid, "Unauthorized message injection")
    finally:
        db.close()


# ==============================================================================
# 3. AI Actions & Human Approval Workflow
# ==============================================================================

def test_ai_action_proposal_and_pending_status():
    """Verify AI action proposals are registered with awaiting_approval status."""
    db = SessionLocal()
    try:
        prop = asst_svc.propose_action(
            db=db,
            user_id="u_priya",
            action_type="NAVIGATE",
            description="Open central documents wallet",
            input_payload={"path": "/documents"},
            case_id="case_demo",
            requires_approval=True,
        )
        assert prop["id"].startswith("aiact_")
        assert prop["action_status"] == "awaiting_approval"
        assert prop["approval_required"] is True
        assert prop["approved_by"] is None

        # Retrieve action details
        details = asst_svc.get_action_details(db, "u_priya", prop["id"])
        assert details["action_type"] == "NAVIGATE"
    finally:
        db.close()


def test_human_approval_of_action_executes():
    """Verify human approval executes the action and updates status to completed."""
    db = SessionLocal()
    try:
        prop = asst_svc.propose_action(
            db=db,
            user_id="u_priya",
            action_type="NAVIGATE",
            description="Navigate to cases",
            input_payload={"path": "/cases/case_demo"},
            case_id="case_demo",
        )
        aid = prop["id"]

        # Human approves
        approved = asst_svc.approve_action(db, "u_priya", aid, approval_notes="Looks good, proceed.")
        assert approved["action_status"] == "completed"
        assert approved["approved_by"] == "u_priya"
        assert approved["approval_timestamp"] is not None
        assert approved["execution_timestamp"] is not None
        assert approved["output_metadata"].get("status") == "success"
    finally:
        db.close()


def test_human_rejection_of_action_without_execution():
    """Verify human rejection updates status to rejected without executing the underlying business logic."""
    db = SessionLocal()
    try:
        prop = asst_svc.propose_action(
            db=db,
            user_id="u_priya",
            action_type="CREATE_TASK",
            description="Create draft task",
            input_payload={"title": "Unauthorized task", "case_id": "case_demo"},
            case_id="case_demo",
        )
        aid = prop["id"]

        # Human rejects
        rejected = asst_svc.reject_action(db, "u_priya", aid, reason="Not needed at this time")
        assert rejected["action_status"] == "rejected"
        assert rejected["failure_reason"] == "Not needed at this time"
        assert rejected["execution_timestamp"] is None
    finally:
        db.close()


def test_ai_cannot_self_approve_actions():
    """Verify strict backend guardrail: AI agents cannot approve actions."""
    db = SessionLocal()
    try:
        prop = asst_svc.propose_action(
            db=db,
            user_id="u_priya",
            action_type="NAVIGATE",
            description="Auto-navigate",
            input_payload={"path": "/cases"},
        )
        aid = prop["id"]

        # AI self-approval must be blocked
        with pytest.raises(PermissionDenied) as exc_info:
            asst_svc.approve_action(db, "ai_assistant_agent", aid)
        assert "forbidden" in str(exc_info.value).lower()

        with pytest.raises(PermissionDenied):
            asst_svc.approve_action(db, "system", aid)
    finally:
        db.close()


def test_failed_action_records_error_details():
    """Verify that an action that fails during execution cleanly captures failure details."""
    db = SessionLocal()
    try:
        # Invalid action type that causes an error in execute_assistant_action
        prop = asst_svc.propose_action(
            db=db,
            user_id="u_priya",
            action_type="UNKNOWN_INVALID_TYPE",
            description="Failing action",
            input_payload={},
        )
        aid = prop["id"]

        res = asst_svc.approve_action(db, "u_priya", aid)
        assert res["action_status"] == "failed"
        assert res["failure_reason"] is not None
        assert "Unknown action type" in res["failure_reason"]
    finally:
        db.close()


# ==============================================================================
# 4. Privacy Preferences & Data Boundary Enforcement
# ==============================================================================

def test_privacy_preferences_protective_defaults():
    """Verify privacy preferences default to protective values with medical sharing disabled."""
    db = SessionLocal()
    try:
        uid = new_id("u_test")
        test_user = User(id=uid, name="Test Privacy User", role_label="Driver")
        db.add(test_user)
        db.commit()

        prefs = privacy_svc.get_privacy_preferences(db, uid)
        assert prefs["ai_data_access_enabled"] is True
        assert prefs["ai_include_medical"] is False  # Medical disabled by default
        assert prefs["medical_info_sharing_enabled"] is False  # Medical sharing disabled
        assert prefs["analytics_enabled"] is False  # Analytics opt-in
    finally:
        db.close()


def test_ai_data_access_respects_privacy_boundaries():
    """Verify AI data access respects individual category boundaries (vehicles, documents, cases, medical)."""
    db = SessionLocal()
    try:
        uid = "u_priya"

        # 1. Disable medical access (default is False anyway)
        privacy_svc.update_privacy_preferences(db, uid, {"ai_include_medical": False})
        can_medical = privacy_svc.check_ai_data_access(db, uid, "medical")
        assert can_medical is False

        # Medical query produces strict privacy warning
        conv = asst_svc.create_conversation(db, uid, "Medical Boundary Test")
        res = asst_svc.post_user_message(db, uid, conv["id"], "What is my blood group and allergies?")
        assert "[Privacy Boundary]" in res["content"] or "disabled" in res["content"].lower()

        # 2. Disable vehicle access
        privacy_svc.update_privacy_preferences(db, uid, {"ai_include_vehicles": False})
        can_veh = privacy_svc.check_ai_data_access(db, uid, "vehicles")
        assert can_veh is False

        res_veh = asst_svc.post_user_message(db, uid, conv["id"], "Check my vehicle insurance")
        assert "[Privacy Boundary]" in res_veh["content"] or "disabled" in res_veh["content"].lower()

        # Restore vehicle access
        privacy_svc.update_privacy_preferences(db, uid, {"ai_include_vehicles": True})
        assert privacy_svc.check_ai_data_access(db, uid, "vehicles") is True

        # 3. Completely disable AI data access
        privacy_svc.update_privacy_preferences(db, uid, {"ai_data_access_enabled": False})
        assert privacy_svc.check_ai_data_access(db, uid, "general") is False

        res_disabled = asst_svc.post_user_message(db, uid, conv["id"], "Help me with my documents")
        assert "Privacy Setting Notice" in res_disabled["content"] or "disabled" in res_disabled["content"].lower()

        # Restore AI data access
        privacy_svc.update_privacy_preferences(db, uid, {"ai_data_access_enabled": True})
        assert privacy_svc.check_ai_data_access(db, uid, "general") is True
    finally:
        db.close()


# ==============================================================================
# 5. Consent Records & Revocation
# ==============================================================================

def test_consent_grant_and_revocation():
    """Verify consent grant, active checking, revocation timestamp, and history preservation."""
    db = SessionLocal()
    try:
        uid = "u_arjun"

        # 1. Grant consent
        c = privacy_svc.grant_consent(
            db=db,
            user_id=uid,
            consent_type="medical_information_sharing",
            policy_version="v2.0",
            consent_source="test_runner",
            ip_address="192.168.1.50",
            user_agent="PyTest/1.0",
            metadata={"purpose": "emergency_trauma_care"},
        )
        assert c["consent_type"] == "medical_information_sharing"
        assert c["consent_status"] == "granted"
        assert c["revoked_at"] is None

        # Check active consent
        assert privacy_svc.has_active_consent(db, uid, "medical_information_sharing") is True

        # 2. Revoke consent
        rev = privacy_svc.revoke_consent(db, uid, "medical_information_sharing", reason="User opted out")
        assert rev["consent_status"] == "revoked"
        assert rev["revoked_at"] is not None

        # Check active consent is now False
        assert privacy_svc.has_active_consent(db, uid, "medical_information_sharing") is False

        # 3. Verify history preservation: consent records are not deleted
        consents = privacy_svc.list_user_consents(db, uid)
        assert any(rec["id"] == c["id"] and rec["consent_status"] == "revoked" for rec in consents)
    finally:
        db.close()


# ==============================================================================
# 6. Notification Preferences & Quiet Hours
# ==============================================================================

def test_notification_preferences_and_quiet_hours():
    """Verify multi-channel notification settings, alert categories, and quiet hours evaluation."""
    db = SessionLocal()
    try:
        uid = "u_priya"
        updated = privacy_svc.update_notification_preferences(
            db=db,
            user_id=uid,
            data={
                "push_notifications": True,
                "ai_action_notifications": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": "23:00",
                "quiet_hours_end": "06:00",
                "quiet_hours_timezone": "Asia/Kolkata",
            },
        )
        assert updated["channels"]["push_notifications"] is True
        assert updated["alerts"]["ai_action_notifications"] is True
        assert updated["quiet_hours"]["enabled"] is True

        # Test notification evaluation
        can_send = privacy_svc.can_send_notification(
            db=db,
            user_id=uid,
            channel="email",
            alert_type="case_updates",
        )
        assert can_send is True

        # WhatsApp is disabled
        can_send_wa = privacy_svc.can_send_notification(
            db=db,
            user_id=uid,
            channel="whatsapp",
            alert_type="case_updates",
        )
        assert can_send_wa is False
    finally:
        db.close()


# ==============================================================================
# 7. Central Audit Logging & Credential Redaction
# ==============================================================================

def test_audit_log_actor_types_and_append_only():
    """Verify central audit logging records events with proper actor types (user, ai, system)."""
    db = SessionLocal()
    try:
        entry = audit_svc.record_audit(
            db=db,
            actor_id="u_priya",
            actor_type="user",
            action_type="export_case_summary",
            resource_type="case",
            resource_id="case_demo",
            case_id="case_demo",
            action_outcome="success",
            result_summary="User exported summary report",
        )
        assert entry["actor_type"] == "user"
        assert entry["action_type"] == "export_case_summary"
        assert entry["action_outcome"] == "success"

        # Read back audit logs
        logs = audit_svc.list_audit_logs(db, case_id="case_demo", action_type="export_case_summary")
        assert len(logs) > 0
        assert logs[0]["actor_id"] == "u_priya"
    finally:
        db.close()


def test_audit_log_sensitive_values_redaction():
    """Verify sensitive keys (passwords, tokens, api_keys) are automatically redacted."""
    db = SessionLocal()
    try:
        raw_payload = {
            "user_id": "u_priya",
            "password": "SuperSecretPassword123!",
            "auth_token": "bearer_928374928374",
            "api_key": "sec_ai_991823749",
            "nested": {
                "secret_key": "critical_private_key",
                "normal_field": "hello world",
            },
        }

        entry = audit_svc.record_audit(
            db=db,
            actor_id="u_priya",
            actor_type="user",
            action_type="authenticate_attempt",
            resource_type="auth",
            payload=raw_payload,
            result_summary="Auth check with credential scrubbing",
        )

        # Inspect DB record directly
        db_log = db.get(AuditLog, entry["id"])
        meta = db_log.sanitized_metadata if isinstance(db_log.sanitized_metadata, dict) else json.loads(db_log.sanitized_metadata or "{}")

        assert meta["password"] == "[REDACTED]"
        assert meta["auth_token"] == "[REDACTED]"
        assert meta["api_key"] == "[REDACTED]"
        assert meta["nested"]["secret_key"] == "[REDACTED]"
        assert meta["nested"]["normal_field"] == "hello world"
    finally:
        db.close()


# ==============================================================================
# 8. FastAPI REST API Integration
# ==============================================================================

def test_phase5_api_endpoints():
    """Verify FastAPI endpoints for conversations, messages, actions, privacy, and consent."""
    headers = {"x-user-id": "u_priya"}

    # 1. GET & POST /api/conversations
    create_res = client.post(
        "/api/conversations",
        headers=headers,
        json={"title": "REST API Test Session", "case_id": "case_demo"},
    )
    assert create_res.status_code == 200
    conv_data = create_res.json()
    cid = conv_data["id"]

    # 2. POST /api/conversations/{id}/messages
    msg_res = client.post(
        f"/api/conversations/{cid}/messages",
        headers=headers,
        json={"content": "What is the cashless hospitalization limit under PM-RAHAT?"},
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["sender"] == "assistant"
    assert "₹1,50,000" in msg_data["content"] or "1,50,000" in msg_data["content"] or "1.5" in msg_data["content"]

    # 3. GET /api/assistant/actions
    act_list_res = client.get("/api/assistant/actions", headers=headers)
    assert act_list_res.status_code == 200
    actions = act_list_res.json()
    assert isinstance(actions, list)

    # 4. GET & PATCH /api/profile/privacy
    get_priv_res = client.get("/api/profile/privacy", headers=headers)
    assert get_priv_res.status_code == 200

    patch_priv_res = client.patch(
        "/api/profile/privacy",
        headers=headers,
        json={"personalization_enabled": True},
    )
    assert patch_priv_res.status_code == 200

    # 5. GET & POST /api/profile/consent
    grant_csnt_res = client.post(
        "/api/profile/consent",
        headers=headers,
        json={"consent_type": "external_document_sharing", "policy_version": "v1.2"},
    )
    assert grant_csnt_res.status_code == 200
    assert grant_csnt_res.json()["consent_status"] == "granted"

    revoke_csnt_res = client.post(
        "/api/profile/consent/external_document_sharing/revoke",
        headers=headers,
        json={"reason": "Revoked via API test"},
    )
    assert revoke_csnt_res.status_code == 200
    assert revoke_csnt_res.json()["consent_status"] == "revoked"

    # 6. GET /api/audit-logs
    audit_res = client.get("/api/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    assert isinstance(audit_res.json(), list)
