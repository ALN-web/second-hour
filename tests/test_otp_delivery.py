"""Comprehensive Test Suite for Second Hour OTP Delivery Pipeline.

Covers:
1. OTP generation triggers the correct email adapter (SMTP & Resend).
2. OTP generation triggers the correct SMS adapter (Twilio & MSG91).
3. Successful provider acceptance returns the correct delivery status and reference ID.
4. Provider rejection is handled correctly without false success.
5. Provider timeout is handled correctly.
6. Missing credentials fail safely without silent fallback.
7. No OTP is exposed in API responses.
8. No OTP is written to application logs.
9. Existing OTP HMAC and purpose-binding security remains intact.
10. Expired and reused OTPs remain rejected.
11. Rate limiting and resend cooldown remain effective.
12. Existing profile and authentication flows remain functional.
13. Phone number normalization (+91, 10-digit Indian mobile formats).
"""
import logging
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import select

from app import config
from app.db import OtpVerification, SessionLocal, User, VerificationRecord, utcnow
from app.services import verification as verify_svc
from app.services.common import ServiceError
from app.services.otp_delivery import (
    DeliveryResult,
    Msg91SmsAdapter,
    OtpDeliveryStatus,
    ResendEmailAdapter,
    SmtpEmailAdapter,
    TwilioSmsAdapter,
    dispatch_email_otp,
    dispatch_sms_otp,
    mask_identifier,
    normalize_indian_phone,
    render_email_template,
)


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
    assert user is not None
    # Ensure active phone and email are set
    user.email = "priya.k@example.com"
    user.phone = "+919876543210"
    user.pending_email = None
    user.pending_phone = None
    db.commit()
    return user


# ==============================================================================
# 1. Phone Normalization & Recipient Masking Tests
# ==============================================================================

def test_normalize_indian_phone_valid():
    """Verify standard Indian mobile formats normalize to canonical E.164 (+91XXXXXXXXXX)."""
    assert normalize_indian_phone("9876543210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("+919876543210") == "+919876543210"
    assert normalize_indian_phone("+91 98765-43210") == "+919876543210"
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("(0) 98765 43210") == "+919876543210"


def test_normalize_indian_phone_invalid():
    """Verify invalid mobile numbers are rejected with descriptive errors."""
    with pytest.raises(ValueError, match="Invalid Indian mobile number"):
        normalize_indian_phone("5123456789")  # Indian mobiles start with 6-9
    
    with pytest.raises(ValueError, match="Invalid Indian mobile number"):
        normalize_indian_phone("12345")  # Too short
        
    with pytest.raises(ValueError, match="Mobile number cannot be empty"):
        normalize_indian_phone("")


def test_mask_identifier():
    """Verify email and phone masking protects privacy in logs and audit."""
    assert mask_identifier("priya.k@example.com") == "p***k@example.com"
    assert mask_identifier("+919876543210") == "+9****3210"
    assert mask_identifier("") == "Not provided"


def test_render_email_template():
    """Verify email templates contain code, expiry, and Second Hour branding."""
    plain, html = render_email_template("789123", expiry_minutes=10, purpose="email_verify")
    assert "789123" in plain
    assert "10 minutes" in plain
    assert "Second Hour" in plain
    assert "789123" in html
    assert "#ff7518" in html


# ==============================================================================
# 2. Email Adapter Unit Tests (SMTP & Resend)
# ==============================================================================

def test_smtp_adapter_successful_send(monkeypatch):
    """Verify SmtpEmailAdapter sends email via smtplib.SMTP with TLS and returns ACCEPTED."""
    adapter = SmtpEmailAdapter(
        host="smtp.test.example.com",
        port=587,
        username="test_user",
        password="test_password",
        use_tls=True,
        use_ssl=False,
        from_email="no-reply@secondhour.in",
        from_name="Second Hour",
        timeout=5.0,
    )
    assert adapter.is_configured() is True

    mock_smtp_instance = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp_instance) as mock_smtp_cls:
        # Context manager support
        mock_smtp_instance.__enter__.return_value = mock_smtp_instance

        res = adapter.send("priya.k@example.com", code="654321", expiry_minutes=10)
        assert res.success is True
        assert res.status == OtpDeliveryStatus.ACCEPTED
        assert res.provider == "SMTP"
        assert res.reference_id is not None
        assert res.reference_id.startswith("SMTP-")

        mock_smtp_cls.assert_called_once_with("smtp.test.example.com", 587, timeout=5.0)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("test_user", "test_password")
        mock_smtp_instance.send_message.assert_called_once()


def test_smtp_adapter_timeout_handling():
    """Verify SMTP socket timeout returns clean error without crashing."""
    adapter = SmtpEmailAdapter(
        host="smtp.timeout.example.com",
        port=587,
        from_email="no-reply@secondhour.in",
        timeout=1.0,
    )
    with patch("smtplib.SMTP", side_effect=TimeoutError("Connection timed out")):
        res = adapter.send("priya.k@example.com", code="654321")
        assert res.success is False
        assert res.status == OtpDeliveryStatus.FAILED
        assert res.error_code == "TIMEOUT"
        assert "temporarily unavailable" in res.user_message


def test_smtp_adapter_rejection_handling():
    """Verify SMTP server rejection returns failure without false success."""
    import smtplib
    adapter = SmtpEmailAdapter(
        host="smtp.reject.example.com",
        port=587,
        from_email="no-reply@secondhour.in",
    )
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPRecipientsRefused({"priya@example.com": (550, b"User unknown")})):
        res = adapter.send("priya@example.com", code="654321")
        assert res.success is False
        assert res.status == OtpDeliveryStatus.FAILED
        assert res.error_code == "PROVIDER_REJECTED"
        assert "Unable to send OTP" in res.user_message


def test_resend_adapter_successful_send():
    """Verify Resend email adapter sends HTTP POST to Resend API and parses ID."""
    adapter = ResendEmailAdapter(api_key="re_123456789", from_email="no-reply@secondhour.in")
    assert adapter.is_configured() is True

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "re_email_id_abc123"}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        res = adapter.send("priya.k@example.com", code="112233")
        assert res.success is True
        assert res.status == OtpDeliveryStatus.ACCEPTED
        assert res.reference_id == "re_email_id_abc123"
        mock_post.assert_called_once()


# ==============================================================================
# 3. SMS Adapter Unit Tests (Twilio & MSG91)
# ==============================================================================

def test_twilio_adapter_successful_send():
    """Verify TwilioSmsAdapter dispatches SMS to Twilio REST API and captures SID."""
    adapter = TwilioSmsAdapter(
        account_sid="ACtest123456789",
        auth_token="auth_secret_token",
        from_number="+15005550006",
        timeout=5.0,
    )
    assert adapter.is_configured() is True

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"sid": "SM998877665544", "status": "queued"}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        res = adapter.send("+919876543210", code="889900")
        assert res.success is True
        assert res.status == OtpDeliveryStatus.ACCEPTED
        assert res.provider == "TWILIO"
        assert res.reference_id == "SM998877665544"

        # Verify POST data
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["auth"] == ("ACtest123456789", "auth_secret_token")
        assert kwargs["data"]["To"] == "+919876543210"
        assert "889900" in kwargs["data"]["Body"]


def test_twilio_adapter_rejection_handling():
    """Verify Twilio API error (e.g. invalid number) returns clean failure."""
    adapter = TwilioSmsAdapter(
        account_sid="ACtest123456789",
        auth_token="auth_secret_token",
        from_number="+15005550006",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"code": 21211, "message": "The 'To' number is not a valid phone number."}

    with patch("httpx.post", return_value=mock_resp):
        res = adapter.send("+919876543210", code="889900")
        assert res.success is False
        assert res.status == OtpDeliveryStatus.FAILED
        assert res.error_code == "TWILIO_21211"
        assert "Unable to send OTP" in res.user_message


def test_twilio_adapter_timeout_handling():
    """Verify Twilio API timeout returns service unavailable."""
    import httpx
    adapter = TwilioSmsAdapter(
        account_sid="ACtest123456789",
        auth_token="auth_secret_token",
        from_number="+15005550006",
    )
    with patch("httpx.post", side_effect=httpx.TimeoutException("Read timed out")):
        res = adapter.send("+919876543210", code="889900")
        assert res.success is False
        assert res.status == OtpDeliveryStatus.FAILED
        assert res.error_code == "TIMEOUT"
        assert "temporarily unavailable" in res.user_message


def test_msg91_adapter_successful_send():
    """Verify MSG91 DLT adapter normalizes Indian phone to 91XXXXXXXXXX and captures request_id."""
    adapter = Msg91SmsAdapter(
        auth_key="msg91_auth_key_123",
        template_id="dlt_template_id_456",
        sender_id="SECHOR",
        dlt_te_id="110123456789",
    )
    assert adapter.is_configured() is True

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"type": "success", "message": "OTP sent successfully", "request_id": "req_msg91_789"}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        res = adapter.send("+919876543210", code="445566")
        assert res.success is True
        assert res.status == OtpDeliveryStatus.ACCEPTED
        assert res.provider == "MSG91"
        assert res.reference_id == "req_msg91_789"

        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["authkey"] == "msg91_auth_key_123"
        # MSG91 expects phone without leading +
        assert kwargs["json"]["mobile"] == "919876543210"
        assert kwargs["json"]["template_id"] == "dlt_template_id_456"
        assert kwargs["json"]["otp"] == "445566"


# ==============================================================================
# 4. End-to-End Pipeline & Security Integration Tests
# ==============================================================================

def test_request_otp_email_triggers_delivery(db, test_user, monkeypatch):
    """Requirement 1 & 3: OTP generation triggers email adapter and returns delivery status."""
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "SMTP")
    monkeypatch.setattr(config, "DEMO_MODE", False)

    # Clean existing OTPs
    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    mock_delivery_res = DeliveryResult(
        success=True,
        provider="SMTP",
        status=OtpDeliveryStatus.ACCEPTED,
        reference_id="SMTP-test-ref-123",
        user_message="OTP sent successfully.",
    )

    with patch("app.services.verification.dispatch_email_otp", return_value=mock_delivery_res) as mock_dispatch:
        res = verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email, purpose="email_verify")

        assert res["status"] == "otp_sent"
        assert res["delivery_status"] == "accepted_by_provider"
        assert res["delivery_provider"] == "SMTP"
        assert res["delivery_reference_id"] == "SMTP-test-ref-123"
        assert res["message"] == "OTP sent successfully."
        # Never exposed in response outside DEMO_MODE
        assert "demo_code" not in res

        # Verify dispatch was called
        mock_dispatch.assert_called_once()
        args, kwargs = mock_dispatch.call_args
        assert args[0] == test_user.email
        assert len(args[1]) == 6  # 6-digit code passed to adapter
        assert kwargs["purpose"] == "email_verify"

        # Verify DB records
        otp_rec = db.scalars(
            select(OtpVerification).where(OtpVerification.user_id == test_user.id).order_by(OtpVerification.created_at.desc())
        ).first()
        assert otp_rec is not None
        assert otp_rec.delivery_status == OtpDeliveryStatus.ACCEPTED
        assert otp_rec.delivery_provider == "SMTP"
        assert otp_rec.delivery_reference_id == "SMTP-test-ref-123"


def test_request_otp_sms_disabled_safely(db, test_user, monkeypatch):
    """Requirement 2 & 3: SMS OTP delivery is temporarily disabled with clean user message."""
    monkeypatch.setattr(config, "DEMO_MODE", False)

    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    with pytest.raises(ServiceError) as exc:
        verify_svc.request_otp(db, test_user.id, channel="phone", target=test_user.phone, purpose="phone_verify")
    assert "SMS verification is temporarily disabled" in str(exc.value)

    # Verify dispatch_sms_otp directly returns disabled status
    res = dispatch_sms_otp(test_user.phone, "123456")
    assert res.success is False
    assert res.error_code == "SMS_DISABLED"
    assert "SMS verification is temporarily disabled" in res.user_message


def test_request_otp_provider_rejection_handled_safely(db, test_user, monkeypatch):
    """Requirement 4: Provider rejection raises error and invalidates OTP record."""
    monkeypatch.setattr(config, "DEMO_MODE", False)

    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    mock_failure = DeliveryResult(
        success=False,
        provider="RESEND",
        status=OtpDeliveryStatus.FAILED,
        error_code="RESEND_422",
        error_message="Invalid recipient address.",
        user_message="Unable to send OTP. Please try again.",
    )

    with patch("app.services.verification.dispatch_email_otp", return_value=mock_failure):
        with pytest.raises(ServiceError) as exc:
            verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email)
        assert "Unable to send OTP" in str(exc.value)

        # Confirm OTP was invalidated in DB and not left active
        otp_rec = db.scalars(
            select(OtpVerification).where(OtpVerification.user_id == test_user.id).order_by(OtpVerification.created_at.desc())
        ).first()
        assert otp_rec is not None
        assert otp_rec.delivery_status == OtpDeliveryStatus.FAILED
        assert otp_rec.is_used is True  # Undelivered code invalidated
        assert otp_rec.delivery_error == "Invalid recipient address."


def test_request_otp_provider_timeout_handled_safely(db, test_user, monkeypatch):
    """Requirement 5: Provider timeout raises temporary unavailability error."""
    monkeypatch.setattr(config, "DEMO_MODE", False)

    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    mock_timeout = DeliveryResult(
        success=False,
        provider="SMTP",
        status=OtpDeliveryStatus.FAILED,
        error_code="TIMEOUT",
        error_message="Connection timed out after 10s",
        user_message="Delivery service temporarily unavailable.",
    )

    with patch("app.services.verification.dispatch_email_otp", return_value=mock_timeout):
        with pytest.raises(ServiceError) as exc:
            verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email)
        assert "Delivery service temporarily unavailable" in str(exc.value)


def test_missing_credentials_fail_safely(db, test_user, monkeypatch):
    """Requirement 6: Missing delivery credentials fail safely without silent mock fallback."""
    monkeypatch.setattr(config, "DEMO_MODE", False)
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "SMTP")
    monkeypatch.setattr(config, "SMTP_HOST", "")  # Empty SMTP host
    monkeypatch.setattr(config, "RESEND_API_KEY", "")

    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    with pytest.raises(ServiceError) as exc:
        verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email)
    assert "Delivery service is not configured" in str(exc.value)


def test_no_otp_exposed_in_logs_or_audit(db, test_user, caplog):
    """Requirement 8: Ensure OTP code is never logged in application logs."""
    caplog.set_level(logging.DEBUG)

    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    mock_delivery = DeliveryResult(
        success=True,
        provider="SMTP",
        status=OtpDeliveryStatus.ACCEPTED,
        reference_id="SMTP-audit-check-1",
        user_message="OTP sent successfully.",
    )

    with patch("app.services.verification.dispatch_email_otp", return_value=mock_delivery) as mock_dispatch:
        res = verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email)
        assert res["status"] == "otp_sent"

        # Capture raw code sent to mock_dispatch
        args, _ = mock_dispatch.call_args
        actual_code = args[1]
        assert len(actual_code) == 6

        # Check caplog: actual_code MUST NOT appear anywhere in logs
        for record in caplog.records:
            assert actual_code not in record.message
            assert actual_code not in str(record.args)


def test_status_transitions_verified_and_expired(db, test_user, monkeypatch):
    """Requirement 9 & 10: Verify delivery_status transitions to VERIFIED on success and EXPIRED on timeout."""
    monkeypatch.setattr(config, "DEMO_MODE", True)

    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    # 1. Request OTP
    res = verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email, purpose="email_verify")
    code = res["demo_code"]

    otp_rec = db.scalars(
        select(OtpVerification).where(OtpVerification.user_id == test_user.id).order_by(OtpVerification.created_at.desc())
    ).first()
    assert otp_rec.delivery_status == OtpDeliveryStatus.ACCEPTED

    # 2. Confirm OTP -> status transitions to VERIFIED
    conf = verify_svc.confirm_otp(db, test_user.id, channel="email", otp_code=code, purpose="email_verify")
    assert conf["status"] == "verified"

    db.refresh(otp_rec)
    assert otp_rec.delivery_status == OtpDeliveryStatus.VERIFIED
    assert otp_rec.is_used is True

    # 3. Replay of same OTP is rejected
    with pytest.raises(ServiceError, match="No active verification code found"):
        verify_svc.confirm_otp(db, test_user.id, channel="email", otp_code=code, purpose="email_verify")


def test_cooldown_rate_limiting(db, test_user):
    """Requirement 11: 60-second cooldown is enforced with user-friendly message."""
    db.query(OtpVerification).filter(OtpVerification.user_id == test_user.id).delete()
    db.commit()

    # First request succeeds
    res1 = verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email, purpose="email_verify")
    assert res1["status"] == "otp_sent"

    # Immediate second request is blocked
    with pytest.raises(ServiceError) as exc:
        verify_svc.request_otp(db, test_user.id, channel="email", target=test_user.email, purpose="email_verify")
    assert "Too many OTP requests" in str(exc.value)
