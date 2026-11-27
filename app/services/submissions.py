"""Phase 4: External Submissions Service.

Tracks outbound filings to statutory authorities, motor insurers, and hospital scheme portals.
Enforces strict verification boundaries:
- User approval does NOT equal external submission.
- Manual user submissions require explicit user confirmation and are transparently labeled as manual.
- External reference numbers and delivery acknowledgements are never fabricated.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import (
    Case,
    ExternalSubmission,
    InsuranceClaim,
    Report,
    User,
    new_id,
    utcnow,
)
from app.services.common import PermissionDenied, ServiceError, add_event, iso, parse_dt, require_member

SUBMISSION_STATUSES = (
    "draft",
    "queued",
    "submitted",
    "acknowledged",
    "rejected",
    "failed",
)

ORG_TYPES = (
    "insurer",
    "police",
    "hospital",
    "government",
    "court",
    "legal",
)

SUBMISSION_METHODS = (
    "manual_user_submission",
    "email",
    "portal_upload",
    "physical_handover",
    "api",
)


def _submission_dict(s: ExternalSubmission) -> dict:
    return {
        "id": s.id,
        "case_id": s.case_id,
        "report_id": s.report_id,
        "claim_id": s.claim_id,
        "submitted_by": s.submitted_by,
        "external_org_name": s.external_org_name,
        "external_org_type": s.external_org_type,
        "external_reference_number": s.external_reference_number,
        "submission_method": s.submission_method,
        "submission_status": s.submission_status,
        "submitted_at": iso(s.submitted_at) if s.submitted_at else None,
        "acknowledged_at": iso(s.acknowledged_at) if s.acknowledged_at else None,
        "response_at": iso(s.response_at) if s.response_at else None,
        "failure_reason": s.failure_reason,
        "is_manual": s.submission_method in ("manual_user_submission", "physical_handover"),
        "is_verified_acknowledgement": s.submission_status == "acknowledged" and bool(s.external_reference_number),
        "metadata": s.metadata_json or {},
        "created_at": iso(s.created_at),
        "updated_at": iso(s.updated_at),
    }


def create_external_submission(
    db: Session,
    actor_id: str,
    case_id: str,
    data: dict,
) -> dict:
    """Create an external submission package draft."""
    case: Case = require_member(db, actor_id, case_id)

    org_name = str(data.get("external_org_name", "")).strip()
    if not org_name:
        raise ServiceError("external_org_name is required")

    org_type = data.get("external_org_type", "insurer")
    if org_type not in ORG_TYPES:
        org_type = "insurer"

    method = data.get("submission_method", "manual_user_submission")
    if method not in SUBMISSION_METHODS:
        method = "manual_user_submission"

    status = data.get("submission_status", "draft")
    if status not in SUBMISSION_STATUSES:
        status = "draft"

    report_id = data.get("report_id")
    claim_id = data.get("claim_id")

    if report_id:
        rpt = db.get(Report, report_id)
        if not rpt or rpt.case_id != case_id:
            raise ServiceError("Associated report does not belong to this case")

    if claim_id:
        clm = db.get(InsuranceClaim, claim_id)
        if not clm or clm.case_id != case_id:
            raise ServiceError("Associated claim does not belong to this case")

    sid = new_id("exsub")
    now = utcnow()
    sub = ExternalSubmission(
        id=sid,
        case_id=case_id,
        report_id=report_id,
        claim_id=claim_id,
        submitted_by=actor_id,
        external_org_name=org_name[:150],
        external_org_type=org_type,
        external_reference_number=str(data["external_reference_number"]).strip() if data.get("external_reference_number") else None,
        submission_method=method,
        submission_status=status,
        submitted_at=now if status == "submitted" else None,
        metadata_json=data.get("metadata") or {},
    )
    db.add(sub)
    db.flush()

    add_event(
        db,
        case_id,
        actor_id,
        "submission_created",
        f"Drafted external filing for {sub.external_org_name} ({sub.external_org_type})",
        title="External Filing Drafted",
        related_entity_type="external_submission",
        related_entity_id=sub.id,
        metadata={"target_org": sub.external_org_name, "status": sub.submission_status},
    )

    db.commit()
    return _submission_dict(sub)


def list_case_submissions(db: Session, actor_id: str, case_id: str) -> list[dict]:
    """List all external submissions recorded for a case."""
    require_member(db, actor_id, case_id)
    subs = db.scalars(
        select(ExternalSubmission)
        .where(ExternalSubmission.case_id == case_id)
        .order_by(ExternalSubmission.created_at.desc())
    ).all()
    return [_submission_dict(s) for s in subs]


def get_submission_details(db: Session, actor_id: str, case_id: str, submission_id: str) -> dict:
    """Retrieve full details of an external submission."""
    require_member(db, actor_id, case_id)
    sub = db.get(ExternalSubmission, submission_id)
    if not sub or sub.case_id != case_id:
        raise ServiceError("External submission not found")
    return _submission_dict(sub)


def confirm_manual_submission(
    db: Session,
    actor_id: str,
    case_id: str,
    submission_id: str,
    external_reference_number: str | None = None,
    notes: str = "",
) -> dict:
    """User explicitly confirms having manually filed/dispatched the dossier to the external organization."""
    require_member(db, actor_id, case_id)
    sub = db.get(ExternalSubmission, submission_id)
    if not sub or sub.case_id != case_id:
        raise ServiceError("External submission not found")

    now = utcnow()
    sub.submission_status = "submitted"
    sub.submitted_at = now
    if external_reference_number and external_reference_number.strip():
        sub.external_reference_number = external_reference_number.strip()

    meta = sub.metadata_json or {}
    meta["manual_user_confirmed"] = True
    meta["user_confirmation_notes"] = notes or "User confirmed manual dispatch"
    meta["confirmed_by"] = actor_id
    sub.metadata_json = meta
    sub.updated_at = now

    add_event(
        db,
        case_id,
        actor_id,
        "submission_confirmed_manual",
        f"User confirmed manual submission to {sub.external_org_name} (Ref: {sub.external_reference_number or 'Pending receipt'})",
        title="Manual Submission Confirmed",
        related_entity_type="external_submission",
        related_entity_id=sub.id,
        metadata={"manual": True, "org": sub.external_org_name, "ref": sub.external_reference_number},
    )

    db.commit()
    return _submission_dict(sub)


def record_submission_acknowledgement(
    db: Session,
    actor_id: str,
    case_id: str,
    submission_id: str,
    external_reference_number: str,
    response_payload: dict | None = None,
) -> dict:
    """Record an authentic acknowledgement or receipt number from the recipient organization."""
    require_member(db, actor_id, case_id)
    sub = db.get(ExternalSubmission, submission_id)
    if not sub or sub.case_id != case_id:
        raise ServiceError("External submission not found")

    ref = str(external_reference_number).strip()
    if not ref:
        raise ServiceError("A real external_reference_number is required to record acknowledgement")

    now = utcnow()
    sub.submission_status = "acknowledged"
    sub.acknowledged_at = now
    sub.response_at = now
    sub.external_reference_number = ref
    if response_payload:
        meta = sub.metadata_json or {}
        meta["response_payload"] = response_payload
        sub.metadata_json = meta
    sub.updated_at = now

    add_event(
        db,
        case_id,
        actor_id,
        "submission_acknowledged",
        f"Filing acknowledged by {sub.external_org_name} with Ref #{ref}",
        title="Filing Acknowledged by External Authority",
        related_entity_type="external_submission",
        related_entity_id=sub.id,
        metadata={"org": sub.external_org_name, "ref": ref},
    )

    db.commit()
    return _submission_dict(sub)


def record_submission_failure(
    db: Session,
    actor_id: str,
    case_id: str,
    submission_id: str,
    failure_reason: str,
) -> dict:
    """Record a rejection or technical delivery failure for an external submission."""
    require_member(db, actor_id, case_id)
    sub = db.get(ExternalSubmission, submission_id)
    if not sub or sub.case_id != case_id:
        raise ServiceError("External submission not found")

    reason = str(failure_reason).strip() or "External authority rejected or failed to process filing"
    now = utcnow()
    sub.submission_status = "failed"
    sub.failure_reason = reason
    sub.response_at = now
    sub.updated_at = now

    add_event(
        db,
        case_id,
        actor_id,
        "submission_failed",
        f"Submission to {sub.external_org_name} failed: {reason}",
        title="External Submission Failed",
        related_entity_type="external_submission",
        related_entity_id=sub.id,
        metadata={"org": sub.external_org_name, "failure_reason": reason},
    )

    db.commit()
    return _submission_dict(sub)

