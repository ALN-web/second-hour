"""Test suite for Phase 1: User Foundation Layer on Neon PostgreSQL.

Verifies:
1. Demo users preservation and identity integrity (u_priya, u_arjun).
2. Profile summary, completion score, and personal info management.
3. User addresses CRUD and unique constraint per (user_id, address_type).
4. Emergency contacts CRUD, primary toggling, priority reordering.
5. 1:1 EmergencyContactPermission model with outbound notification vs interactive workspace separation.
6. Optional medical information privacy defaults and quarantined management.
7. Purpose-specific medical access logging and append-only audit trail.
8. Unauthorized medical access prevention and permission enforcement.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import (
    EmergencyContact,
    EmergencyContactPermission,
    MedicalAccessLog,
    MedicalInformation,
    SessionLocal,
    User,
    UserAddress,
)
from app.services import profile as profile_svc
from app.services.common import PermissionDenied, ServiceError


def test_phase1_demo_users_preserved():
    """Verify demo users u_priya and u_arjun exist with correct identities."""
    db = SessionLocal()
    try:
        priya = db.get(User, "u_priya")
        assert priya is not None, "Demo user u_priya must exist in database"
        assert "Priya" in priya.name
        assert priya.email_verified is True
        assert priya.phone_verified is True

        arjun = db.get(User, "u_arjun")
        assert arjun is not None, "Demo user u_arjun must exist in database"
        assert "Arjun" in arjun.name
        assert arjun.email_verified is True
    finally:
        db.close()


def test_phase1_profile_retrieval_and_update():
    """Verify profile retrieval and personal info update workflow."""
    db = SessionLocal()
    try:
        prof = profile_svc.get_profile(db, "u_priya")
        assert prof["user_id"] == "u_priya"
        assert prof["stats"]["completion_percentage"] >= 75

        # Update preferred language and role
        updated = profile_svc.update_personal_info(
            db,
            "u_priya",
            {
                "name": "Priya Sharma",
                "preferred_language": "Hindi",
                "date_of_birth": "1992-06-14",
                "gender": "female",
            },
        )
        assert updated["preferred_language"] == "Hindi"

        # Restore language
        profile_svc.update_personal_info(
            db,
            "u_priya",
            {
                "name": "Priya Sharma",
                "preferred_language": "English",
                "date_of_birth": "1992-06-14",
                "gender": "female",
            },
        )
    finally:
        db.close()


def test_phase1_user_addresses_crud_and_unique_constraint():
    """Verify address management and (user_id, address_type) uniqueness."""
    db = SessionLocal()
    try:
        addresses = profile_svc.get_addresses(db, "u_priya")
        assert "current" in addresses

        # Update current address
        updated = profile_svc.save_address(
            db,
            "u_priya",
            "current",
            {
                "address_line_1": "#505, Outer Ring Road",
                "address_line_2": "Near Bellandur",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pin_code": "560103",
                "country": "India",
                "is_same_as_current": False,
            },
        )
        assert updated["current"]["address_line_1"] == "#505, Outer Ring Road"

        # Verify unique constraint at database level
        duplicate_addr = UserAddress(
            user_id="u_priya",
            address_type="current",
            address_line_1="Duplicate Test",
            city="Bengaluru",
            state="Karnataka",
            pin_code="560103",
        )
        db.add(duplicate_addr)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_phase1_emergency_contacts_and_reordering():
    """Verify emergency contacts CRUD, primary toggling, and priority reordering."""
    db = SessionLocal()
    try:
        # Add new contact
        new_c = profile_svc.add_emergency_contact(
            db,
            "u_priya",
            {
                "full_name": "Kavita Sharma",
                "relationship": "Relative",
                "mobile_number": "+91 98450 77665",
                "email": "kavita@example.com",
                "preferred_contact_method": "whatsapp",
            },
        )
        cid = new_c["id"]
        assert new_c["full_name"] == "Kavita Sharma"

        # Set as primary
        profile_svc.update_emergency_contact(db, "u_priya", cid, {"is_primary": True})
        contacts = profile_svc.list_emergency_contacts(db, "u_priya")
        primary = next((c for c in contacts if c["id"] == cid), None)
        assert primary is not None and primary["is_primary"] is True

        # Reorder priorities
        all_ids = [c["id"] for c in contacts]
        reversed_ids = list(reversed(all_ids))
        reordered = profile_svc.reorder_emergency_contacts(db, "u_priya", reversed_ids)
        assert reordered[0]["id"] == reversed_ids[0]
        assert reordered[0]["priority"] == 1

        # Delete added contact
        profile_svc.delete_emergency_contact(db, "u_priya", cid)

        # Restore ec_arjun as primary
        profile_svc.update_emergency_contact(db, "u_priya", "ec_arjun", {"is_primary": True})
    finally:
        db.close()


def test_phase1_emergency_contact_permissions_separation():
    """Verify 1:1 EmergencyContactPermission model separates outbound SOS/SMS from workspace access."""
    db = SessionLocal()
    try:
        contacts = profile_svc.list_emergency_contacts(db, "u_priya")
        arjun_contact = next(c for c in contacts if c["id"] == "ec_arjun")
        assert "permissions" in arjun_contact

        # Update permissions with refined fields
        updated_perms = profile_svc.update_emergency_contact_permissions(
            db,
            user_id="u_priya",
            contact_id="ec_arjun",
            can_notify_accident_sos=True,
            can_receive_case_sms=True,
            can_receive_whatsapp_updates=True,
            has_workspace_access=True,
            permitted_case_ids=["case_demo"],
            workspace_role="editor",
            can_view_limited_summary_only=False,
            can_view_medical=False,
            can_view_documents=True,
        )

        assert updated_perms["can_notify_accident_sos"] is True
        assert updated_perms["can_receive_whatsapp_updates"] is True
        assert updated_perms["has_workspace_access"] is True
        assert updated_perms["workspace_role"] == "editor"
        assert updated_perms["can_view_medical"] is False
        assert updated_perms["can_view_documents"] is True

        # Test backward-compatible alias keys
        assert updated_perms["can_notify_accident"] is True
        assert updated_perms["can_access_case"] is True
    finally:
        db.close()


def test_phase1_medical_info_quarantine_and_defaults():
    """Verify medical information privacy defaults and updating."""
    db = SessionLocal()
    try:
        med = profile_svc.get_medical_info(db, user_id="u_priya", actor_id="u_priya")
        assert med["user_id"] == "u_priya"
        assert med["blood_group"] == "O+"
        assert "Penicillin" in (med["allergies"] or "")

        # Update medical info
        updated = profile_svc.update_medical_info(
            db,
            "u_priya",
            {
                "blood_group": "O+",
                "allergies": "Penicillin (Mild hives)",
                "medical_conditions": "None",
                "medications": "None ongoing",
                "emergency_notes": "Primary emergency contact is Arjun Sharma",
                "share_with_ems": True,
                "share_with_ai": False,
            },
        )
        assert updated["share_with_ems"] is True
        assert updated["share_with_ai"] is False
    finally:
        db.close()


def test_phase1_medical_access_logging():
    """Verify that viewing quarantined medical info creates an append-only audit log."""
    db = SessionLocal()
    try:
        # Get count of logs before
        logs_before = profile_svc.list_medical_access_logs(db, "u_priya")
        count_before = len(logs_before)

        # Access medical info as Priya
        profile_svc.get_medical_info(
            db,
            user_id="u_priya",
            actor_id="u_priya",
            purpose="user_self_view",
            ip_address="127.0.0.1",
            user_agent="pytest/test_phase1",
        )

        # Verify log entry was created
        logs_after = profile_svc.list_medical_access_logs(db, "u_priya")
        assert len(logs_after) == count_before + 1
        latest = logs_after[0]
        assert latest["user_id"] == "u_priya"
        assert latest["actor_id"] == "u_priya"
        assert latest["access_purpose"] == "user_self_view"
        assert latest["authorization_type"] == "self_authorized"
    finally:
        db.close()


def test_phase1_medical_unauthorized_access_blocked():
    """Verify that an unauthorized actor cannot query medical information."""
    db = SessionLocal()
    try:
        # u_outsider has no permissions and is not a case member with medical access
        with pytest.raises(PermissionDenied):
            profile_svc.get_medical_info(
                db,
                user_id="u_priya",
                actor_id="u_outsider",
                purpose="unauthorized_attempt",
            )
    finally:
        db.close()
