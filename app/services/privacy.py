"""Phase 5: Privacy Preferences, Consent Management & Notification Governance Service.

Provides:
1. User Privacy Preferences: Fine-grained switches governing AI data inclusion and data sharing.
   - Medical information defaults to disabled.
   - Separate switches for vehicles, documents, cases, and emergency broadcast.
   - Backend enforcement preventing unauthorized ingestion.
2. Consent Management: Immutable history of explicit consent grants and revocations.
   - Distinguishes Terms, Privacy, AI Processing, Medical Sharing, Emergency Dispatch, and Notifications.
   - Revocation never erases historical grant logs; marks previous grants as revoked.
   - Enforced by backend services before dispatch or data sharing.
3. Notification Preferences & Quiet Hours:
   - Channel toggles: email, SMS, in-app, WhatsApp, push.
   - Category toggles: accident alerts, case updates, document expiry, insurance renewals, task reminders, AI actions.
   - Quiet hours evaluation in user's configured timezone.
"""
from __future__ import annotations

from datetime import datetime, time
import zoneinfo
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import (
    ConsentRecord,
    UserNotificationPreference,
    UserPrivacyPreference,
    new_id,
    utcnow,
)
from app.services import audit
from app.services.common import ServiceError, iso


CONSENT_TYPES = (
    "terms_of_service",
    "privacy_policy",
    "ai_data_processing",
    "medical_information_sharing",
    "emergency_contact_data_sharing",
    "external_document_sharing",
    "notifications",
    "pm_rahat_claim_intake",
)


# ==============================================================================
# Privacy Preferences
# ==============================================================================

def _privacy_dict(p: UserPrivacyPreference) -> dict[str, Any]:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "ai_data_access_enabled": p.ai_data_access_enabled,
        "ai_include_medical": p.ai_include_medical,
        "ai_include_documents": p.ai_include_documents,
        "ai_include_vehicles": p.ai_include_vehicles,
        "ai_include_cases": p.ai_include_cases,
        "allow_emergency_broadcast": p.allow_emergency_broadcast,
        "conversation_retention_days": p.conversation_retention_days,
        "personalization_enabled": p.personalization_enabled,
        "analytics_enabled": p.analytics_enabled,
        "data_sharing_preferences": p.data_sharing_preferences or {},
        "medical_info_sharing_enabled": p.medical_info_sharing_enabled,
        "updated_at": iso(p.updated_at),
    }


def get_privacy_preferences(db: Session, user_id: str) -> dict[str, Any]:
    """Retrieve privacy preferences with privacy-protective defaults."""
    pref = db.scalars(select(UserPrivacyPreference).where(UserPrivacyPreference.user_id == user_id)).first()
    if not pref:
        pref = UserPrivacyPreference(
            id=new_id("privpref"),
            user_id=user_id,
            ai_data_access_enabled=True,
            ai_include_medical=False,  # Private by default!
            ai_include_documents=True,
            ai_include_vehicles=True,
            ai_include_cases=True,
            allow_emergency_broadcast=True,
            conversation_retention_days=365,
            personalization_enabled=True,
            analytics_enabled=False,
            data_sharing_preferences={"anonymized_research": False, "insurer_direct_share": False},
            medical_info_sharing_enabled=False,
        )
        db.add(pref)
        db.commit()

    return _privacy_dict(pref)


def update_privacy_preferences(db: Session, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Update privacy settings and record changes in audit log."""
    pref = db.scalars(select(UserPrivacyPreference).where(UserPrivacyPreference.user_id == user_id)).first()
    if not pref:
        pref = UserPrivacyPreference(id=new_id("privpref"), user_id=user_id)
        db.add(pref)

    boolean_fields = (
        "ai_data_access_enabled",
        "ai_include_medical",
        "ai_include_documents",
        "ai_include_vehicles",
        "ai_include_cases",
        "allow_emergency_broadcast",
        "personalization_enabled",
        "analytics_enabled",
        "medical_info_sharing_enabled",
    )
    for field in boolean_fields:
        if field in data:
            setattr(pref, field, bool(data[field]))

    if "conversation_retention_days" in data:
        try:
            val = int(data["conversation_retention_days"])
            if val in (30, 90, 180, 365, 730, 0):  # 0 indicates indefinite
                pref.conversation_retention_days = val
        except (ValueError, TypeError):
            pass

    if "data_sharing_preferences" in data and isinstance(data["data_sharing_preferences"], dict):
        cur = pref.data_sharing_preferences or {}
        cur.update(data["data_sharing_preferences"])
        pref.data_sharing_preferences = cur

    pref.updated_at = utcnow()

    # Centralized audit log
    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="update_privacy_preferences",
        resource_type="privacy_preference",
        resource_id=pref.id,
        payload=data,
        result_summary="User updated privacy preferences",
    )
    db.commit()

    return _privacy_dict(pref)


def check_ai_data_access(db: Session, user_id: str, resource_type: str) -> bool:
    """Evaluate whether the AI assistant is authorized to inspect a given resource."""
    pref = db.scalars(select(UserPrivacyPreference).where(UserPrivacyPreference.user_id == user_id)).first()
    if not pref:
        # Defaults
        if resource_type in ("medical", "medical_information"):
            return False
        return True

    if not pref.ai_data_access_enabled:
        return False

    if resource_type in ("medical", "medical_information"):
        return bool(pref.ai_include_medical and pref.medical_info_sharing_enabled)
    elif resource_type in ("vehicles", "vehicle"):
        return bool(pref.ai_include_vehicles)
    elif resource_type in ("documents", "document"):
        return bool(pref.ai_include_documents)
    elif resource_type in ("cases", "case", "accident_case"):
        return bool(pref.ai_include_cases)

    return True


# ==============================================================================
# Consent Records
# ==============================================================================

def _consent_dict(c: ConsentRecord) -> dict[str, Any]:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "consent_type": c.consent_type,
        "consent_status": c.consent_status,
        "policy_version": c.policy_version,
        "consent_source": c.consent_source,
        "metadata": c.metadata_json or {},
        "ip_address": c.ip_address,
        "user_agent": c.user_agent,
        "consent_timestamp": iso(c.consent_timestamp),
        "revoked_at": iso(c.revoked_at) if c.revoked_at else None,
        "recorded_at": iso(c.recorded_at),
    }


def grant_consent(
    db: Session,
    user_id: str,
    consent_type: str,
    policy_version: str = "1.0",
    consent_source: str = "web_application",
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Record an explicit user consent grant."""
    if consent_type not in CONSENT_TYPES:
        consent_type = "general"

    cid = new_id("consent")
    now = utcnow()

    record = ConsentRecord(
        id=cid,
        user_id=user_id,
        consent_type=consent_type,
        consent_status="granted",
        policy_version=policy_version,
        consent_source=consent_source,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
        consent_timestamp=now,
        recorded_at=now,
    )
    db.add(record)

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="grant_consent",
        resource_type="consent_record",
        resource_id=cid,
        payload={"consent_type": consent_type, "policy_version": policy_version, "source": consent_source},
        result_summary=f"User granted explicit consent for '{consent_type}' (v{policy_version})",
    )
    db.commit()
    return _consent_dict(record)


def revoke_consent(
    db: Session,
    user_id: str,
    consent_type: str,
    metadata: dict[str, Any] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Revoke consent for a specific category while preserving historical records."""
    now = utcnow()

    # Mark active records as revoked
    active_records = db.scalars(
        select(ConsentRecord)
        .where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.consent_status == "granted",
        )
    ).all()

    for r in active_records:
        r.consent_status = "revoked"
        r.revoked_at = now

    meta = dict(metadata or {})
    if reason:
        meta["reason"] = reason
    meta["revoked_at"] = now.isoformat()

    # Also insert an immutable revocation entry
    cid = new_id("consent")
    revocation_entry = ConsentRecord(
        id=cid,
        user_id=user_id,
        consent_type=consent_type,
        consent_status="revoked",
        policy_version="1.0",
        consent_source="web_application",
        metadata_json=meta,
        consent_timestamp=now,
        revoked_at=now,
        recorded_at=now,
    )
    db.add(revocation_entry)

    # Central audit
    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="revoke_consent",
        resource_type="consent_record",
        resource_id=cid,
        payload={"consent_type": consent_type, "reason": reason},
        result_summary=f"User revoked consent for '{consent_type}'",
    )
    db.commit()
    return _consent_dict(revocation_entry)


def list_user_consents(db: Session, user_id: str) -> list[dict[str, Any]]:
    """Retrieve full audit history of consent grants and revocations."""
    records = db.scalars(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .order_by(desc(ConsentRecord.recorded_at))
    ).all()
    return [_consent_dict(r) for r in records]


def has_active_consent(db: Session, user_id: str, consent_type: str) -> bool:
    """Verify whether an active, unrevoked consent record exists for this user."""
    latest = db.scalars(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id, ConsentRecord.consent_type == consent_type)
        .order_by(desc(ConsentRecord.recorded_at))
    ).first()
    return bool(latest and latest.consent_status == "granted" and latest.revoked_at is None)


# ==============================================================================
# Notification Preferences & Quiet Hours
# ==============================================================================

def _notification_dict(p: UserNotificationPreference) -> dict[str, Any]:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "channels": {
            "email_notifications": p.email_notifications,
            "sms_notifications": p.sms_notifications,
            "in_app_notifications": p.in_app_notifications,
            "whatsapp_notifications": p.whatsapp_notifications,
            "push_notifications": p.push_notifications,
        },
        "alerts": {
            "accident_alerts": p.accident_alerts,
            "case_updates": p.case_updates,
            "document_expiry_reminders": p.document_expiry_reminders,
            "insurance_renewal_reminders": p.insurance_renewal_reminders,
            "pending_task_reminders": p.pending_task_reminders,
            "ai_action_notifications": p.ai_action_notifications,
        },
        "quiet_hours": {
            "enabled": p.quiet_hours_enabled,
            "start": p.quiet_hours_start,
            "end": p.quiet_hours_end,
            "timezone": p.quiet_hours_timezone,
        },
        "preferred_language": p.preferred_language,
        "updated_at": iso(p.updated_at),
    }


def get_notification_preferences(db: Session, user_id: str) -> dict[str, Any]:
    """Retrieve user's communication channels, alert types, and quiet hour settings."""
    pref = db.scalars(select(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id)).first()
    if not pref:
        pref = UserNotificationPreference(
            id=new_id("notifpref"),
            user_id=user_id,
            email_notifications=True,
            sms_notifications=True,
            in_app_notifications=True,
            whatsapp_notifications=False,
            push_notifications=True,
            accident_alerts=True,
            case_updates=True,
            document_expiry_reminders=True,
            insurance_renewal_reminders=True,
            pending_task_reminders=True,
            ai_action_notifications=True,
            quiet_hours_enabled=False,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            quiet_hours_timezone="Asia/Kolkata",
            preferred_language="English",
        )
        db.add(pref)
        db.commit()

    return _notification_dict(pref)


def update_notification_preferences(db: Session, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Update notification settings with audit logging."""
    pref = db.scalars(select(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id)).first()
    if not pref:
        pref = UserNotificationPreference(id=new_id("notifpref"), user_id=user_id)
        db.add(pref)

    # Flatten nested structures from UI if present
    flat: dict[str, Any] = {}
    if "channels" in data and isinstance(data["channels"], dict):
        flat.update(data["channels"])
    if "alerts" in data and isinstance(data["alerts"], dict):
        flat.update(data["alerts"])
    if "quiet_hours" in data and isinstance(data["quiet_hours"], dict):
        qh = data["quiet_hours"]
        if "enabled" in qh: pref.quiet_hours_enabled = bool(qh["enabled"])
        if "start" in qh: pref.quiet_hours_start = str(qh["start"])[:8]
        if "end" in qh: pref.quiet_hours_end = str(qh["end"])[:8]
        if "timezone" in qh: pref.quiet_hours_timezone = str(qh["timezone"])[:64]

    flat.update({k: v for k, v in data.items() if k not in ("channels", "alerts", "quiet_hours")})

    boolean_fields = (
        "email_notifications",
        "sms_notifications",
        "in_app_notifications",
        "whatsapp_notifications",
        "push_notifications",
        "accident_alerts",
        "case_updates",
        "document_expiry_reminders",
        "insurance_renewal_reminders",
        "pending_task_reminders",
        "ai_action_notifications",
        "quiet_hours_enabled",
    )
    for field in boolean_fields:
        if field in flat:
            setattr(pref, field, bool(flat[field]))

    if "preferred_language" in flat:
        pref.preferred_language = str(flat["preferred_language"])[:32]
    if "quiet_hours_start" in flat:
        pref.quiet_hours_start = str(flat["quiet_hours_start"])[:8]
    if "quiet_hours_end" in flat:
        pref.quiet_hours_end = str(flat["quiet_hours_end"])[:8]
    if "quiet_hours_timezone" in flat:
        pref.quiet_hours_timezone = str(flat["quiet_hours_timezone"])[:64]

    pref.updated_at = utcnow()

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="update_notification_preferences",
        resource_type="notification_preference",
        resource_id=pref.id,
        payload=data,
        result_summary="User updated notification preferences",
    )
    db.commit()

    return _notification_dict(pref)


def can_send_notification(
    db: Session,
    user_id: str,
    channel: str,
    alert_category: str | None = None,
    alert_type: str | None = None,
    override_quiet_hours: bool = False,
    as_dict: bool = False,
) -> bool | dict[str, Any]:
    """Evaluate whether an outbound notification can be dispatched under user preferences."""
    cat = (alert_category or alert_type or "general").strip().lower()
    pref = db.scalars(select(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id)).first()
    if not pref:
        # Default allow
        return {"allowed": True, "reason": "Default notification settings active"} if as_dict else True

    # 1. Check channel toggle
    channel_col = f"{channel.lower()}_notifications"
    if hasattr(pref, channel_col) and not getattr(pref, channel_col):
        return {"allowed": False, "reason": f"Channel '{channel}' disabled in user notification preferences"} if as_dict else False

    # 2. Check alert category toggle (critical accident alerts bypass category check)
    if cat != "accident_emergency":
        cat_col = f"{cat}"
        if hasattr(pref, cat_col) and not getattr(pref, cat_col):
            return {"allowed": False, "reason": f"Alert category '{cat}' disabled by user"} if as_dict else False

    # 3. Check quiet hours (unless critical emergency override is active)
    if pref.quiet_hours_enabled and not override_quiet_hours and cat != "accident_emergency":
        try:
            tz = zoneinfo.ZoneInfo(pref.quiet_hours_timezone or "Asia/Kolkata")
            now_local = datetime.now(tz)
            cur_time = now_local.time()

            # Parse start and end times
            s_hour, s_min = map(int, pref.quiet_hours_start.split(":")[:2])
            e_hour, e_min = map(int, pref.quiet_hours_end.split(":")[:2])
            start_t = time(s_hour, s_min)
            end_t = time(e_hour, e_min)

            in_quiet = False
            if start_t <= end_t:
                in_quiet = start_t <= cur_time <= end_t
            else:  # Spans across midnight, e.g. 22:00 to 07:00
                in_quiet = cur_time >= start_t or cur_time <= end_t

            if in_quiet:
                return {
                    "allowed": False,
                    "reason": f"Quiet hours active ({pref.quiet_hours_start} to {pref.quiet_hours_end} {pref.quiet_hours_timezone})",
                } if as_dict else False
        except Exception:
            # If timezone parsing fails, fall back gracefully
            pass

    return {"allowed": True, "reason": "Notification permitted by user preferences"} if as_dict else True
