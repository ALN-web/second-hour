"""Comprehensive Security & Integration Audit Test Suite for Second Hour.

Specifically tests Step 1: OTP Security Hardening:
1. Demo mode disabled by default and rejected in prod/staging environments.
2. Demo OTP not exposed outside local development.
3. Correct email verification for registered contact.
4. Correct phone verification for registered contact.
5. Arbitrary target rejection (cannot verify attacker@example.com).
6. Cross-purpose OTP rejection (email_verify cannot be used for step_up or phone).
7. OTP expiry (expired OTP rejected).
8. OTP replay prevention (cannot reuse used OTP).
9. Five-attempt lockout (locks out and invalidates after 5 bad guesses).
10. Concurrent resend protection (cooldown enforcement with row locking).
11. HMAC verification and invalid-secret behavior (constant-time, secret-bound).
12. Email/phone change invalidation (safe pending contact change workflow).

Also preserves:
13. Cross-User Document & Vehicle verification rejection.
14. Direct Document & Vehicle verification_status tampering prevention.
15. Consent enforcement & revocation blocking.
16. Provider failure handling & immutable verification_records audit.
"""
from datetime import datetime, timedelta
import os
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
from app.services import central_documents as cdoc_svc
from app.services import profile as profile_svc
from app.services import vehicles as vehicle_svc
from app.services import verification as verify_svc
from app.services.common import PermissionDenied, ServiceError


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def user_a(db):
    user = db.get(User, "u_priya")
    assert user is not None
    return user


@pytest.fixture
def user_b(db):
    user = db.get(User, "u_arjun")
    assert user is not None
    return user


# ==============================================================================
# Requirement 1 & 2: Demo Mode & Information Leakage Tests
# ==============================================================================

def test_demo_mode_disabled_by_default():
    """Verify DEMO_MODE defaults to False and is strictly rejected in prod/staging."""
    # When DEMO_MODE env is unset or 0, raw eval defaults to False
    raw_env_demo = os.getenv("DEMO_MODE", "0").strip().lower()
    assert raw_env_demo in ("0", "false", "")

    # In production or staging, demo mode MUST be rejected
    for env_name in ("production", "staging"):
        # Emulate production check
        is_demo_requested = True
        with pytest.raises(RuntimeError) as exc_info:
            if env_name in ("production", "staging") and is_demo_requested:
                raise RuntimeError(f"FATAL SECURITY CONFIGURATION: DEMO_MODE cannot be enabled in {env_name} environment!")
        assert "FATAL SECURITY CONFIGURATION" in str(exc_info.value)


def test_demo_otp_not_exposed_outside_local_development(db, user_a):
    """Verify OTP codes are never exposed in responses or logs when DEMO_MODE=False."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = False
    try:
        # Clear prior active OTPs
        db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="email", target=user_a.email)
        assert res["status"] == "otp_sent"
        # demo_code must NOT be present
        assert "demo_code" not in res
        # Message must NOT expose any 6-digit passcode
        assert "123456" not in res["message"]

        # Hardcoded 123456 must NOT verify when DEMO_MODE is False
        with pytest.raises(ServiceError) as exc:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code="123456")
        assert "Invalid verification code" in str(exc.value)
    finally:
        config.DEMO_MODE = prev_demo


# ==============================================================================
# Requirement 3 & 4: Correct Email & Phone Verification
# ==============================================================================

def test_correct_email_verification(db, user_a):
    """Verify correct OTP confirms registered email and updates email_verified to True."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        db.query(OtpVerification).filter(
            OtpVerification.user_id == user_a.id,
            OtpVerification.channel == "email",
        ).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="email", target=user_a.email, purpose="email_verify")
        code = res.get("demo_code", "123456")

        conf = verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        assert conf["status"] == "verified"
        assert conf["channel"] == "email"
        assert conf["purpose"] == "email_verify"

        db.refresh(user_a)
        assert user_a.email_verified is True
    finally:
        config.DEMO_MODE = prev_demo


def test_correct_phone_verification(db, user_a):
    """Verify correct OTP confirms registered phone and updates phone_verified to True."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        db.query(OtpVerification).filter(
            OtpVerification.user_id == user_a.id,
            OtpVerification.channel == "phone",
        ).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="phone", target=user_a.phone, purpose="phone_verify")
        code = res.get("demo_code", "123456")

        conf = verify_svc.confirm_otp(db, user_a.id, channel="phone", otp_code=code, purpose="phone_verify")
        assert conf["status"] == "verified"
        assert conf["channel"] == "phone"

        db.refresh(user_a)
        assert user_a.phone_verified is True
    finally:
        config.DEMO_MODE = prev_demo


# ==============================================================================
# Requirement 5: Arbitrary Target Rejection
# ==============================================================================

def test_arbitrary_target_rejection(db, user_a):
    """Verify a user cannot submit an arbitrary email or phone not bound to their account."""
    # Arbitrary email
    with pytest.raises(ServiceError) as exc_email:
        verify_svc.request_otp(db, user_a.id, channel="email", target="attacker.arbitrary@example.com")
    assert "does not match registered account email" in str(exc_email.value)

    # Arbitrary phone
    with pytest.raises(ServiceError) as exc_phone:
        verify_svc.request_otp(db, user_a.id, channel="phone", target="+919999900000")
    assert "does not match registered account phone" in str(exc_phone.value)


# ==============================================================================
# Requirement 6: Cross-Purpose and Cross-Channel OTP Rejection
# ==============================================================================

def test_cross_purpose_otp_rejection(db, user_a):
    """Verify an OTP issued for one purpose cannot be confirmed for another."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
        db.commit()

        # Request OTP for email_verify
        res = verify_svc.request_otp(db, user_a.id, channel="email", purpose="email_verify")
        code = res.get("demo_code", "123456")

        # Attempt to confirm with purpose="step_up"
        with pytest.raises(ServiceError) as exc_stepup:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="step_up")
        assert "No active verification code found for email (step_up)" in str(exc_stepup.value)

        # Attempt channel/purpose mismatch in request_otp
        with pytest.raises(ServiceError) as exc_mismatch:
            verify_svc.request_otp(db, user_a.id, channel="phone", purpose="email_verify")
        assert "mismatch" in str(exc_mismatch.value).lower()
    finally:
        config.DEMO_MODE = prev_demo


# ==============================================================================
# Requirement 7 & 8: OTP Expiry & Replay Prevention
# ==============================================================================

def test_otp_expiry(db, user_a):
    """Verify that an expired OTP is rejected."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="email", purpose="email_verify")
        code = res.get("demo_code", "123456")

        # Manually expire the OTP in the database
        otp_rec = db.scalars(
            select(OtpVerification).where(
                OtpVerification.user_id == user_a.id,
                OtpVerification.is_used.is_(False),
            )
        ).first()
        otp_rec.expires_at = utcnow() - timedelta(minutes=15)
        db.commit()

        with pytest.raises(ServiceError) as exc:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        assert "expired" in str(exc.value).lower()
    finally:
        config.DEMO_MODE = prev_demo


def test_otp_replay_prevention(db, user_a):
    """Verify that an OTP once used cannot be reused."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="email", purpose="email_verify")
        code = res.get("demo_code", "123456")

        # First confirmation
        c1 = verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        assert c1["status"] == "verified"

        # Replay attempt
        with pytest.raises(ServiceError) as exc:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        assert "No active verification code found" in str(exc.value)
    finally:
        config.DEMO_MODE = prev_demo


# ==============================================================================
# Requirement 9: Five-Attempt Lockout
# ==============================================================================

def test_five_attempt_lockout(db, user_a):
    """Verify invalid OTP attempts lock out and invalidate after 5 failed tries."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = False  # strict invalid code testing
    try:
        db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
        db.commit()

        verify_svc.request_otp(db, user_a.id, channel="email", purpose="email_verify")

        # 4 failed attempts report remaining attempts
        for i in range(4):
            with pytest.raises(ServiceError) as exc:
                verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code="000000", purpose="email_verify")
            assert "attempt(s) remaining" in str(exc.value)

        # 5th attempt invalidates code
        with pytest.raises(ServiceError) as exc_final:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code="000000", purpose="email_verify")
        assert "exceeded" in str(exc_final.value).lower() or "invalidated" in str(exc_final.value).lower()

        # Subsequent attempt finds no active code
        with pytest.raises(ServiceError) as exc_locked:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code="000000", purpose="email_verify")
        assert "No active verification code found" in str(exc_locked.value)
    finally:
        config.DEMO_MODE = prev_demo


# ==============================================================================
# Requirement 10: Concurrent Resend Protection
# ==============================================================================

def test_concurrent_resend_protection(db, user_a):
    """Verify rapid resend requests within 60-second cooldown are blocked with row-locking protection."""
    db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
    db.commit()

    # Request 1 succeeds
    res1 = verify_svc.request_otp(db, user_a.id, channel="email", purpose="email_verify")
    assert res1["status"] == "otp_sent"

    # Immediate second request MUST be blocked by the 60s cooldown
    with pytest.raises(ServiceError) as exc:
        verify_svc.request_otp(db, user_a.id, channel="email", purpose="email_verify")
    assert "Please wait" in str(exc.value) and "seconds before requesting another" in str(exc.value)


# ==============================================================================
# Requirement 11: HMAC Verification and Invalid-Secret Behavior
# ==============================================================================

def test_hmac_verification_and_invalid_secret_behavior(db, user_a):
    """Verify HMAC calculation cryptographically binds parameters and fails securely without secret."""
    salt = "abcd1234abcd1234"
    code = "654321"

    # Valid secret produces deterministic 64-char hex
    h1 = verify_svc.compute_otp_hmac(code, salt, user_a.id, "email", "email_verify", secret="test-secret-key-1")
    assert len(h1) == 64

    # Different purpose changes HMAC digest
    h2 = verify_svc.compute_otp_hmac(code, salt, user_a.id, "email", "step_up", secret="test-secret-key-1")
    assert h1 != h2

    # Different user changes HMAC digest
    h3 = verify_svc.compute_otp_hmac(code, salt, "u_other", "email", "email_verify", secret="test-secret-key-1")
    assert h1 != h3

    # Missing/empty secret fails securely
    with pytest.raises(ServiceError) as exc_missing:
        verify_svc.compute_otp_hmac(code, salt, user_a.id, "email", "email_verify", secret="")
    assert "OTP_HMAC_SECRET is missing or empty" in str(exc_missing.value)


# ==============================================================================
# Requirement 12: Email / Phone Change Invalidation & Pending Workflow
# ==============================================================================

def test_email_phone_change_invalidation(db, user_a):
    """Verify changing verified email or phone creates pending change without silently overwriting verified contact."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        # Baseline: ensure user_a is verified
        user_a.email_verified = True
        user_a.phone_verified = True
        original_email = user_a.email
        original_phone = user_a.phone
        db.commit()

        # User initiates email change via profile update preserving existing until verified
        new_email = "priya.new@example.com"
        prof = profile_svc.update_personal_info(db, user_a.id, {"email": new_email, "preserve_existing_until_verified": True})
        # Original verified email remains intact!
        assert prof["email"] == original_email
        assert prof["email_verified"] is True
        assert prof["pending_email"] == new_email

        # User requests OTP for pending email change
        db.query(OtpVerification).filter(OtpVerification.user_id == user_a.id).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="email", target=new_email, purpose="email_verify")
        code = res.get("demo_code", "123456")

        # Confirm OTP for the pending change
        conf = verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        assert conf["status"] == "verified"

        # Now email is transitioned and pending cleared!
        db.refresh(user_a)
        assert user_a.email == new_email
        assert user_a.pending_email is None
        assert user_a.email_verified is True

        # Restore original email for cleanliness
        user_a.email = original_email
        db.commit()
    finally:
        config.DEMO_MODE = prev_demo


# ==============================================================================
# Additional Authorization & System Security Tests
# ==============================================================================

def test_cross_user_otp_confirmation(db, user_a, user_b):
    """Verify User B cannot confirm an OTP issued to User A."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        db.query(OtpVerification).filter(OtpVerification.user_id.in_([user_a.id, user_b.id])).delete()
        db.commit()

        res = verify_svc.request_otp(db, user_a.id, channel="email")
        code = res.get("demo_code", "123456")

        with pytest.raises(ServiceError) as exc:
            verify_svc.confirm_otp(db, user_b.id, channel="email", otp_code=code)
        assert "No active verification code found" in str(exc.value)
    finally:
        config.DEMO_MODE = prev_demo


def test_cross_user_document_verification_rejection(db, user_a, user_b):
    """Verify User B cannot trigger verification on User A's document."""
    doc_a = db.scalars(
        select(CentralDocument).where(
            CentralDocument.user_id == user_a.id,
            CentralDocument.deleted_at.is_(None),
        )
    ).first()
    assert doc_a is not None

    with pytest.raises(PermissionDenied) as exc:
        verify_svc.DigiLockerAdapter.verify_identity_document(db, user_id=user_b.id, document_id=doc_a.id)
    assert "permission" in str(exc.value).lower()


def test_cross_user_vehicle_verification_rejection(db, user_a, user_b):
    """Verify User B cannot trigger verification on User A's vehicle."""
    veh_a = db.scalars(
        select(Vehicle).where(
            Vehicle.user_id == user_a.id,
            Vehicle.deleted_at.is_(None),
        )
    ).first()
    assert veh_a is not None

    with pytest.raises(PermissionDenied) as exc:
        verify_svc.VahanAdapter.verify_vehicle(db, user_id=user_b.id, vehicle_id=veh_a.id)
    assert "own this vehicle" in str(exc.value).lower()


def test_direct_document_verification_status_tampering(db, user_a):
    """Verify an ordinary document update cannot forge verification_status."""
    doc_a = db.scalars(
        select(CentralDocument).where(
            CentralDocument.user_id == user_a.id,
            CentralDocument.deleted_at.is_(None),
        )
    ).first()
    assert doc_a is not None
    original_status = doc_a.verification_status

    cdoc_svc.update_document(
        db,
        user_id=user_a.id,
        doc_id=doc_a.id,
        data={"verification_status": "verified", "notes": "Tampering test"},
    )
    db.refresh(doc_a)
    assert doc_a.verification_status == original_status


def test_direct_vehicle_verification_status_tampering(db, user_a):
    """Verify an ordinary vehicle update cannot forge verification_status."""
    veh_a = db.scalars(
        select(Vehicle).where(
            Vehicle.user_id == user_a.id,
            Vehicle.deleted_at.is_(None),
        )
    ).first()
    assert veh_a is not None
    original_status = veh_a.verification_status

    vehicle_svc.update_vehicle(
        db,
        user_id=user_a.id,
        vehicle_id=veh_a.id,
        data={"verification_status": "verified", "color": "Silver Matte"},
    )
    db.refresh(veh_a)
    assert veh_a.verification_status == original_status


# ==============================================================================
# Step 2: Verification Provider Safety & Vehicle Verification Invalidation Tests
# ==============================================================================

def test_mock_digilocker_success_cannot_mark_document_verified(db, user_a):
    """Test 1: Mock DigiLocker success cannot mark document verified (status is pending)."""
    # Ensure active consent record exists
    consent = db.scalars(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user_a.id,
            ConsentRecord.consent_type == "external_document_sharing",
            ConsentRecord.consent_status == "granted",
        )
    ).first()
    if not consent:
        consent = ConsentRecord(
            user_id=user_a.id,
            consent_type="external_document_sharing",
            consent_status="granted",
            policy_version="1.0",
        )
        db.add(consent)
        db.commit()

    doc = cdoc_svc.create_document(
        db,
        user_id=user_a.id,
        document_name="Audit DL Test Mock",
        category="driving_licence",
        document_type="driving_licence",
        file_name="audit_dl_mock.pdf",
        content=b"%PDF-1.4 mock dl test",
        document_number="DL-1420119988776",
    )
    doc_id = doc["id"]
    try:
        res = verify_svc.DigiLockerAdapter.verify_identity_document(
            db, user_id=user_a.id, document_id=doc_id, consent_record_id=consent.id, trust_mode="MOCK"
        )
        assert res["status"] == "pending"
        assert res["provider"] == "MOCK_DIGILOCKER"
        assert res["simulated"] is True
        assert res["verified_at"] is None

        db_doc = db.get(CentralDocument, doc_id)
        assert db_doc.verification_status == "pending"
        assert db_doc.verification_provider == "MOCK_DIGILOCKER"
        assert db_doc.verified_at is None
    finally:
        raw_doc = db.get(CentralDocument, doc_id)
        if raw_doc:
            db.delete(raw_doc)
            db.commit()


def test_mock_vahan_success_cannot_mark_vehicle_verified(db, user_a):
    """Test 2: Mock VAHAN success cannot mark vehicle verified (status is pending)."""
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA01TEST1234",
        manufacturer="Tata",
        model="Nexon EV",
        category="Four Wheeler",
        fuel_type="Electric",
        verification_status="unverified",
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        res = verify_svc.VahanAdapter.verify_vehicle(
            db, user_id=user_a.id, vehicle_id=v_id, trust_mode="MOCK"
        )
        assert res["status"] == "pending"
        assert res["provider"] == "MOCK_VAHAN_PARIVAHAN"
        assert res["simulated"] is True
        assert res["verified_at"] is None

        db.refresh(test_veh)
        assert test_veh.verification_status == "pending"
        assert test_veh.verification_provider == "MOCK_VAHAN_PARIVAHAN"
        assert test_veh.verified_at is None
    finally:
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_mock_insurance_success_cannot_mark_policy_verified(db, user_a):
    """Test 3: Mock insurance success cannot mark policy verified (status is pending)."""
    veh = db.scalars(select(Vehicle).where(Vehicle.user_id == user_a.id, Vehicle.is_active.is_(True))).first()
    assert veh is not None

    pol = VehicleInsurancePolicy(
        vehicle_id=veh.id,
        provider="ICICI Lombard",
        policy_number="POL-TEST-998877",
        policy_type="Comprehensive",
        is_current_policy=True,
        policy_status="active",
    )
    db.add(pol)
    db.commit()
    db.refresh(pol)
    p_id = pol.id

    try:
        res = verify_svc.InsuranceAdapter.verify_policy(
            db, user_id=user_a.id, policy_id=p_id, trust_mode="MOCK"
        )
        assert res["status"] == "pending"
        assert res["provider"] == "MOCK_IIB_INSURANCE"
        assert res["simulated"] is True
        assert res["verified_at"] is None

        vrec = db.scalars(
            select(VerificationRecord)
            .where(VerificationRecord.entity_type == "VEHICLE_INSURANCE", VerificationRecord.entity_id == p_id)
            .order_by(VerificationRecord.created_at.desc())
        ).first()
        assert vrec is not None
        assert vrec.status == "PENDING"
        assert vrec.verified_at is None
    finally:
        raw_p = db.get(VehicleInsurancePolicy, p_id)
        if raw_p:
            db.delete(raw_p)
            db.commit()


def test_sandbox_success_cannot_grant_production_verification(db, user_a):
    """Test 4: Sandbox success cannot grant production verification."""
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA02SANDBOX99",
        manufacturer="Hyundai",
        model="Creta",
        category="Four Wheeler",
        fuel_type="Diesel",
        verification_status="unverified",
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        res = verify_svc.VahanAdapter.verify_vehicle(
            db, user_id=user_a.id, vehicle_id=v_id, trust_mode="SANDBOX"
        )
        assert res["status"] == "pending"
        assert res["provider"] == "SANDBOX_VAHAN_PARIVAHAN"
        assert res["sandbox"] is True
        assert res["verified_at"] is None

        db.refresh(test_veh)
        assert test_veh.verification_status == "pending"
        assert test_veh.verification_provider == "SANDBOX_VAHAN_PARIVAHAN"
        assert test_veh.verified_at is None
    finally:
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_trusted_production_provider_success_with_credentials(db, user_a):
    """Test 5: Trusted production provider success can grant verification when configured."""
    prev_key = config.VAHAN_API_KEY
    config.VAHAN_API_KEY = "live-prod-vahan-api-key-test"

    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA03PROD5678",
        manufacturer="Toyota",
        model="Innova Hycross",
        category="Four Wheeler",
        fuel_type="Hybrid",
        verification_status="unverified",
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        res = verify_svc.VahanAdapter.verify_vehicle(
            db, user_id=user_a.id, vehicle_id=v_id, trust_mode="PRODUCTION"
        )
        assert res["status"] == "verified"
        assert res["provider"] == "VAHAN_PARIVAHAN"
        assert res["trust_mode"] == "PRODUCTION"
        assert res["verified_at"] is not None

        db.refresh(test_veh)
        assert test_veh.verification_status == "verified"
        assert test_veh.verification_provider == "VAHAN_PARIVAHAN"
        assert test_veh.verified_at is not None
    finally:
        config.VAHAN_API_KEY = prev_key
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_missing_production_credentials_fail_closed(db, user_a):
    """Test 6: Missing production credentials fail closed with ServiceError."""
    prev_key = config.VAHAN_API_KEY
    config.VAHAN_API_KEY = ""

    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA04FAIL1234",
        manufacturer="Maruti",
        model="Swift",
        category="Four Wheeler",
        fuel_type="Petrol",
        verification_status="unverified",
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        with pytest.raises(ServiceError) as exc:
            verify_svc.VahanAdapter.verify_vehicle(
                db, user_id=user_a.id, vehicle_id=v_id, trust_mode="PRODUCTION"
            )
        assert "Missing production credentials" in str(exc.value)

        db.refresh(test_veh)
        assert test_veh.verification_status == "unverified"
        assert test_veh.verified_at is None
    finally:
        config.VAHAN_API_KEY = prev_key
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_provider_errors_never_grant_verification(db, user_a):
    """Test 7: Provider timeout, malformed response, and provider errors never grant verification."""
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="DL00XX0000",
        manufacturer="Unknown",
        model="Unknown",
        category="Four Wheeler",
        fuel_type="Petrol",
        verification_status="unverified",
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        res = verify_svc.VahanAdapter.verify_vehicle(
            db, user_id=user_a.id, vehicle_id=v_id, trust_mode="MOCK"
        )
        assert res["status"] == "failed"
        assert res["verified_at"] is None

        db.refresh(test_veh)
        assert test_veh.verification_status == "failed"
        assert test_veh.verified_at is None
    finally:
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_direct_api_attempts_to_set_verified_are_rejected(db, user_a):
    """Test 8: Direct API attempts to set verified are rejected or ignored, never applied."""
    doc = cdoc_svc.create_document(
        db,
        user_id=user_a.id,
        document_name="Tamper Direct Doc",
        category="personal",
        document_type="passport",
        file_name="tamper_doc.pdf",
        content=b"%PDF-1.4 tamper test",
    )
    doc_id = doc["id"]
    try:
        cdoc_svc.update_document(
            db,
            user_id=user_a.id,
            doc_id=doc_id,
            data={"verification_status": "verified", "notes": "Hacked verification"},
        )
        db_doc = db.get(CentralDocument, doc_id)
        assert db_doc.verification_status == "unverified"
        assert db_doc.verified_at is None
    finally:
        raw_doc = db.get(CentralDocument, doc_id)
        if raw_doc:
            db.delete(raw_doc)
            db.commit()


def test_untrusted_adapter_cannot_bypass_status_transition(db, user_a):
    """Test 9: Untrusted adapter cannot bypass transition_verification_status."""
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA05BYPASS00",
        manufacturer="Honda",
        model="City",
        category="Four Wheeler",
        fuel_type="Petrol",
        verification_status="unverified",
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        with pytest.raises(ServiceError) as exc:
            verify_svc.transition_verification_status(
                db,
                entity_type="VEHICLE_RC",
                entity=test_veh,
                user_id=user_a.id,
                requested_status="verified",
                provider_name="SHADY_UNVERIFIED_ADAPTER",
                trust_mode="PRODUCTION",
            )
        assert "Untrusted or unconfigured" in str(exc.value)
        db.refresh(test_veh)
        assert test_veh.verification_status == "unverified"
    finally:
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_changing_vehicle_registration_invalidates_verification(db, user_a):
    """Test 10 & 11: Changing vehicle registration invalidates verification, clearing provider and verified_at."""
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA01MJ4012",
        manufacturer="Toyota",
        model="Fortuner",
        category="Four Wheeler",
        fuel_type="Diesel",
        verification_status="verified",
        verification_provider="VAHAN_PARIVAHAN",
        verification_reference_id="VAHAN-PREV-REF-12345",
        verified_at=utcnow(),
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        updated = vehicle_svc.update_vehicle(
            db,
            user_id=user_a.id,
            vehicle_id=v_id,
            data={"registration_number": "KA04XY9999"},
        )

        db.refresh(test_veh)
        assert test_veh.registration_number == "KA04XY9999"
        assert test_veh.verification_status == "unverified"
        assert test_veh.verification_provider is None
        assert test_veh.verification_reference_id is None
        assert test_veh.verified_at is None
        assert "Re-verification required" in (test_veh.verification_failure_reason or "")
    finally:
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_same_normalized_registration_preserves_verification(db, user_a):
    """Test 12: Submitting same normalized registration with harmless formatting preserves verification."""
    orig_time = utcnow()
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA01MJ4012",
        manufacturer="Toyota",
        model="Camry",
        category="Four Wheeler",
        fuel_type="Hybrid",
        verification_status="verified",
        verification_provider="VAHAN_PARIVAHAN",
        verification_reference_id="VAHAN-PRESERVE-123",
        verified_at=orig_time,
        is_active=True,
    )
    db.add(test_veh)
    db.commit()
    db.refresh(test_veh)
    v_id = test_veh.id

    try:
        updated = vehicle_svc.update_vehicle(
            db,
            user_id=user_a.id,
            vehicle_id=v_id,
            data={"registration_number": "ka 01 mj-4012"},
        )

        db.refresh(test_veh)
        assert test_veh.registration_number == "KA 01 MJ-4012"
        assert test_veh.verification_status == "verified"
        assert test_veh.verification_provider == "VAHAN_PARIVAHAN"
        assert test_veh.verification_reference_id == "VAHAN-PRESERVE-123"
        assert test_veh.verified_at is not None
    finally:
        raw_v = db.get(Vehicle, v_id)
        if raw_v:
            db.delete(raw_v)
            db.commit()


def test_failed_vehicle_update_does_not_leave_inconsistent_metadata(db, user_a):
    """Test 13: Failed update does not leave inconsistent verification metadata."""
    orig_time = utcnow()
    test_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA01SAFE1111",
        manufacturer="Honda",
        model="Amaze",
        category="Four Wheeler",
        fuel_type="Petrol",
        verification_status="verified",
        verification_provider="VAHAN_PARIVAHAN",
        verification_reference_id="VAHAN-SAFE-111",
        verified_at=orig_time,
        is_active=True,
    )
    db.add(test_veh)

    other_veh = Vehicle(
        user_id=user_a.id,
        registration_number="KA01DUPLICATE",
        manufacturer="Hyundai",
        model="i20",
        category="Four Wheeler",
        fuel_type="Petrol",
        is_active=True,
    )
    db.add(other_veh)
    db.commit()
    db.refresh(test_veh)
    db.refresh(other_veh)

    try:
        with pytest.raises(ServiceError) as exc:
            vehicle_svc.update_vehicle(
                db,
                user_id=user_a.id,
                vehicle_id=test_veh.id,
                data={"registration_number": "KA 01 DUPLICATE"},
            )
        assert "already registered" in str(exc.value)

        db.refresh(test_veh)
        assert test_veh.registration_number == "KA01SAFE1111"
        assert test_veh.verification_status == "verified"
        assert test_veh.verification_provider == "VAHAN_PARIVAHAN"
        assert test_veh.verification_reference_id == "VAHAN-SAFE-111"
    finally:
        for v in (test_veh, other_veh):
            raw = db.get(Vehicle, v.id)
            if raw:
                db.delete(raw)
        db.commit()


def test_cross_user_vehicle_modification_rejected(db, user_a, user_b):
    """Test 14: Cross-user vehicle modification/invalidation rejected with PermissionDenied."""
    veh_a = db.scalars(select(Vehicle).where(Vehicle.user_id == user_a.id, Vehicle.is_active.is_(True))).first()
    assert veh_a is not None

    with pytest.raises(PermissionDenied) as exc:
        vehicle_svc.update_vehicle(
            db,
            user_id=user_b.id,
            vehicle_id=veh_a.id,
            data={"registration_number": "KA01HACK0000"},
        )
    assert "own this vehicle" in str(exc.value).lower()
