"""Phase 4: Insurance Claims Service.

Connects accident cases, vehicles, policies, reports, and claim lifecycle tracking.
Strictly separates internal user readiness/approval from external insurer submission and settlement.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import (
    Case,
    CaseVehicle,
    InsuranceClaim,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    new_id,
    utcnow,
)
from app.services.common import PermissionDenied, ServiceError, add_event, iso, parse_dt, require_member

CLAIM_STATUSES = (
    "draft",
    "preparing",
    "ready_for_review",
    "approved_by_user",
    "submitted",
    "under_review",
    "additional_info_required",
    "approved_by_insurer",
    "rejected",
    "settled",
    "withdrawn",
)

CLAIM_TYPES = (
    "own_damage",
    "third_party_liability",
    "comprehensive",
    "personal_accident",
)


def _claim_dict(c: InsuranceClaim) -> dict:
    return {
        "id": c.id,
        "case_id": c.case_id,
        "vehicle_id": c.vehicle_id,
        "policy_id": c.policy_id,
        "created_by": c.created_by,
        "insurer_name": c.insurer_name,
        "policy_number": c.policy_number,
        "claim_reference_number": c.claim_reference_number,
        "claim_type": c.claim_type,
        "incident_date": iso(c.incident_date),
        "description": c.description,
        "estimated_amount": float(c.estimated_amount) if c.estimated_amount is not None else None,
        "approved_amount": float(c.approved_amount) if c.approved_amount is not None else None,
        "claim_status": c.claim_status,
        "filed_at": iso(c.filed_at) if c.filed_at else None,
        "settled_at": iso(c.settled_at) if c.settled_at else None,
        "surveyor_name": c.surveyor_name,
        "surveyor_phone": c.surveyor_phone,
        "cashless_garage": c.cashless_garage,
        "metadata": c.metadata_json or {},
        "created_at": iso(c.created_at),
        "updated_at": iso(c.updated_at),
    }


def create_insurance_claim(
    db: Session,
    actor_id: str,
    case_id: str,
    data: dict,
) -> dict:
    """Create an insurance claim record linked to an accident case and optional vehicle/policy."""
    case: Case = require_member(db, actor_id, case_id)

    # 1. Determine vehicle and policy
    vehicle_id = data.get("vehicle_id") or case.primary_vehicle_id or case.vehicle_id
    policy_id = data.get("policy_id")

    # If policy_id was not explicitly passed, attempt to find vehicle's active policy
    policy = None
    if policy_id:
        policy = db.get(VehicleInsurancePolicy, policy_id)
    elif vehicle_id:
        policy = db.scalars(
            select(VehicleInsurancePolicy)
            .where(VehicleInsurancePolicy.vehicle_id == vehicle_id, VehicleInsurancePolicy.is_current_policy == True)
            .order_by(VehicleInsurancePolicy.created_at.desc())
        ).first()
        if policy:
            policy_id = policy.id

    insurer_name = (data.get("insurer_name") or (policy.provider if policy else case.insurance_provider) or "Tata AIG General Insurance").strip()
    policy_number = (data.get("policy_number") or (policy.policy_number if policy else case.insurance_policy_number) or "POL-UNKNOWN").strip()
    claim_type = data.get("claim_type", "own_damage")
    if claim_type not in CLAIM_TYPES:
        claim_type = "own_damage"

    incident_dt = parse_dt(data.get("incident_date"), "incident_date") if data.get("incident_date") else case.incident_at

    claim_status = data.get("claim_status", "draft")
    if claim_status not in CLAIM_STATUSES:
        claim_status = "draft"

    cid = new_id("claim")
    claim_ref = data.get("claim_reference_number")
    if not claim_ref or not str(claim_ref).strip():
        suffix = case.case_number[-4:] if case.case_number else "0001"
        claim_ref = f"CLM-{suffix}-{cid[-4:].upper()}"

    claim = InsuranceClaim(
        id=cid,
        case_id=case_id,
        vehicle_id=vehicle_id,
        policy_id=policy_id,
        created_by=actor_id,
        insurer_name=insurer_name[:150],
        policy_number=policy_number[:100],
        claim_reference_number=claim_ref,
        claim_type=claim_type,
        incident_date=incident_dt,
        description=data.get("description", "").strip(),
        estimated_amount=float(data["estimated_amount"]) if data.get("estimated_amount") is not None else None,
        approved_amount=float(data["approved_amount"]) if data.get("approved_amount") is not None else None,
        claim_status=claim_status,
        filed_at=parse_dt(data.get("filed_at"), "filed_at") if data.get("filed_at") else None,
        surveyor_name=data.get("surveyor_name") or case.insurance_surveyor_name,
        surveyor_phone=data.get("surveyor_phone") or case.insurance_surveyor_phone,
        cashless_garage=data.get("cashless_garage") or "Authorized Service Centre",
        metadata_json=data.get("metadata") or {},
        is_active=True,
    )
    db.add(claim)
    db.flush()

    # Mirror onto case table for backward compatibility if case has none
    if not case.insurance_claim_number and claim.claim_reference_number:
        case.insurance_claim_number = claim.claim_reference_number
    if not case.insurance_provider:
        case.insurance_provider = claim.insurer_name
    if not case.insurance_policy_number:
        case.insurance_policy_number = claim.policy_number

    add_event(
        db,
        case_id,
        actor_id,
        "claim_created",
        f"Initiated insurance claim ({claim.insurer_name} - {claim.claim_type})",
        title="Insurance Claim Initiated",
        related_entity_type="insurance_claim",
        related_entity_id=claim.id,
        metadata={"claim_type": claim.claim_type, "status": claim.claim_status},
    )

    db.commit()
    return _claim_dict(claim)


def list_case_claims(db: Session, actor_id: str, case_id: str) -> list[dict]:
    """Retrieve all active claims associated with a case."""
    require_member(db, actor_id, case_id)
    claims = db.scalars(
        select(InsuranceClaim)
        .where(InsuranceClaim.case_id == case_id, InsuranceClaim.is_active == True)
        .order_by(InsuranceClaim.created_at.desc())
    ).all()
    return [_claim_dict(c) for c in claims]


def get_claim_details(db: Session, actor_id: str, case_id: str, claim_id: str) -> dict:
    """Retrieve full details of a specific claim, including associated submissions."""
    require_member(db, actor_id, case_id)
    claim = db.get(InsuranceClaim, claim_id)
    if not claim or claim.case_id != case_id or not claim.is_active:
        raise ServiceError("Insurance claim not found")

    res = _claim_dict(claim)
    # Include associated external submissions
    res["submissions"] = [
        {
            "id": s.id,
            "external_org_name": s.external_org_name,
            "submission_method": s.submission_method,
            "submission_status": s.submission_status,
            "external_reference_number": s.external_reference_number,
            "submitted_at": iso(s.submitted_at),
            "acknowledged_at": iso(s.acknowledged_at),
        }
        for s in claim.submissions
    ]
    return res


def update_claim(
    db: Session,
    actor_id: str,
    case_id: str,
    claim_id: str,
    data: dict,
) -> dict:
    """Update claim fields (amounts, surveyor details, description, claim reference)."""
    require_member(db, actor_id, case_id)
    claim = db.get(InsuranceClaim, claim_id)
    if not claim or claim.case_id != case_id or not claim.is_active:
        raise ServiceError("Insurance claim not found")

    if "claim_reference_number" in data:
        claim.claim_reference_number = str(data["claim_reference_number"]).strip() or None
    if "insurer_name" in data and data["insurer_name"]:
        claim.insurer_name = str(data["insurer_name"]).strip()[:150]
    if "policy_number" in data and data["policy_number"]:
        claim.policy_number = str(data["policy_number"]).strip()[:100]
    if "claim_type" in data and data["claim_type"] in CLAIM_TYPES:
        claim.claim_type = data["claim_type"]
    if "description" in data:
        claim.description = str(data["description"]).strip()
    if "estimated_amount" in data:
        claim.estimated_amount = float(data["estimated_amount"]) if data["estimated_amount"] is not None else None
    if "approved_amount" in data:
        claim.approved_amount = float(data["approved_amount"]) if data["approved_amount"] is not None else None
    if "surveyor_name" in data:
        claim.surveyor_name = str(data["surveyor_name"]).strip() or None
    if "surveyor_phone" in data:
        claim.surveyor_phone = str(data["surveyor_phone"]).strip() or None
    if "cashless_garage" in data:
        claim.cashless_garage = str(data["cashless_garage"]).strip() or None
    if "metadata" in data and isinstance(data["metadata"], dict):
        current_meta = claim.metadata_json or {}
        current_meta.update(data["metadata"])
        claim.metadata_json = current_meta

    claim.updated_at = utcnow()
    db.commit()
    return _claim_dict(claim)


def update_claim_status(
    db: Session,
    actor_id: str,
    case_id: str,
    claim_id: str,
    new_status: str,
    reason: str = "",
    notes: str = "",
) -> dict:
    """Transition claim status with audit logging."""
    require_member(db, actor_id, case_id)
    claim = db.get(InsuranceClaim, claim_id)
    if not claim or claim.case_id != case_id or not claim.is_active:
        raise ServiceError("Insurance claim not found")

    if new_status not in CLAIM_STATUSES:
        raise ServiceError(f"Invalid claim status: {new_status}. Allowed: {CLAIM_STATUSES}")

    effective_reason = reason or notes or "Status update"
    old_status = claim.claim_status
    claim.claim_status = new_status
    now = utcnow()
    claim.updated_at = now

    if new_status == "submitted" and not claim.filed_at:
        claim.filed_at = now
    elif new_status == "settled" and not claim.settled_at:
        claim.settled_at = now

    add_event(
        db,
        case_id,
        actor_id,
        "claim_status_updated",
        f"Claim {claim.id} status changed from {old_status} to {new_status} ({effective_reason})",
        title="Claim Status Updated",
        related_entity_type="insurance_claim",
        related_entity_id=claim.id,
        metadata={"old_status": old_status, "new_status": new_status, "reason": effective_reason},
    )

    db.commit()
    return _claim_dict(claim)


def delete_claim(db: Session, actor_id: str, case_id: str, claim_id: str) -> dict:
    """Soft-delete insurance claim."""
    require_member(db, actor_id, case_id)
    claim = db.get(InsuranceClaim, claim_id)
    if not claim or claim.case_id != case_id:
        raise ServiceError("Insurance claim not found")

    claim.is_active = False
    claim.deleted_at = utcnow()
    add_event(
        db,
        case_id,
        actor_id,
        "claim_deleted",
        f"Deleted insurance claim {claim.id}",
        title="Claim Deleted",
        related_entity_type="insurance_claim",
        related_entity_id=claim.id,
    )
    db.commit()
    return {"claim_id": claim_id, "deleted": True}
