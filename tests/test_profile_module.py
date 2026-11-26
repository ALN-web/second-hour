"""Test suite for Second Hour My Profile Module.

Tests:
1. Profile overview, completion score, and stats.
2. Personal info update and security reset of verification status when email/phone changes.
3. OTP request and confirmation workflow.
4. Emergency contacts CRUD, primary contact designation, and priority reordering.
5. Emergency contact granular permissions management.
6. Optional medical information updates and clearing.
7. Address management (current, permanent, same as current).
8. Identity documents reference and number masking.
9. Privacy preferences & notification preferences.
10. Password change validation and legal retention guardrails on account deletion.
11. User data isolation.
"""
from __future__ import annotations

import os
import tempfile
import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="sh_prof_test_")
os.environ["ANTHROPIC_API_KEY"] = ""

from app.db import SessionLocal, User
from app.services import profile as profile_svc
from app.services.common import ServiceError
from scripts.seed import seed


@pytest.fixture(autouse=True)
def setup_db():
    seed()
    yield


def test_get_profile_and_completion():
    db = SessionLocal()
    try:
        prof = profile_svc.get_profile(db, "u_priya")
        assert prof["user_id"] == "u_priya"
        assert "Priya" in prof["name"]
        assert prof["email_verified"] is True
        assert prof["phone_verified"] is True
        assert prof["stats"]["completion_percentage"] >= 75
        assert prof["stats"]["emergency_contacts_count"] >= 1
    finally:
        db.close()


def test_update_personal_info_and_verification_reset():
    db = SessionLocal()
    try:
        # Update name and DOB
        prof = profile_svc.update_personal_info(db, "u_priya", {
            "name": "Priya Sharma Updated",
            "gender": "female",
            "date_of_birth": "1992-06-14",
            "preferred_language": "Hindi",
        })
        assert prof["name"] == "Priya Sharma Updated"
        assert prof["preferred_language"] == "Hindi"

        # Changing phone must reset phone_verified
        prof2 = profile_svc.update_personal_info(db, "u_priya", {
            "phone": "+91 98450 99999",
        })
        assert prof2["phone"] == "+91 98450 99999"
        assert prof2["phone_verified"] is False
    finally:
        db.close()


def test_otp_verification_workflow():
    db = SessionLocal()
    try:
        # Request OTP
        req = profile_svc.request_verification_otp(db, "u_priya", "phone")
        assert req["status"] == "otp_sent"
        assert "123456" in req["message"]

        # Confirm with wrong OTP
        with pytest.raises(ServiceError):
            profile_svc.confirm_verification_otp(db, "u_priya", "phone", "000000")

        # Confirm with valid OTP
        conf = profile_svc.confirm_verification_otp(db, "u_priya", "phone", "123456")
        assert conf["status"] == "verified"
        assert conf["profile"]["phone_verified"] is True
    finally:
        db.close()


def test_emergency_contacts_crud_and_primary():
    db = SessionLocal()
    try:
        # List initial seeded contacts
        contacts = profile_svc.list_emergency_contacts(db, "u_priya")
        assert len(contacts) >= 2
        primary = next(c for c in contacts if c["is_primary"])
        assert primary["full_name"] == "Arjun Sharma"

        # Add new contact
        new_c = profile_svc.add_emergency_contact(db, "u_priya", {
            "full_name": "Kavita Rao",
            "relationship": "Friend",
            "mobile_number": "+91 98765 43210",
            "is_primary": True,  # should demote Arjun as primary
        })
        assert new_c["full_name"] == "Kavita Rao"

        updated_contacts = profile_svc.list_emergency_contacts(db, "u_priya")
        new_primary = next(c for c in updated_contacts if c["is_primary"])
        assert new_primary["full_name"] == "Kavita Rao"

        # Reorder contacts
        c_ids = [c["id"] for c in updated_contacts]
        reordered = profile_svc.reorder_emergency_contacts(db, "u_priya", list(reversed(c_ids)))
        assert reordered[0]["id"] == c_ids[-1]

        # Delete contact
        del_res = profile_svc.delete_emergency_contact(db, "u_priya", new_c["id"])
        assert del_res is True
    finally:
        db.close()


def test_emergency_contact_permissions():
    db = SessionLocal()
    try:
        contacts = profile_svc.list_emergency_contacts(db, "u_priya")
        cid = contacts[0]["id"]

        # Update granular permissions
        res = profile_svc.update_emergency_contact(db, "u_priya", cid, {
            "permissions": {
                "can_notify_accident": True,
                "can_receive_case_updates": True,
                "can_access_case": True,
                "permitted_case_ids": ["case_demo"],
                "can_view_limited_case_info": True,
                "can_view_medical": False,
                "can_view_documents": True,
            }
        })
        assert res["status"] == "success"

        updated = profile_svc.list_emergency_contacts(db, "u_priya")
        target = next(c for c in updated if c["id"] == cid)
        assert target["permissions"]["can_access_case"] is True
        assert "case_demo" in target["permissions"]["permitted_case_ids"]
        assert target["permissions"]["can_view_medical"] is False
    finally:
        db.close()


def test_medical_info_optional_and_clear():
    db = SessionLocal()
    try:
        med = profile_svc.get_medical_info(db, "u_priya")
        assert "optional" in med["disclaimer"].lower()
        assert med["blood_group"] == "O+"

        # Update
        updated = profile_svc.update_medical_info(db, "u_priya", {
            "allergies": "Sulfa drugs, Dust",
            "emergency_notes": "Allergic to sulfa drugs; carry prescription in wallet",
            "share_with_ems": True,
            "share_with_ai": True,
        })
        assert "Sulfa" in updated["allergies"]
        assert updated["share_with_ai"] is True

        # Clear
        cleared = profile_svc.clear_medical_info(db, "u_priya")
        assert cleared["blood_group"] is None
        assert cleared["allergies"] is None
    finally:
        db.close()


def test_address_management():
    db = SessionLocal()
    try:
        addrs = profile_svc.get_addresses(db, "u_priya")
        assert addrs["current"] is not None
        assert addrs["current"]["city"] == "Bengaluru"

        # Update current address
        profile_svc.save_address(db, "u_priya", "current", {
            "address_line_1": "#101, Prestige Palms",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560066",
        })

        # Permanent address same as current
        perm_res = profile_svc.save_address(db, "u_priya", "permanent", {
            "is_same_as_current": True,
        })
        assert perm_res["permanent"]["is_same_as_current"] is True
        assert perm_res["permanent"]["pin_code"] == "560066"
    finally:
        db.close()


def test_identity_documents_masking():
    db = SessionLocal()
    try:
        docs = profile_svc.get_identity_documents(db, "u_priya")
        assert len(docs) >= 1
        for d in docs:
            # Check masking
            num = d["masked_number"]
            assert "XXXX" in num or "****" in num or num == "Not Provided"
    finally:
        db.close()


def test_privacy_and_notification_preferences():
    db = SessionLocal()
    try:
        # Privacy preferences
        priv = profile_svc.get_privacy_preferences(db, "u_priya")
        assert priv["ai_data_access_enabled"] is True

        up_priv = profile_svc.update_privacy_preferences(db, "u_priya", {
            "ai_include_medical": True,
        })
        assert up_priv["ai_include_medical"] is True

        # Notification preferences
        notif = profile_svc.get_notification_preferences(db, "u_priya")
        assert notif["channels"]["email_notifications"] is True

        up_notif = profile_svc.update_notification_preferences(db, "u_priya", {
            "channels": {"whatsapp_notifications": True},
        })
        assert up_notif["channels"]["whatsapp_notifications"] is True
    finally:
        db.close()


def test_account_deletion_statutory_retention():
    db = SessionLocal()
    try:
        # Wrong confirmation
        with pytest.raises(ServiceError):
            profile_svc.request_account_deletion(db, "u_priya", "NO")

        # User with active accident case cannot have records wiped silently
        res = profile_svc.request_account_deletion(db, "u_priya", "DELETE")
        assert res["status"] == "retention_lock"
        assert res["active_cases_count"] >= 1
        assert "statutory" in res["message"].lower()

        # User without cases can be deactivated
        outsider_res = profile_svc.request_account_deletion(db, "u_outsider", "DELETE")
        assert outsider_res["status"] == "deactivated"
    finally:
        db.close()


def test_user_data_isolation():
    db = SessionLocal()
    try:
        priya_contacts = profile_svc.list_emergency_contacts(db, "u_priya")
        priya_cid = priya_contacts[0]["id"]

        # Outsider cannot delete Priya's contact
        with pytest.raises(ServiceError):
            profile_svc.delete_emergency_contact(db, "u_outsider", priya_cid)

        # Outsider cannot update Priya's contact
        with pytest.raises(ServiceError):
            profile_svc.update_emergency_contact(db, "u_outsider", priya_cid, {"full_name": "Hacked"})
    finally:
        db.close()
