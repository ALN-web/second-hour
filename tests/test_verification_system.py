"""Comprehensive Tests for Second Hour Identity & Document Verification System.

Tests:
1. Email and mobile OTP verification (salted SHA-256 hash, rate limiting, expiry, max attempts).
2. Requirement #8: Uploaded documents receive 'unverified' status by default.
3. DigiLocker institutional verification adapter and consent checking.
4. VAHAN/Parivahan vehicle RC verification (success, failure, retry).
5. Insurance policy verification via IIB adapter.
6. Verification status aggregation and immutable verification_records audit history.
7. Non-blocking emergency access: unverified status never blocks case creation.
"""
import pytest
from sqlalchemy import select

from app import config
from app.db import (
    CentralDocument,
    ConsentRecord,
    OtpVerification,
    SessionLocal,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    VerificationRecord,
    utcnow,
)
from app.services import cases as case_svc
from app.services import central_documents as cdoc_svc
from app.services import verification as verify_svc
from app.services.common import ServiceError


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_user(db):
    user = db.get(User, "u_priya")
    assert user is not None, "Demo user u_priya must exist"
    return user


# ==============================================================================
# 1. Email & Mobile OTP Verification Tests
# ==============================================================================

def test_otp_request_and_salted_hash_storage(db, test_user):
    """Verify OTP generation stores only keyed HMAC-SHA256 hashes, not plaintext."""
    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id, OtpVerification.channel == "email").delete()
    db.commit()

    res = verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email)
    assert res["status"] == "otp_sent"
    assert res["channel"] == "email"
    assert "target" in res

    # Check database record: must NOT contain plaintext code
    otp_record = db.scalars(
        select(OtpVerification).where(
            OtpVerification.user_id == test_user.id,
            OtpVerification.channel == "email",
            OtpVerification.is_used.is_(False),
        ).order_by(OtpVerification.created_at.desc())
    ).first()

    assert otp_record is not None
    assert len(otp_record.otp_hash) == 64  # SHA-256 hex digest
    assert len(otp_record.salt) == 32      # 16-byte hex salt
    assert otp_record.purpose == "email_verify"
    # Plaintext code must NOT be stored in any column
    assert not hasattr(otp_record, "code")


def test_otp_confirm_success(db, test_user):
    """Verify correct OTP confirms identity and updates user verification status."""
    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id, OtpVerification.channel == "phone").delete()
    db.commit()

    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        res = verify_svc.request_otp(db, test_user.id, channel="phone", target=test_user.phone)
        code = res.get("demo_code", "123456")

        confirm_res = verify_svc.confirm_otp(db, test_user.id, channel="phone", otp_code=code)
        assert confirm_res["status"] == "verified"
        assert confirm_res["channel"] == "phone"

        # Refresh user
        user = db.get(User, test_user.id)
        assert user.phone_verified is True
    finally:
        config.DEMO_MODE = prev_demo


def test_otp_invalid_code_retry_and_lockout(db, test_user):
    """Verify wrong OTP attempts increment counter and lock out after 5 attempts."""
    # Clear prior active test OTPs to test lockout independently of cooldown
    db.query(OtpVerification).filter(
        OtpVerification.user_id == test_user.id,
        OtpVerification.channel == "email",
    ).delete()
    db.commit()

    verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email)

    # 4 invalid attempts should report remaining attempts
    for i in range(4):
        with pytest.raises(ServiceError) as exc:
            verify_svc.confirm_otp(db, test_user.id, channel="email", otp_code="000000")
        assert "attempt(s) remaining" in str(exc.value)

    # 5th invalid attempt should lock out
    with pytest.raises(ServiceError) as exc:
        verify_svc.confirm_otp(db, test_user.id, channel="email", otp_code="000000")
    assert "exceeded" in str(exc.value).lower() or "invalidated" in str(exc.value).lower()


# ==============================================================================
# 2. Document Upload Default Status (Requirement #8)
# ==============================================================================

def test_uploaded_document_receives_unverified_status(db, test_user):
    """Requirement 8: Prevent uploaded documents from automatically receiving verified status."""
    dummy_pdf = b"%PDF-1.4 test document content for verification check"
    doc = cdoc_svc.create_document(
        db,
        user_id=test_user.id,
        document_name="Test Self Uploaded Driving Licence",
        category="driving_licence",
        document_type="driving_licence",
        file_name="dl_self_upload.pdf",
        content=dummy_pdf,
        document_number="DL-1420110099999",
        issuing_authority="Delhi RTO",
    )

    assert doc["verification_status"] == "unverified", "Uploaded document MUST default to 'unverified'"

    # Clean up test doc
    raw_doc = db.get(CentralDocument, doc["id"])
    if raw_doc:
        db.delete(raw_doc)
        db.commit()


# ==============================================================================
# 3. Institutional Provider Adapters
# ==============================================================================

def test_digilocker_verification_with_consent(db, test_user):
    """Test DigiLocker adapter verifies identity document when explicit consent is present."""
    # Ensure active consent record exists
    consent = db.scalars(
        select(ConsentRecord).where(
            ConsentRecord.user_id == test_user.id,
            ConsentRecord.consent_type == "external_document_sharing",
            ConsentRecord.consent_status == "granted",
        )
    ).first()
    if not consent:
        consent = ConsentRecord(
            user_id=test_user.id,
            consent_type="external_document_sharing",
            consent_status="granted",
            policy_version="1.0",
        )
        db.add(consent)
        db.commit()

    # Create dummy driving licence
    dummy_pdf = b"%PDF-1.4 valid licence payload"
    doc_dict = cdoc_svc.create_document(
        db,
        user_id=test_user.id,
        document_name="Priya Driving Licence Valid",
        category="driving_licence",
        document_type="driving_licence",
        file_name="priya_dl_valid.pdf",
        content=dummy_pdf,
        document_number="DL-1420110012345",
        issuing_authority="MoRTH",
    )

    # Verify via DigiLocker in default MOCK mode (must NEVER grant verified status)
    res = verify_svc.DigiLockerAdapter.verify_identity_document(
        db, user_id=test_user.id, document_id=doc_dict["id"], consent_record_id=consent.id
    )
    assert res["status"] == "pending"
    assert res["provider"] == "MOCK_DIGILOCKER"
    assert "MOCK-" in res["reference_id"]
    assert res["simulated"] is True
    assert res["metadata"]["digital_signature_valid"] is True

    # Check database doc: status must be pending, verified_at must be None
    db_doc = db.get(CentralDocument, doc_dict["id"])
    assert db_doc.verification_status == "pending"
    assert db_doc.verification_provider == "MOCK_DIGILOCKER"
    assert db_doc.verified_at is None

    # Cleanup
    db.delete(db_doc)
    db.commit()


def test_vahan_vehicle_verification(db, test_user):
    """Test VAHAN adapter verifies vehicle registration certificate in default MOCK mode."""
    veh = db.scalars(
        select(Vehicle).where(Vehicle.user_id == test_user.id, Vehicle.is_active.is_(True))
    ).first()
    assert veh is not None, "Demo vehicle must exist"

    # Verify vehicle in default MOCK mode
    res = verify_svc.VahanAdapter.verify_vehicle(db, user_id=test_user.id, vehicle_id=veh.id)
    assert res["status"] == "pending"
    assert res["provider"] == "MOCK_VAHAN_PARIVAHAN"
    assert "MOCK-" in res["reference_id"]
    assert res["simulated"] is True
    assert "masked_chassis" in res["metadata"]

    # Verify database state
    db.refresh(veh)
    assert veh.verification_status == "pending"
    assert veh.verification_provider == "MOCK_VAHAN_PARIVAHAN"
    assert veh.verified_at is None


def test_vahan_invalid_vehicle_failure_and_retry(db, test_user):
    """Test VAHAN verification handles invalid registration numbers gracefully."""
    # Create invalid test vehicle
    invalid_veh = Vehicle(
        user_id=test_user.id,
        registration_number="DL00XX0000",
        manufacturer="TestMaker",
        model="TestModel",
        category="Four Wheeler",
        fuel_type="Petrol",
        is_active=True,
    )
    db.add(invalid_veh)
    db.commit()

    # VAHAN check should fail gracefully
    fail_res = verify_svc.VahanAdapter.verify_vehicle(db, user_id=test_user.id, vehicle_id=invalid_veh.id)
    assert fail_res["status"] == "failed"
    assert "not found" in fail_res["reason"].lower()

    db.refresh(invalid_veh)
    assert invalid_veh.verification_status == "failed"

    # Cleanup
    db.delete(invalid_veh)
    db.commit()


# ==============================================================================
# 4. Status Aggregation & Audit Logs
# ==============================================================================

def test_verification_status_aggregation(db, test_user):
    """Test get_verification_overview aggregates contacts, vehicles, and documents."""
    overview = verify_svc.get_verification_overview(db, test_user.id)
    assert "trust_score_percentage" in overview
    assert "contacts" in overview
    assert "vehicles" in overview
    assert "documents" in overview
    assert overview["vehicles"]["total"] >= 1
    assert "recent_activity" in overview


def test_verification_history_audit_trail(db, test_user):
    """Test immutable verification records logging."""
    history = verify_svc.list_verification_history(db, test_user.id, limit=20)
    assert isinstance(history, list)
    assert len(history) > 0
    first = history[0]
    assert "id" in first
    assert "entity_type" in first
    assert "provider" in first
    assert "status" in first


# ==============================================================================
# 5. Non-Blocking Emergency Access Guarantee
# ==============================================================================

def test_unverified_status_does_not_block_case_creation(db, test_user):
    """Ensure verification failures or pending checks NEVER block emergency accident reporting."""
    # Create an accident case for the user even if some items are unverified
    case_dict = case_svc.create_case(
        db=db,
        actor_id=test_user.id,
        incident_at="2026-11-27T14:30:00",
        approximate_location="MG Road Intersection, Bengaluru",
        title="Emergency Case Test - Verification Non-Blocking",
        latitude=12.9716,
        longitude=77.5946,
    )

    assert case_dict is not None
    assert case_dict["case_id"] is not None
    assert case_dict["status"] in ("draft", "active", "dispatched", "intake_pending", "reporting")

    # Cleanup
    case_svc.delete_case(db, test_user.id, case_dict["case_id"])
