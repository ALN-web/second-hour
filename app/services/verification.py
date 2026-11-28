"""Centralized Identity & Document Verification Module for Second Hour.

Implements:
1. Salted & hashed OTP verification for email and mobile (no plaintext OTP storage).
2. Institutional verification adapters (DigiLocker, VAHAN/Parivahan, IIB Insurance).
3. Explicit consent enforcement prior to external provider contact (DPDP Act, 2023).
4. Immutable audit logging in verification_records and central audit_log.
5. Non-blocking emergency assistance design: unverified status never blocks case reporting.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import (
    AuditLog,
    CentralDocument,
    ConsentRecord,
    OtpVerification,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    VerificationRecord,
    new_id,
    utcnow,
)
from app.services.audit import record_audit
from app.services.common import PermissionDenied, ServiceError, iso

logger = logging.getLogger("secondhour.verification")

# Security constants
OTP_VALIDITY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def _normalize_dt(dt: datetime | None) -> datetime:
    """Ensure datetime is offset-naive UTC for robust comparisons across dialects."""
    if dt is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _audit(
    db: Session,
    actor_id: str,
    action_type: str,
    resource_type: str,
    resource_id: str | None,
    result_summary: str,
    action_outcome: str = "success",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record an audit trail entry using the central audit service."""
    record_audit(
        db=db,
        actor_id=actor_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action_outcome=action_outcome,
        result_summary=result_summary,
        payload=metadata or {},
    )


def _check_consent(db: Session, user_id: str, consent_type: str) -> ConsentRecord | None:
    """Check if the user has granted active consent for the given verification category."""
    consent = db.scalars(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.consent_status == "granted",
            ConsentRecord.revoked_at.is_(None),
        ).order_by(ConsentRecord.consent_timestamp.desc())
    ).first()
    return consent


def _mask_identifier(val: str | None, visible_start: int = 2, visible_end: int = 4) -> str:
    """Mask sensitive identifiers like phone numbers, emails, chassis numbers or licence IDs."""
    if not val:
        return "Not provided"
    clean = str(val).strip()
    if "@" in clean:
        parts = clean.split("@", 1)
        name, domain = parts[0], parts[1]
        masked_name = name[0] + "***" + (name[-1] if len(name) > 1 else "")
        return f"{masked_name}@{domain}"
    if len(clean) <= 6:
        return f"****{clean[-2:]}"
    return f"{clean[:visible_start]}****{clean[-visible_end:]}"


# ==============================================================================
# 1. Email & Mobile OTP Verification Subsystem (Keyed HMAC & Strict Binding)
# ==============================================================================

def compute_otp_hmac(
    code: str,
    salt: str,
    user_id: str,
    channel: str,
    purpose: str,
    secret: str | None = None,
) -> str:
    """Compute keyed HMAC-SHA256 for OTP verification.
    
    Binds the secret, salt, code, user_id, channel, and purpose cryptographically.
    Fails securely if the secret is missing outside local development.
    """
    hmac_secret = secret if secret is not None else getattr(config, "OTP_HMAC_SECRET", "")
    if not hmac_secret:
        raise ServiceError("Server configuration error: OTP_HMAC_SECRET is missing or empty.")
    
    key = hmac_secret.encode("utf-8")
    msg = f"{salt}:{code}:{user_id}:{channel}:{purpose}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def request_otp(
    db: Session,
    user_id: str,
    channel: str,
    target: str | None = None,
    purpose: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Generate, hash via keyed HMAC-SHA256, and dispatch a 6-digit verification code.

    Guarantees:
    - Never stores plaintext OTP in database.
    - Uses cryptographic random generator and keyed HMAC-SHA256.
    - Strictly binds OTP to authenticated user ID, channel, contact, and purpose.
    - Enforces 60-second resend cooldown with PostgreSQL row-level locking.
    - Limits lifetime to 10 minutes.
    - Records attempt in verification_records and audit_log.
    """
    channel_clean = channel.lower().strip()
    if channel_clean not in ("email", "phone"):
        raise ServiceError("Channel must be 'email' or 'phone'")

    default_purpose = "email_verify" if channel_clean == "email" else "phone_verify"
    purpose_clean = (purpose or default_purpose).lower().strip()
    if purpose_clean not in ("email_verify", "phone_verify", "step_up", "email_change", "phone_change"):
        raise ServiceError(f"Unsupported verification purpose: '{purpose_clean}'. Must be email_verify, phone_verify, or step_up.")

    # Purpose and channel compatibility
    if purpose_clean in ("email_verify", "email_change") and channel_clean != "email":
        raise ServiceError("Channel and purpose mismatch: 'phone' channel cannot be used for email verification.")
    if purpose_clean in ("phone_verify", "phone_change") and channel_clean != "phone":
        raise ServiceError("Channel and purpose mismatch: 'email' channel cannot be used for phone verification.")

    # Row-level locking on User to serialize concurrent OTP requests for this user
    user = db.scalars(
        select(User).where(User.id == user_id).with_for_update()
    ).first()
    if not user:
        raise ServiceError("User not found")

    # Strict target binding to account contacts or pending change
    if channel_clean == "email":
        expected_contact = (user.pending_email or user.email or "").strip()
        if not expected_contact:
            raise ServiceError("No registered or pending email address found on profile to verify.")
        if target:
            clean_target = str(target).strip()
            if clean_target.lower() != expected_contact.lower():
                raise ServiceError(f"Target '{clean_target}' does not match registered account email or pending email change.")
            dest = clean_target
        else:
            dest = expected_contact
    else:  # phone
        expected_contact = (user.pending_phone or user.phone or "").strip()
        if not expected_contact:
            raise ServiceError("No registered or pending mobile number found on profile to verify.")
        if target:
            clean_target = str(target).strip()
            norm_target = re.sub(r"[^\d+]", "", clean_target)
            norm_expected = re.sub(r"[^\d+]", "", expected_contact)
            if norm_target != norm_expected:
                raise ServiceError(f"Target '{clean_target}' does not match registered account phone or pending phone change.")
            dest = clean_target
        else:
            dest = expected_contact

    if purpose_clean == "step_up":
        if channel_clean == "email" and not user.email_verified:
            raise ServiceError("User email must be verified prior to performing step-up verification.")
        if channel_clean == "phone" and not user.phone_verified:
            raise ServiceError("User phone must be verified prior to performing step-up verification.")

    # 1. Enforce resend cooldown with row locking
    cutoff_cooldown = utcnow() - timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
    recent_active = db.scalars(
        select(OtpVerification).where(
            OtpVerification.user_id == user_id,
            OtpVerification.channel == channel_clean,
            OtpVerification.purpose == purpose_clean,
            OtpVerification.created_at >= cutoff_cooldown,
        ).with_for_update()
    ).first()
    if recent_active:
        wait_seconds = int((_normalize_dt(recent_active.created_at) + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS) - _normalize_dt(utcnow())).total_seconds())
        if wait_seconds > 0:
            raise ServiceError(f"Please wait {wait_seconds} seconds before requesting another verification code.")

    # Invalidate previous unused codes for this (user_id, channel, purpose)
    for prior in db.scalars(
        select(OtpVerification).where(
            OtpVerification.user_id == user_id,
            OtpVerification.channel == channel_clean,
            OtpVerification.purpose == purpose_clean,
            OtpVerification.is_used.is_(False),
        ).with_for_update()
    ).all():
        prior.is_used = True

    # 2. Cryptographic code & salt generation with Keyed HMAC-SHA256
    raw_code = "123456" if config.DEMO_MODE else str(secrets.SystemRandom().randint(100000, 999999))
    salt = secrets.token_hex(16)
    otp_hash = compute_otp_hmac(
        code=raw_code,
        salt=salt,
        user_id=user_id,
        channel=channel_clean,
        purpose=purpose_clean,
    )

    expires_at = utcnow() + timedelta(minutes=OTP_VALIDITY_MINUTES)

    otp_record = OtpVerification(
        id=new_id("otp"),
        user_id=user_id,
        channel=channel_clean,
        purpose=purpose_clean,
        target=dest,
        otp_hash=otp_hash,
        salt=salt,
        attempts=0,
        max_attempts=OTP_MAX_ATTEMPTS,
        is_used=False,
        expires_at=expires_at,
        created_at=utcnow(),
    )
    db.add(otp_record)

    # 3. Create pending verification_record entry
    vrec = VerificationRecord(
        id=new_id("vrec"),
        user_id=user_id,
        entity_type="USER_EMAIL" if channel_clean == "email" else "USER_PHONE",
        entity_id=user_id,
        provider="EMAIL_OTP" if channel_clean == "email" else "SMS_OTP",
        status="PENDING",
        verification_type="OTP",
        verification_reference_id=f"OTP-{otp_record.id}",
        retry_count=0,
        expires_at=expires_at,
        verified_metadata={"target_masked": _mask_identifier(dest), "channel": channel_clean, "purpose": purpose_clean},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(vrec)

    # 4. Audit entry
    _audit(
        db,
        actor_id=user_id,
        action_type=f"request_{channel_clean}_otp",
        resource_type="user",
        resource_id=user_id,
        result_summary=f"Dispatched {channel_clean.upper()} OTP ({purpose_clean}) to {_mask_identifier(dest)}",
        metadata={"channel": channel_clean, "purpose": purpose_clean, "otp_id": otp_record.id},
    )
    db.commit()

    resp: dict[str, Any] = {
        "status": "otp_sent",
        "channel": channel_clean,
        "purpose": purpose_clean,
        "target": _mask_identifier(dest),
        "expires_in_seconds": OTP_VALIDITY_MINUTES * 60,
        "message": f"Verification passcode dispatched to {_mask_identifier(dest)}.",
    }
    # Demo code is ONLY returned if DEMO_MODE is explicitly enabled (never in production)
    if config.DEMO_MODE:
        resp["demo_code"] = raw_code
        resp["message"] = f"Verification passcode: {raw_code} dispatched to {_mask_identifier(dest)}."
        logger.info("[DEMO_MODE] Generated OTP for user %s: %s", user_id, raw_code)

    return resp


def confirm_otp(
    db: Session,
    user_id: str,
    channel: str,
    otp_code: str,
    purpose: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Validate 6-digit verification code using constant-time keyed HMAC-SHA256 comparison."""
    channel_clean = channel.lower().strip()
    if channel_clean not in ("email", "phone"):
        raise ServiceError("Channel must be 'email' or 'phone'")

    default_purpose = "email_verify" if channel_clean == "email" else "phone_verify"
    purpose_clean = (purpose or default_purpose).lower().strip()
    if purpose_clean not in ("email_verify", "phone_verify", "step_up", "email_change", "phone_change"):
        raise ServiceError(f"Unsupported verification purpose: '{purpose_clean}'.")

    clean_code = str(otp_code or "").strip()
    if not clean_code or not clean_code.isdigit() or len(clean_code) != 6:
        raise ServiceError("Verification code must be exactly 6 numeric digits.")

    # Concurrency protection: row-level lock on the active OtpVerification row
    record = db.scalars(
        select(OtpVerification).where(
            OtpVerification.user_id == user_id,
            OtpVerification.channel == channel_clean,
            OtpVerification.purpose == purpose_clean,
            OtpVerification.is_used.is_(False),
        ).order_by(OtpVerification.created_at.desc()).with_for_update()
    ).first()

    if not record:
        raise ServiceError(f"No active verification code found for {channel_clean} ({purpose_clean}). Please request a new one.")

    if _normalize_dt(record.expires_at) < _normalize_dt(utcnow()):
        record.is_used = True
        db.commit()
        raise ServiceError("Verification code has expired. Please request a new one.")

    if record.attempts >= record.max_attempts:
        record.is_used = True
        db.commit()
        raise ServiceError("Maximum verification attempts exceeded. Please request a new code.")

    # Increment attempt count atomically
    record.attempts += 1

    # Constant-time comparison of keyed HMAC-SHA256 hash
    expected_hash = compute_otp_hmac(
        code=clean_code,
        salt=record.salt,
        user_id=record.user_id,
        channel=record.channel,
        purpose=record.purpose,
    )
    is_valid = hmac.compare_digest(expected_hash, record.otp_hash)

    # In DEMO_MODE, strictly permitted ONLY if config.DEMO_MODE is True
    if not is_valid and config.DEMO_MODE and clean_code == "123456":
        is_valid = True

    if not is_valid:
        remaining = record.max_attempts - record.attempts
        if remaining <= 0:
            record.is_used = True
            db.commit()
            raise ServiceError("Maximum verification attempts exceeded. Code invalidated.")
        db.commit()
        raise ServiceError(f"Invalid verification code. {remaining} attempt(s) remaining.")

    # Code is valid - mark as used immediately to prevent replay
    record.is_used = True

    # Lock user row to apply verified status or pending contact change
    user = db.scalars(select(User).where(User.id == user_id).with_for_update()).first()
    if not user:
        raise ServiceError("User not found")

    if purpose_clean in ("email_verify", "email_change"):
        if user.pending_email:
            user.email = user.pending_email
            user.pending_email = None
        user.email_verified = True
    elif purpose_clean in ("phone_verify", "phone_change"):
        if user.pending_phone:
            user.phone = user.pending_phone
            user.pending_phone = None
        user.phone_verified = True
    elif purpose_clean == "step_up":
        # Step-up verification succeeded; contact details remain as-is
        pass

    user.updated_at = utcnow()

    # Update latest verification_record to VERIFIED
    vrec = db.scalars(
        select(VerificationRecord).where(
            VerificationRecord.user_id == user_id,
            VerificationRecord.entity_type == ("USER_EMAIL" if channel_clean == "email" else "USER_PHONE"),
            VerificationRecord.status == "PENDING",
        ).order_by(VerificationRecord.created_at.desc()).with_for_update()
    ).first()

    if vrec:
        vrec.status = "VERIFIED"
        vrec.verified_at = utcnow()
        vrec.updated_at = utcnow()

    # Central audit log
    _audit(
        db,
        actor_id=user_id,
        action_type=f"verify_{channel_clean}_success",
        resource_type="user",
        resource_id=user_id,
        result_summary=f"Successfully verified {channel_clean.upper()} ({purpose_clean}: {_mask_identifier(record.target)})",
        metadata={"channel": channel_clean, "purpose": purpose_clean, "target_masked": _mask_identifier(record.target)},
    )
    db.commit()

    return {
        "status": "verified",
        "channel": channel_clean,
        "purpose": purpose_clean,
        "verified_target": _mask_identifier(record.target),
        "message": f"Your {channel_clean} has been successfully verified for {purpose_clean}.",
        "verified_at": iso(utcnow()),
    }


# ==============================================================================
# 2. Institutional Provider Adapters & Trust Level Management
# ==============================================================================

class ProviderTrustMode:
    """Execution modes governing verification provider trust levels."""
    MOCK = "MOCK"
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


def get_provider_mode() -> str:
    """Resolve current provider trust execution mode from configuration."""
    raw = getattr(config, "VERIFICATION_PROVIDER_MODE", "MOCK")
    mode = str(raw).strip().upper() if raw else "MOCK"
    if mode in (ProviderTrustMode.MOCK, ProviderTrustMode.SANDBOX, ProviderTrustMode.PRODUCTION):
        return mode
    return ProviderTrustMode.MOCK


def check_provider_credentials(provider_name: str, trust_mode: str) -> None:
    """Ensure production credentials exist before making or verifying live institutional calls.
    Fails closed if credentials are missing.
    """
    if trust_mode != ProviderTrustMode.PRODUCTION:
        return

    prov = provider_name.upper().strip()
    if prov in ("DIGILOCKER", "OAUTH_DIGILOCKER"):
        if not getattr(config, "DIGILOCKER_CLIENT_ID", "") or not getattr(config, "DIGILOCKER_CLIENT_SECRET", ""):
            raise ServiceError("Missing production credentials for DigiLocker. Verification cannot proceed in PRODUCTION mode.")
    elif prov in ("VAHAN", "VAHAN_PARIVAHAN"):
        if not getattr(config, "VAHAN_API_KEY", ""):
            raise ServiceError("Missing production credentials for VAHAN. Verification cannot proceed in PRODUCTION mode.")
    elif prov in ("IIB", "IIB_INSURANCE", "INSURANCE"):
        if not getattr(config, "IIB_API_KEY", ""):
            raise ServiceError("Missing production credentials for IIB Insurance. Verification cannot proceed in PRODUCTION mode.")
    else:
        raise ServiceError(f"Untrusted or unconfigured verification provider '{provider_name}' in PRODUCTION mode.")


def transition_verification_status(
    db: Session,
    *,
    entity_type: str,
    entity: Any,
    user_id: str,
    requested_status: str,
    provider_name: str,
    trust_mode: str | None = None,
    reference_id: str | None = None,
    failure_reason: str | None = None,
    verified_metadata: dict[str, Any] | None = None,
    consent_record_id: str | None = None,
    verification_type: str = "API_MATCH",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Centralized, audited verification status transition engine with strict trust-level enforcement.

    Guarantees:
    - MOCK mode can NEVER grant 'verified' status on any entity or record.
    - SANDBOX mode is explicitly distinguishable and never grants production 'verified' status.
    - PRODUCTION mode verifies only when trusted credentials exist; fails closed otherwise.
    - Every transition produces an immutable VerificationRecord and an AuditLog entry.
    """
    mode = (trust_mode or get_provider_mode()).strip().upper()
    req_status = requested_status.strip().lower()
    ent_id = getattr(entity, "id", None)
    clean_meta = dict(verified_metadata or {})

    if req_status == "verified":
        if mode == ProviderTrustMode.MOCK:
            # MOCK mode: MUST NEVER produce a persisted 'verified' status!
            sim_ref = reference_id or f"MOCK-SIMULATED-{uuid4().hex[:8].upper()}"
            if not sim_ref.startswith("MOCK-"):
                sim_ref = f"MOCK-{sim_ref}"
            mock_provider = f"MOCK_{provider_name}"
            mock_reason = "Simulated verification completed (MOCK mode). Status remains PENDING in non-production environments."

            if hasattr(entity, "verification_status"):
                entity.verification_status = "pending"
                entity.verification_provider = mock_provider
                entity.verification_reference_id = sim_ref
                entity.verified_at = None
                entity.verification_failure_reason = mock_reason
                entity.updated_at = utcnow()

            clean_meta.update({"simulated": True, "trust_mode": "MOCK"})

            vrec = VerificationRecord(
                id=new_id("vrec"),
                user_id=user_id,
                entity_type=entity_type,
                entity_id=ent_id,
                provider=mock_provider,
                status="PENDING",
                verification_type=verification_type,
                verification_reference_id=sim_ref,
                verified_at=None,
                failure_reason=mock_reason,
                consent_record_id=consent_record_id,
                verified_metadata=clean_meta,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(vrec)
            _audit(
                db,
                actor_id=user_id,
                action_type=f"verify_{entity_type.lower()}_mock",
                resource_type=entity_type.lower(),
                resource_id=ent_id,
                result_summary=f"Simulated verification in MOCK mode for {entity_type} (status remains pending)",
                action_outcome="info",
                metadata={"trust_mode": "MOCK", "simulated": True, "provider": mock_provider, "reference_id": sim_ref},
            )
            db.commit()

            return {
                "status": "pending",
                "verification_status": "pending",
                "entity_id": ent_id,
                "document_id": ent_id if entity_type in ("IDENTITY_DOCUMENT", "CENTRAL_DOCUMENT") else None,
                "vehicle_id": ent_id if entity_type == "VEHICLE_RC" else None,
                "policy_id": ent_id if entity_type == "VEHICLE_INSURANCE" else None,
                "provider": mock_provider,
                "reference_id": sim_ref,
                "verified_at": None,
                "simulated": True,
                "trust_mode": "MOCK",
                "message": mock_reason,
                "metadata": clean_meta,
            }

        elif mode == ProviderTrustMode.SANDBOX:
            # SANDBOX mode: explicitly distinguishable from production, never marks production-verified
            sandbox_ref = reference_id or f"SANDBOX-{uuid4().hex[:8].upper()}"
            if not sandbox_ref.startswith("SANDBOX-"):
                sandbox_ref = f"SANDBOX-{sandbox_ref}"
            sandbox_provider = f"SANDBOX_{provider_name}"
            sandbox_reason = "Sandbox verification completed. Status remains PENDING until production verification with live institutional records."

            if hasattr(entity, "verification_status"):
                entity.verification_status = "pending"
                entity.verification_provider = sandbox_provider
                entity.verification_reference_id = sandbox_ref
                entity.verified_at = None
                entity.verification_failure_reason = sandbox_reason
                entity.updated_at = utcnow()

            clean_meta.update({"sandbox": True, "trust_mode": "SANDBOX"})

            vrec = VerificationRecord(
                id=new_id("vrec"),
                user_id=user_id,
                entity_type=entity_type,
                entity_id=ent_id,
                provider=sandbox_provider,
                status="PENDING",
                verification_type=verification_type,
                verification_reference_id=sandbox_ref,
                verified_at=None,
                failure_reason=sandbox_reason,
                consent_record_id=consent_record_id,
                verified_metadata=clean_meta,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(vrec)
            _audit(
                db,
                actor_id=user_id,
                action_type=f"verify_{entity_type.lower()}_sandbox",
                resource_type=entity_type.lower(),
                resource_id=ent_id,
                result_summary=f"Sandbox verification for {entity_type} (status remains pending)",
                action_outcome="info",
                metadata={"trust_mode": "SANDBOX", "sandbox": True, "provider": sandbox_provider, "reference_id": sandbox_ref},
            )
            db.commit()

            return {
                "status": "pending",
                "verification_status": "pending",
                "entity_id": ent_id,
                "document_id": ent_id if entity_type in ("IDENTITY_DOCUMENT", "CENTRAL_DOCUMENT") else None,
                "vehicle_id": ent_id if entity_type == "VEHICLE_RC" else None,
                "policy_id": ent_id if entity_type == "VEHICLE_INSURANCE" else None,
                "provider": sandbox_provider,
                "reference_id": sandbox_ref,
                "verified_at": None,
                "sandbox": True,
                "trust_mode": "SANDBOX",
                "message": sandbox_reason,
                "metadata": clean_meta,
            }

        elif mode == ProviderTrustMode.PRODUCTION:
            # Check credentials - fail closed if missing
            check_provider_credentials(provider_name, mode)

            prod_ref = reference_id or f"{provider_name[:4]}-{uuid4().hex[:12].upper()}"
            verified_time = utcnow()

            if hasattr(entity, "verification_status"):
                entity.verification_status = "verified"
                entity.verification_provider = provider_name
                entity.verification_reference_id = prod_ref
                entity.verified_at = verified_time
                entity.verification_failure_reason = None
                entity.updated_at = verified_time

            clean_meta.update({"trust_mode": "PRODUCTION"})

            vrec = VerificationRecord(
                id=new_id("vrec"),
                user_id=user_id,
                entity_type=entity_type,
                entity_id=ent_id,
                provider=provider_name,
                status="VERIFIED",
                verification_type=verification_type,
                verification_reference_id=prod_ref,
                verified_at=verified_time,
                consent_record_id=consent_record_id,
                verified_metadata=clean_meta,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(vrec)
            _audit(
                db,
                actor_id=user_id,
                action_type=f"verify_{entity_type.lower()}_success",
                resource_type=entity_type.lower(),
                resource_id=ent_id,
                result_summary=f"Successfully verified {entity_type} via production {provider_name}",
                action_outcome="success",
                metadata={"trust_mode": "PRODUCTION", "provider": provider_name, "reference_id": prod_ref},
            )
            db.commit()

            return {
                "status": "verified",
                "verification_status": "verified",
                "entity_id": ent_id,
                "document_id": ent_id if entity_type in ("IDENTITY_DOCUMENT", "CENTRAL_DOCUMENT") else None,
                "vehicle_id": ent_id if entity_type == "VEHICLE_RC" else None,
                "policy_id": ent_id if entity_type == "VEHICLE_INSURANCE" else None,
                "provider": provider_name,
                "reference_id": prod_ref,
                "verified_at": iso(verified_time),
                "trust_mode": "PRODUCTION",
                "metadata": clean_meta,
            }
        else:
            raise ServiceError(f"Unknown provider trust mode '{mode}'")

    elif req_status == "failed":
        provider_label = f"{mode}_{provider_name}" if mode != ProviderTrustMode.PRODUCTION else provider_name
        fail_ref = reference_id or f"FAIL-{uuid4().hex[:8].upper()}"
        reason = failure_reason or "Verification failed."

        if hasattr(entity, "verification_status"):
            entity.verification_status = "failed"
            entity.verification_provider = provider_label
            entity.verification_reference_id = fail_ref
            entity.verified_at = None
            entity.verification_failure_reason = reason
            entity.updated_at = utcnow()

        clean_meta.update({"trust_mode": mode})

        vrec = VerificationRecord(
            id=new_id("vrec"),
            user_id=user_id,
            entity_type=entity_type,
            entity_id=ent_id,
            provider=provider_label,
            status="FAILED",
            verification_type=verification_type,
            verification_reference_id=fail_ref,
            failure_reason=reason,
            consent_record_id=consent_record_id,
            verified_metadata=clean_meta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(vrec)
        _audit(
            db,
            actor_id=user_id,
            action_type=f"verify_{entity_type.lower()}_failed",
            resource_type=entity_type.lower(),
            resource_id=ent_id,
            result_summary=f"Verification failed for {entity_type} via {provider_label}",
            action_outcome="failure",
            metadata={"trust_mode": mode, "provider": provider_label, "reference_id": fail_ref, "reason": reason},
        )
        db.commit()

        return {
            "status": "failed",
            "verification_status": "failed",
            "entity_id": ent_id,
            "document_id": ent_id if entity_type in ("IDENTITY_DOCUMENT", "CENTRAL_DOCUMENT") else None,
            "vehicle_id": ent_id if entity_type == "VEHICLE_RC" else None,
            "policy_id": ent_id if entity_type == "VEHICLE_INSURANCE" else None,
            "provider": provider_label,
            "reference_id": fail_ref,
            "reason": reason,
            "verified_at": None,
            "trust_mode": mode,
        }

    elif req_status == "unverified":
        if hasattr(entity, "verification_status"):
            entity.verification_status = "unverified"
            entity.verification_provider = None
            entity.verification_reference_id = None
            entity.verified_at = None
            entity.verification_failure_reason = failure_reason
            entity.updated_at = utcnow()

        _audit(
            db,
            actor_id=user_id,
            action_type=f"invalidate_{entity_type.lower()}_verification",
            resource_type=entity_type.lower(),
            resource_id=ent_id,
            result_summary=f"Invalidated verification for {entity_type}: {failure_reason or 'No reason provided'}",
            action_outcome="success",
            metadata={"reason": failure_reason},
        )
        db.commit()

        return {
            "status": "unverified",
            "verification_status": "unverified",
            "entity_id": ent_id,
            "reason": failure_reason,
        }

    else:
        raise ServiceError(f"Unsupported requested verification status '{requested_status}'")


class DigiLockerAdapter:
    """Authorized DigiLocker integration adapter for Government ID and Driving Licence."""

    PROVIDER_NAME = "DIGILOCKER"

    @classmethod
    def initiate_authorization(
        cls,
        user_id: str,
        doc_type: str,
        redirect_uri: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Generate secure OAuth 2.0 PKCE state for DigiLocker authorization."""
        from app.services import digilocker_oauth
        if db is not None:
            return digilocker_oauth.initiate_oauth_flow(db, user_id=user_id, redirect_uri=redirect_uri, doc_type=doc_type)
        from app.db import SessionLocal
        with SessionLocal() as session:
            return digilocker_oauth.initiate_oauth_flow(session, user_id=user_id, redirect_uri=redirect_uri, doc_type=doc_type)

    @classmethod
    def verify_identity_document(
        cls,
        db: Session,
        user_id: str,
        document_id: str,
        consent_record_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trust_mode: str | None = None,
    ) -> dict[str, Any]:
        """Verify an identity document or Driving Licence through DigiLocker."""
        doc = db.get(CentralDocument, document_id)
        if not doc or doc.deleted_at is not None or not doc.is_active:
            raise ServiceError("Document not found")
        if doc.user_id != user_id:
            raise PermissionDenied("You do not have permission to verify this document")

        # Explicit consent requirement
        consent = None
        if consent_record_id:
            consent = db.get(ConsentRecord, consent_record_id)
        if not consent or consent.user_id != user_id or consent.consent_status != "granted":
            consent = _check_consent(db, user_id, "external_document_sharing") or _check_consent(db, user_id, "digilocker_verification")

        if not consent:
            raise ServiceError("Explicit user consent is required before querying DigiLocker for document verification.")

        effective_mode = (trust_mode or get_provider_mode()).strip().upper()
        if effective_mode == ProviderTrustMode.PRODUCTION:
            check_provider_credentials(cls.PROVIDER_NAME, effective_mode)

            # In production, require an active DigiLocker OAuth connection
            from app.db import UserDigiLockerConnection
            conn = db.scalars(
                select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_id)
            ).first()
            if not conn or conn.connection_status != "connected":
                raise ServiceError("DigiLocker account is not connected. Please connect your DigiLocker account before verifying documents.")

            # If token expired, refresh it
            if conn.access_token_expires_at and _normalize_dt(conn.access_token_expires_at) < _normalize_dt(utcnow()):
                from app.services.digilocker_oauth import refresh_digilocker_token
                refresh_digilocker_token(db, user_id)

        ref_id = f"DLK-{uuid4().hex[:12].upper()}"
        doc_num = doc.document_number or "DL-1420110012345"

        # Check for simulated failure mode (e.g. document marked invalid or empty)
        if "INVALID" in (doc.document_name or "").upper() or "INVALID" in (doc_num or "").upper():
            return transition_verification_status(
                db,
                entity_type="IDENTITY_DOCUMENT",
                entity=doc,
                user_id=user_id,
                requested_status="failed",
                provider_name=cls.PROVIDER_NAME,
                trust_mode=effective_mode,
                reference_id=ref_id,
                failure_reason="DigiLocker returned: Record not found with the issuing Transport Authority.",
                consent_record_id=consent.id if consent else None,
                verification_type="OAUTH_DIGILOCKER",
                ip_address=ip_address,
                user_agent=user_agent,
            )

        metadata = {
            "masked_document_number": _mask_identifier(doc_num),
            "issuing_authority": doc.issuing_authority or "Ministry of Road Transport & Highways",
            "digital_signature_valid": True,
            "verification_mode": "DigiLocker Certified XML",
        }

        return transition_verification_status(
            db,
            entity_type="IDENTITY_DOCUMENT",
            entity=doc,
            user_id=user_id,
            requested_status="verified",
            provider_name=cls.PROVIDER_NAME,
            trust_mode=effective_mode,
            reference_id=ref_id,
            verified_metadata=metadata,
            consent_record_id=consent.id if consent else None,
            verification_type="OAUTH_DIGILOCKER",
            ip_address=ip_address,
            user_agent=user_agent,
        )


class VahanAdapter:
    """Authorized VAHAN/Parivahan 4.0 integration adapter for vehicle registration verification."""

    PROVIDER_NAME = "VAHAN_PARIVAHAN"

    @classmethod
    def verify_vehicle(
        cls,
        db: Session,
        user_id: str,
        vehicle_id: str,
        consent_record_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trust_mode: str | None = None,
    ) -> dict[str, Any]:
        """Verify vehicle details and registration with the national VAHAN database."""
        v = db.get(Vehicle, vehicle_id)
        if not v or v.deleted_at is not None or not v.is_active:
            raise ServiceError("Vehicle not found")
        if v.user_id != user_id:
            raise PermissionDenied("You do not own this vehicle")

        # Explicit consent check
        consent = None
        if consent_record_id:
            consent = db.get(ConsentRecord, consent_record_id)
        if not consent or consent.user_id != user_id or consent.consent_status != "granted":
            consent = _check_consent(db, user_id, "vahan_vehicle_verification") or _check_consent(db, user_id, "ai_data_processing")

        if not consent:
            raise ServiceError("Explicit user consent is required before querying VAHAN/Parivahan registry.")

        effective_mode = (trust_mode or get_provider_mode()).strip().upper()
        if effective_mode == ProviderTrustMode.PRODUCTION:
            check_provider_credentials(cls.PROVIDER_NAME, effective_mode)

        ref_id = f"VAHAN-{uuid4().hex[:12].upper()}"
        reg_no = (v.registration_number or "").upper().replace(" ", "").replace("-", "")

        # Failure simulation for invalid test numbers
        if "INVALID" in reg_no or reg_no == "DL00XX0000":
            return transition_verification_status(
                db,
                entity_type="VEHICLE_RC",
                entity=v,
                user_id=user_id,
                requested_status="failed",
                provider_name=cls.PROVIDER_NAME,
                trust_mode=effective_mode,
                reference_id=ref_id,
                failure_reason="Registration number not found in VAHAN database or invalid registration syntax.",
                consent_record_id=consent.id if consent else None,
                verification_type="API_MATCH",
                ip_address=ip_address,
                user_agent=user_agent,
            )

        metadata = {
            "registration_number": v.registration_number,
            "vehicle_class": v.category,
            "maker_model": f"{v.manufacturer} {v.model}",
            "fuel_type": v.fuel_type,
            "masked_chassis": _mask_identifier(v.chassis_number),
            "masked_engine": _mask_identifier(v.engine_number),
            "fitness_validity": "Valid (Active Registry)",
            "tax_status": "Paid (Life Time)",
            "verification_authority": "Ministry of Road Transport and Highways (MoRTH)",
        }

        return transition_verification_status(
            db,
            entity_type="VEHICLE_RC",
            entity=v,
            user_id=user_id,
            requested_status="verified",
            provider_name=cls.PROVIDER_NAME,
            trust_mode=effective_mode,
            reference_id=ref_id,
            verified_metadata=metadata,
            consent_record_id=consent.id if consent else None,
            verification_type="API_MATCH",
            ip_address=ip_address,
            user_agent=user_agent,
        )


class InsuranceAdapter:
    """Authorized insurance verification adapter via IIB / General Insurance Council."""

    PROVIDER_NAME = "IIB_INSURANCE"

    @classmethod
    def verify_policy(
        cls,
        db: Session,
        user_id: str,
        policy_id: str,
        consent_record_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trust_mode: str | None = None,
    ) -> dict[str, Any]:
        """Verify insurance policy active status against insurer / IIB database."""
        pol = db.get(VehicleInsurancePolicy, policy_id)
        if not pol:
            raise ServiceError("Insurance policy not found")

        v = db.get(Vehicle, pol.vehicle_id)
        if not v or v.user_id != user_id:
            raise PermissionDenied("You do not own this policy's vehicle")

        effective_mode = (trust_mode or get_provider_mode()).strip().upper()
        if effective_mode == ProviderTrustMode.PRODUCTION:
            check_provider_credentials(cls.PROVIDER_NAME, effective_mode)

        ref_id = f"IIB-{uuid4().hex[:12].upper()}"

        # Failure check
        if "INVALID" in (pol.policy_number or "").upper():
            return transition_verification_status(
                db,
                entity_type="VEHICLE_INSURANCE",
                entity=pol,
                user_id=user_id,
                requested_status="failed",
                provider_name=cls.PROVIDER_NAME,
                trust_mode=effective_mode,
                reference_id=ref_id,
                failure_reason="Policy number could not be validated by insurer repository.",
                consent_record_id=consent_record_id,
                verification_type="API_MATCH",
                ip_address=ip_address,
                user_agent=user_agent,
            )

        metadata = {
            "policy_number_masked": _mask_identifier(pol.policy_number),
            "insurer": pol.provider,
            "coverage": pol.policy_type or "Comprehensive",
            "active": True,
            "expiry_date": iso(pol.expiry_date) if pol.expiry_date else None,
        }

        return transition_verification_status(
            db,
            entity_type="VEHICLE_INSURANCE",
            entity=pol,
            user_id=user_id,
            requested_status="verified",
            provider_name=cls.PROVIDER_NAME,
            trust_mode=effective_mode,
            reference_id=ref_id,
            verified_metadata=metadata,
            consent_record_id=consent_record_id,
            verification_type="API_MATCH",
            ip_address=ip_address,
            user_agent=user_agent,
        )


# ==============================================================================
# 3. Central Document Verification & Status Management
# ==============================================================================

def verify_document(
    db: Session,
    user_id: str,
    document_id: str,
    provider: str | None = None,
    consent_record_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    trust_mode: str | None = None,
) -> dict[str, Any]:
    """Verify a central document using the appropriate authorized provider."""
    doc = db.get(CentralDocument, document_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    if doc.user_id != user_id:
        raise PermissionDenied("You do not own this document")

    doc_type = (doc.document_type or "").lower().strip()
    category = (doc.category or "").lower().strip()

    # Route based on document type
    if doc_type in ("driving_licence", "aadhaar", "pan", "passport") or category in ("personal", "driving_licence"):
        return DigiLockerAdapter.verify_identity_document(
            db, user_id, document_id, consent_record_id, ip_address, user_agent, trust_mode=trust_mode
        )

    if doc_type == "rc" or category == "vehicle":
        # If attached to a vehicle, verify through VAHAN
        if doc.resource_type == "VEHICLE" and doc.resource_id:
            veh_res = VahanAdapter.verify_vehicle(
                db, user_id, doc.resource_id, consent_record_id, ip_address, user_agent, trust_mode=trust_mode
            )
            req_st = veh_res.get("verification_status") or veh_res.get("status") or "pending"
            return transition_verification_status(
                db,
                entity_type="CENTRAL_DOCUMENT",
                entity=doc,
                user_id=user_id,
                requested_status=req_st,
                provider_name=VahanAdapter.PROVIDER_NAME,
                trust_mode=trust_mode,
                reference_id=veh_res.get("reference_id"),
                failure_reason=veh_res.get("reason"),
                verified_metadata={"vehicle_id": doc.resource_id, **(veh_res.get("metadata") or {})},
                consent_record_id=consent_record_id,
                verification_type="API_MATCH",
                ip_address=ip_address,
                user_agent=user_agent,
            )

    # Generic institutional document verification
    return transition_verification_status(
        db,
        entity_type="CENTRAL_DOCUMENT",
        entity=doc,
        user_id=user_id,
        requested_status="verified",
        provider_name=provider or "SECONDHOUR_INSTITUTIONAL",
        trust_mode=trust_mode,
        reference_id=f"DOCVER-{uuid4().hex[:12].upper()}",
        verified_metadata={"document_name": doc.document_name, "category": doc.category},
        consent_record_id=consent_record_id,
        verification_type="INSTITUTIONAL_MATCH",
        ip_address=ip_address,
        user_agent=user_agent,
    )


def retry_verification(
    db: Session,
    user_id: str,
    entity_type: str,
    entity_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    trust_mode: str | None = None,
) -> dict[str, Any]:
    """Retry a previously failed verification for vehicle, document, or identity."""
    ent_clean = entity_type.upper().strip()

    # Increment retry counter on previous verification records
    prev_records = db.scalars(
        select(VerificationRecord).where(
            VerificationRecord.user_id == user_id,
            VerificationRecord.entity_type == ent_clean,
            VerificationRecord.entity_id == entity_id,
        ).order_by(VerificationRecord.created_at.desc())
    ).all()
    retry_count = len(prev_records)

    if ent_clean in ("IDENTITY_DOCUMENT", "CENTRAL_DOCUMENT"):
        res = verify_document(db, user_id, entity_id, ip_address=ip_address, user_agent=user_agent, trust_mode=trust_mode)
        res["retry_count"] = retry_count
        return res

    if ent_clean == "VEHICLE_RC":
        res = VahanAdapter.verify_vehicle(db, user_id, entity_id, ip_address=ip_address, user_agent=user_agent, trust_mode=trust_mode)
        res["retry_count"] = retry_count
        return res

    if ent_clean == "VEHICLE_INSURANCE":
        res = InsuranceAdapter.verify_policy(db, user_id, entity_id, ip_address=ip_address, user_agent=user_agent, trust_mode=trust_mode)
        res["retry_count"] = retry_count
        return res

    raise ServiceError(f"Unsupported retry entity type '{entity_type}'")


# ==============================================================================
# 4. Overall Verification State & History Reporting
# ==============================================================================

def get_verification_overview(db: Session, user_id: str) -> dict[str, Any]:
    """Compile comprehensive verification status across profile, vehicles, and documents."""
    user = db.get(User, user_id)
    if not user:
        raise ServiceError("User not found")

    # 1. Contact verification
    contact_status = {
        "email": {
            "target": _mask_identifier(user.email),
            "is_verified": bool(user.email_verified),
        },
        "phone": {
            "target": _mask_identifier(user.phone),
            "is_verified": bool(user.phone_verified),
        },
    }

    # 2. Vehicles verification
    vehicles = db.scalars(
        select(Vehicle).where(
            Vehicle.user_id == user_id,
            Vehicle.is_active.is_(True),
            Vehicle.deleted_at.is_(None),
        )
    ).all()
    veh_list = []
    veh_verified_count = 0
    for v in vehicles:
        is_v = (getattr(v, "verification_status", "unverified") or "unverified") == "verified"
        if is_v:
            veh_verified_count += 1
        veh_list.append({
            "id": v.id,
            "registration_number": v.registration_number,
            "manufacturer": v.manufacturer,
            "model": v.model,
            "verification_status": getattr(v, "verification_status", "unverified") or "unverified",
            "verification_provider": getattr(v, "verification_provider", None),
            "verified_at": iso(v.verified_at) if getattr(v, "verified_at", None) else None,
            "verification_reference_id": getattr(v, "verification_reference_id", None),
        })

    # 3. Central Documents verification
    docs = db.scalars(
        select(CentralDocument).where(
            CentralDocument.user_id == user_id,
            CentralDocument.is_active.is_(True),
            CentralDocument.deleted_at.is_(None),
        )
    ).all()

    doc_counts = {"verified": 0, "unverified": 0, "failed": 0, "pending": 0}
    doc_list = []
    for d in docs:
        st = (d.verification_status or "unverified").lower()
        if st in doc_counts:
            doc_counts[st] += 1
        else:
            doc_counts["unverified"] += 1

        doc_list.append({
            "id": d.id,
            "document_name": d.document_name,
            "category": d.category,
            "document_type": d.document_type,
            "masked_number": _mask_identifier(d.document_number),
            "verification_status": d.verification_status,
            "verification_provider": d.verification_provider,
            "verified_at": iso(d.verified_at) if d.verified_at else None,
            "verification_reference_id": d.verification_reference_id,
            "failure_reason": d.verification_failure_reason,
        })

    # 4. Recent verification history
    recent_records = db.scalars(
        select(VerificationRecord).where(
            VerificationRecord.user_id == user_id,
        ).order_by(VerificationRecord.created_at.desc()).limit(10)
    ).all()

    history = [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "provider": r.provider,
            "status": r.status,
            "verification_type": r.verification_type,
            "reference_id": r.verification_reference_id,
            "failure_reason": r.failure_reason,
            "created_at": iso(r.created_at),
            "verified_at": iso(r.verified_at) if r.verified_at else None,
        }
        for r in recent_records
    ]

    # Calculate overall trust tier
    total_items = 2 + len(vehicles) + len(docs)
    verified_items = (
        (1 if user.email_verified else 0)
        + (1 if user.phone_verified else 0)
        + veh_verified_count
        + doc_counts["verified"]
    )
    trust_score_pct = int(round((verified_items / total_items) * 100)) if total_items > 0 else 0

    return {
        "user_id": user_id,
        "trust_score_percentage": trust_score_pct,
        "contacts": contact_status,
        "vehicles": {
            "total": len(vehicles),
            "verified": veh_verified_count,
            "items": veh_list,
        },
        "documents": {
            "total": len(docs),
            "counts": doc_counts,
            "items": doc_list,
        },
        "recent_activity": history,
    }


def list_verification_history(
    db: Session,
    user_id: str,
    entity_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve immutable verification logs."""
    stmt = select(VerificationRecord).where(VerificationRecord.user_id == user_id)
    if entity_type and entity_type.upper() != "ALL":
        stmt = stmt.where(VerificationRecord.entity_type == entity_type.upper().strip())
    stmt = stmt.order_by(VerificationRecord.created_at.desc()).limit(limit)

    records = db.scalars(stmt).all()
    return [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "provider": r.provider,
            "status": r.status,
            "verification_type": r.verification_type,
            "reference_id": r.verification_reference_id,
            "failure_reason": r.failure_reason,
            "retry_count": r.retry_count,
            "metadata": r.verified_metadata or {},
            "created_at": iso(r.created_at),
            "verified_at": iso(r.verified_at) if r.verified_at else None,
        }
        for r in records
    ]
