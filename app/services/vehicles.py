"""Vehicle management service for Second Hour."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app import config
from app.db import (
    CentralDocument,
    DocumentAccessLog,
    DocumentVersion,
    User,
    Vehicle,
    VehicleDocument,
    VehicleInsurancePolicy,
    VehiclePhoto,
    new_id,
    utcnow,
)
from app.services.audit import record_audit
from app.services.common import PermissionDenied, ServiceError, iso
from app.storage import get_storage


def normalize_registration_number(reg: str | None) -> str:
    """Normalize vehicle registration number for canonical comparison (uppercase alphanumeric only)."""
    if not reg:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", str(reg)).upper()


def require_vehicle_owner(db: Session, user_id: str, vehicle_id: str) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if not v or v.deleted_at is not None or not v.is_active:
        raise ServiceError("Vehicle not found")
    if v.user_id != user_id:
        raise PermissionDenied("You do not own this vehicle")
    return v


def calculate_insurance_status(expiry_date: datetime | None) -> tuple[str, int | None]:
    """Calculate actual insurance expiry status: active, expiring_soon, expired, not_provided."""
    if not expiry_date:
        return "not_provided", None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days_left = (expiry_date.date() - now.date()).days
    if days_left < 0:
        return "expired", days_left
    elif days_left <= 30:
        return "expiring_soon", days_left
    return "active", days_left


def vehicle_summary_dict(v: Vehicle, insurance: VehicleInsurancePolicy | None, doc_count: int, photo_count: int) -> dict[str, Any]:
    status, days_left = calculate_insurance_status(insurance.expiry_date if insurance else None)
    return {
        "id": v.id,
        "registration_number": v.registration_number,
        "category": v.category,
        "manufacturer": v.manufacturer,
        "model": v.model,
        "variant": v.variant,
        "manufacturing_year": v.manufacturing_year,
        "fuel_type": v.fuel_type,
        "color": v.color,
        "main_image": v.main_image,
        "owner_name": v.owner_name,
        "ownership_type": v.ownership_type,
        "is_primary": v.is_primary,
        "is_active": v.is_active,
        "verification_status": getattr(v, "verification_status", "unverified") or "unverified",
        "verification_provider": getattr(v, "verification_provider", None),
        "verified_at": iso(v.verified_at) if getattr(v, "verified_at", None) else None,
        "verification_reference_id": getattr(v, "verification_reference_id", None),
        "insurance": {
            "id": insurance.id if insurance else None,
            "provider": insurance.provider if insurance else None,
            "policy_number": insurance.policy_number if insurance else None,
            "policy_type": insurance.policy_type if insurance else None,
            "expiry_date": iso(insurance.expiry_date) if insurance and insurance.expiry_date else None,
            "status": status,
            "days_left": days_left,
        },
        "doc_count": doc_count,
        "photo_count": photo_count,
        "created_at": iso(v.created_at),
        "updated_at": iso(v.updated_at),
    }


def list_vehicles(db: Session, user_id: str) -> list[dict[str, Any]]:
    """List active vehicles belonging to authenticated user, sorted with primary first."""
    vehicles = db.scalars(
        select(Vehicle)
        .where(Vehicle.user_id == user_id, Vehicle.is_active.is_(True), Vehicle.deleted_at.is_(None))
        .order_by(Vehicle.is_primary.desc(), Vehicle.created_at.desc())
    ).all()

    results = []
    for v in vehicles:
        ins = db.scalars(
            select(VehicleInsurancePolicy)
            .where(VehicleInsurancePolicy.vehicle_id == v.id, VehicleInsurancePolicy.is_current_policy.is_(True))
            .order_by(VehicleInsurancePolicy.created_at.desc())
        ).first()
        vdoc_ids = set(db.scalars(select(VehicleDocument.id).where(VehicleDocument.vehicle_id == v.id)).all())
        cdoc_ids = set(
            db.scalars(
                select(CentralDocument.id).where(
                    CentralDocument.resource_type == "VEHICLE",
                    CentralDocument.resource_id == v.id,
                    CentralDocument.deleted_at.is_(None),
                )
            ).all()
        )
        doc_count = len(vdoc_ids.union(cdoc_ids))
        photo_count = len(db.scalars(select(VehiclePhoto.id).where(VehiclePhoto.vehicle_id == v.id)).all())
        results.append(vehicle_summary_dict(v, ins, doc_count, photo_count))
    return results


def get_vehicle(db: Session, user_id: str, vehicle_id: str) -> dict[str, Any]:
    """Retrieve full vehicle details including current insurance, policies history, and documents."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    insurance = db.scalars(
        select(VehicleInsurancePolicy)
        .where(VehicleInsurancePolicy.vehicle_id == v.id, VehicleInsurancePolicy.is_current_policy.is_(True))
        .order_by(VehicleInsurancePolicy.created_at.desc())
    ).first()
    status, days_left = calculate_insurance_status(insurance.expiry_date if insurance else None)

    # Historical policies
    policies = db.scalars(
        select(VehicleInsurancePolicy)
        .where(VehicleInsurancePolicy.vehicle_id == v.id)
        .order_by(VehicleInsurancePolicy.is_current_policy.desc(), VehicleInsurancePolicy.start_date.desc(), VehicleInsurancePolicy.created_at.desc())
    ).all()

    photos = db.scalars(
        select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id).order_by(VehiclePhoto.is_primary.desc(), VehiclePhoto.uploaded_at.desc())
    ).all()
    vdocs = db.scalars(
        select(VehicleDocument).where(VehicleDocument.vehicle_id == v.id).order_by(VehicleDocument.uploaded_at.desc())
    ).all()
    cdocs = db.scalars(
        select(CentralDocument)
        .where(CentralDocument.resource_type == "VEHICLE", CentralDocument.resource_id == v.id, CentralDocument.deleted_at.is_(None))
        .order_by(CentralDocument.created_at.desc())
    ).all()

    seen_ids = set()
    docs_payload = []
    for d in vdocs:
        seen_ids.add(d.id)
        docs_payload.append({
            "id": d.id,
            "document_type": d.document_type,
            "document_name": d.document_name,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
            "expiry_date": iso(d.expiry_date) if d.expiry_date else None,
            "verification_status": d.verification_status,
            "uploaded_at": iso(d.uploaded_at),
            "url": f"/api/vehicles/{v.id}/documents/{d.id}/file",
        })
    for cd in cdocs:
        if cd.id not in seen_ids:
            seen_ids.add(cd.id)
            docs_payload.append({
                "id": cd.id,
                "document_type": cd.document_type,
                "document_name": cd.document_name,
                "file_name": cd.file_name,
                "file_size": cd.file_size,
                "mime_type": cd.mime_type,
                "expiry_date": iso(cd.expiry_date) if cd.expiry_date else None,
                "verification_status": cd.verification_status,
                "uploaded_at": iso(cd.created_at),
                "url": f"/api/documents/{cd.id}/file",
            })

    return {
        "id": v.id,
        "user_id": v.user_id,
        "registration_number": v.registration_number,
        "category": v.category,
        "manufacturer": v.manufacturer,
        "model": v.model,
        "variant": v.variant,
        "manufacturing_year": v.manufacturing_year,
        "fuel_type": v.fuel_type,
        "color": v.color,
        "chassis_number": v.chassis_number,
        "engine_number": v.engine_number,
        "vin": v.vin,
        "engine_capacity": v.engine_capacity,
        "transmission": v.transmission,
        "owner_name": v.owner_name,
        "ownership_type": v.ownership_type,
        "relationship_to_user": v.relationship_to_user,
        "is_primary": v.is_primary,
        "is_active": v.is_active,
        "verification_status": getattr(v, "verification_status", "unverified") or "unverified",
        "verification_provider": getattr(v, "verification_provider", None),
        "verified_at": iso(v.verified_at) if getattr(v, "verified_at", None) else None,
        "verification_reference_id": getattr(v, "verification_reference_id", None),
        "registration_date": iso(v.registration_date) if v.registration_date else None,
        "main_image": v.main_image,
        "created_at": iso(v.created_at),
        "updated_at": iso(v.updated_at),
        "insurance": {
            "id": insurance.id if insurance else None,
            "provider": insurance.provider if insurance else None,
            "policy_number": insurance.policy_number if insurance else None,
            "policy_type": insurance.policy_type if insurance else "Comprehensive",
            "start_date": iso(insurance.start_date) if insurance and insurance.start_date else None,
            "expiry_date": iso(insurance.expiry_date) if insurance and insurance.expiry_date else None,
            "document_id": insurance.document_id if insurance else None,
            "status": status,
            "days_left": days_left,
        },
        "insurance_history": [
            {
                "id": pol.id,
                "provider": pol.provider,
                "policy_number": pol.policy_number,
                "policy_type": pol.policy_type,
                "start_date": iso(pol.start_date) if pol.start_date else None,
                "expiry_date": iso(pol.expiry_date) if pol.expiry_date else None,
                "is_current_policy": pol.is_current_policy,
                "policy_status": pol.policy_status,
                "superseded_by_policy_id": pol.superseded_by_policy_id,
                "coverage_details": pol.coverage_details,
                "created_at": iso(pol.created_at),
            }
            for pol in policies
        ],
        "photos": [
            {
                "id": p.id,
                "photo_category": p.photo_category,
                "file_name": p.file_name,
                "mime_type": p.mime_type,
                "is_primary": p.is_primary,
                "uploaded_at": iso(p.uploaded_at),
                "url": f"/api/vehicles/{v.id}/photos/{p.id}/file",
            }
            for p in photos
        ],
        "documents": docs_payload,
    }


def create_vehicle(db: Session, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Register a new vehicle with active duplicate prevention and primary designation."""
    reg_num = data["registration_number"].upper().strip()

    # Prevent duplicate active vehicles for this user
    existing = db.scalars(
        select(Vehicle).where(
            Vehicle.user_id == user_id,
            Vehicle.registration_number == reg_num,
            Vehicle.is_active.is_(True),
            Vehicle.deleted_at.is_(None),
        )
    ).first()
    if existing:
        raise ServiceError(f"A vehicle with registration number '{reg_num}' is already active in your account.")

    # Determine if this vehicle should be primary
    existing_count = len(
        db.scalars(
            select(Vehicle.id).where(Vehicle.user_id == user_id, Vehicle.is_active.is_(True), Vehicle.deleted_at.is_(None))
        ).all()
    )
    should_be_primary = bool(data.get("is_primary")) or existing_count == 0

    if should_be_primary:
        # Demote existing primary vehicles
        for other_v in db.scalars(select(Vehicle).where(Vehicle.user_id == user_id, Vehicle.is_active.is_(True))).all():
            other_v.is_primary = False

    reg_date = None
    if data.get("registration_date"):
        try:
            reg_date = datetime.fromisoformat(str(data["registration_date"]).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass

    v = Vehicle(
        id=new_id("veh"),
        user_id=user_id,
        registration_number=reg_num,
        category=data.get("category", "Four Wheeler"),
        manufacturer=data.get("manufacturer", "").strip(),
        model=data.get("model", "").strip(),
        variant=data.get("variant"),
        manufacturing_year=data.get("manufacturing_year"),
        fuel_type=data.get("fuel_type", "Petrol"),
        color=data.get("color"),
        chassis_number=data.get("chassis_number"),
        engine_number=data.get("engine_number"),
        vin=data.get("vin"),
        engine_capacity=data.get("engine_capacity"),
        transmission=data.get("transmission"),
        owner_name=data.get("owner_name"),
        ownership_type=data.get("ownership_type", "Individual"),
        relationship_to_user=data.get("relationship_to_user", "Self"),
        main_image=data.get("main_image"),
        is_primary=should_be_primary,
        is_active=True,
        registration_date=reg_date,
    )
    db.add(v)
    db.flush()

    # Optional initial insurance policy
    ins_data = data.get("insurance")
    if ins_data and ins_data.get("provider") and ins_data.get("policy_number"):
        exp_dt = None
        if ins_data.get("expiry_date"):
            try:
                exp_dt = datetime.fromisoformat(ins_data["expiry_date"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        start_dt = None
        if ins_data.get("start_date"):
            try:
                start_dt = datetime.fromisoformat(ins_data["start_date"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass

        pol = VehicleInsurancePolicy(
            id=new_id("vpol"),
            vehicle_id=v.id,
            provider=ins_data["provider"],
            policy_number=ins_data["policy_number"],
            policy_type=ins_data.get("policy_type", "Comprehensive"),
            start_date=start_dt,
            expiry_date=exp_dt,
            is_current_policy=True,
            policy_status="active",
        )
        db.add(pol)

    db.commit()
    return get_vehicle(db, user_id, v.id)


def update_vehicle(db: Session, user_id: str, vehicle_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Edit vehicle information with registration change invalidation and insurance policy renewal support."""
    v = require_vehicle_owner(db, user_id, vehicle_id)

    if "registration_number" in data and data["registration_number"]:
        new_reg = str(data["registration_number"]).strip().upper()
        old_reg = (v.registration_number or "").strip().upper()
        new_norm = normalize_registration_number(new_reg)
        old_norm = normalize_registration_number(old_reg)

        if new_norm != old_norm:
            # Check duplicate against other active vehicles of this user using normalized check
            other_vehicles = db.scalars(
                select(Vehicle).where(
                    Vehicle.user_id == user_id,
                    Vehicle.id != v.id,
                    Vehicle.is_active.is_(True),
                    Vehicle.deleted_at.is_(None),
                )
            ).all()
            for other_v in other_vehicles:
                if normalize_registration_number(other_v.registration_number) == new_norm:
                    raise ServiceError(f"A vehicle with registration number '{new_reg}' is already registered in your account.")

            # Apply new registration number
            v.registration_number = new_reg

            # If vehicle was verified or pending, genuinely changing registration invalidates verification
            current_status = getattr(v, "verification_status", "unverified") or "unverified"
            if current_status in ("verified", "pending"):
                old_status = current_status
                old_provider = v.verification_provider
                old_ref = v.verification_reference_id
                old_verified_at = v.verified_at

                v.verification_status = "unverified"
                v.verification_provider = None
                v.verification_reference_id = None
                v.verified_at = None
                v.verification_failure_reason = f"Registration number changed from '{old_reg}' to '{new_reg}'. Re-verification required."

                record_audit(
                    db=db,
                    actor_id=user_id,
                    action_type="vehicle_verification_invalidated",
                    resource_type="vehicle",
                    resource_id=v.id,
                    action_outcome="success",
                    result_summary=f"Vehicle verification invalidated due to registration number change ({old_reg} -> {new_reg})",
                    payload={
                        "old_registration": old_reg,
                        "new_registration": new_reg,
                        "old_verification_status": old_status,
                        "old_verification_provider": old_provider,
                        "old_verification_reference_id": old_ref,
                        "old_verified_at": iso(old_verified_at) if old_verified_at else None,
                    },
                )
        elif new_reg != old_reg:
            # Same normalized registration with harmless formatting change (e.g. 'ka 01 mj 4012' vs 'KA-01-MJ-4012')
            # Update string representation while strictly preserving existing verification status and metadata
            v.registration_number = new_reg

    fields = [
        "category", "manufacturer", "model", "variant",
        "manufacturing_year", "fuel_type", "color", "chassis_number", "engine_number",
        "vin", "engine_capacity", "transmission", "owner_name", "ownership_type",
        "relationship_to_user", "main_image"
    ]
    for f in fields:
        if f in data:
            setattr(v, f, data[f])

    if "is_primary" in data:
        should_be_primary = bool(data["is_primary"])
        if should_be_primary:
            for other_v in db.scalars(select(Vehicle).where(Vehicle.user_id == user_id, Vehicle.id != v.id)).all():
                other_v.is_primary = False
            v.is_primary = True
        else:
            v.is_primary = False

    if "registration_date" in data:
        if data["registration_date"]:
            try:
                v.registration_date = datetime.fromisoformat(str(data["registration_date"]).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        else:
            v.registration_date = None

    v.updated_at = utcnow()

    # Insurance update / renewal workflow
    if "insurance" in data and isinstance(data["insurance"], dict):
        ins_data = data["insurance"]
        if ins_data.get("provider") and ins_data.get("policy_number"):
            current_pol = db.scalars(
                select(VehicleInsurancePolicy)
                .where(VehicleInsurancePolicy.vehicle_id == v.id, VehicleInsurancePolicy.is_current_policy.is_(True))
                .order_by(VehicleInsurancePolicy.created_at.desc())
            ).first()

            exp_dt = None
            if ins_data.get("expiry_date"):
                try:
                    exp_dt = datetime.fromisoformat(ins_data["expiry_date"].replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
            start_dt = None
            if ins_data.get("start_date"):
                try:
                    start_dt = datetime.fromisoformat(ins_data["start_date"].replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            is_renewal = False
            if current_pol:
                # If policy number changed or expiry date extended, treat as renewal
                if current_pol.policy_number != ins_data["policy_number"] or (exp_dt and current_pol.expiry_date and exp_dt > current_pol.expiry_date):
                    is_renewal = True

            if is_renewal and current_pol:
                new_pol = VehicleInsurancePolicy(
                    id=new_id("vpol"),
                    vehicle_id=v.id,
                    provider=ins_data["provider"],
                    policy_number=ins_data["policy_number"],
                    policy_type=ins_data.get("policy_type", current_pol.policy_type),
                    start_date=start_dt or current_pol.expiry_date,
                    expiry_date=exp_dt,
                    is_current_policy=True,
                    policy_status="active",
                )
                db.add(new_pol)
                db.flush()

                # Mark previous policy as superseded
                current_pol.is_current_policy = False
                current_pol.policy_status = "superseded"
                current_pol.superseded_by_policy_id = new_pol.id
                current_pol.updated_at = utcnow()
            elif current_pol:
                current_pol.provider = ins_data["provider"]
                current_pol.policy_number = ins_data["policy_number"]
                if "policy_type" in ins_data:
                    current_pol.policy_type = ins_data["policy_type"]
                current_pol.start_date = start_dt
                current_pol.expiry_date = exp_dt
                current_pol.updated_at = utcnow()
            else:
                new_pol = VehicleInsurancePolicy(
                    id=new_id("vpol"),
                    vehicle_id=v.id,
                    provider=ins_data["provider"],
                    policy_number=ins_data["policy_number"],
                    policy_type=ins_data.get("policy_type", "Comprehensive"),
                    start_date=start_dt,
                    expiry_date=exp_dt,
                    is_current_policy=True,
                    policy_status="active",
                )
                db.add(new_pol)

    db.commit()
    return get_vehicle(db, user_id, v.id)


def set_primary_vehicle(db: Session, user_id: str, vehicle_id: str) -> dict[str, Any]:
    """Designate a vehicle as the primary vehicle for the user."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    for other_v in db.scalars(select(Vehicle).where(Vehicle.user_id == user_id, Vehicle.id != v.id)).all():
        other_v.is_primary = False
    v.is_primary = True
    v.updated_at = utcnow()
    db.commit()
    return get_vehicle(db, user_id, v.id)


def delete_vehicle(db: Session, user_id: str, vehicle_id: str) -> bool:
    """Soft-delete a vehicle and reassign primary vehicle if needed."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    was_primary = v.is_primary

    v.is_active = False
    v.deleted_at = utcnow()
    v.is_primary = False

    if was_primary:
        # Reassign primary to next active vehicle
        next_v = db.scalars(
            select(Vehicle)
            .where(Vehicle.user_id == user_id, Vehicle.id != v.id, Vehicle.is_active.is_(True), Vehicle.deleted_at.is_(None))
            .order_by(Vehicle.created_at.desc())
        ).first()
        if next_v:
            next_v.is_primary = True

    db.commit()
    return True


def add_vehicle_photo(
    db: Session,
    user_id: str,
    vehicle_id: str,
    photo_category: str,
    filename: str,
    content: bytes,
    is_primary: bool = False,
) -> dict[str, Any]:
    """Upload and store a vehicle photo using StorageAdapter outside PostgreSQL."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    if not content:
        raise ServiceError("Uploaded photo is empty")
    if len(content) > 10 * 1024 * 1024:
        raise ServiceError("Photo size exceeds 10 MB limit")

    ext = Path(filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ServiceError(f"Unsupported image format '{ext}'. Allowed: JPG, PNG, WEBP")

    mime_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/webp"
    digest = hashlib.sha256(content).hexdigest()
    photo_id = new_id("vpho")

    # Storage key: users/{user_id}/vehicles/{vehicle_id}/photos/{photo_id}_{filename}
    clean_name = Path(filename).name[:50]
    storage_key = f"users/{user_id}/vehicles/{v.id}/photos/{photo_id}_{clean_name}"
    storage = get_storage()
    storage.put_object(storage_key, content, mime_type)

    existing_photos_count = len(db.scalars(select(VehiclePhoto.id).where(VehiclePhoto.vehicle_id == v.id)).all())
    set_as_primary = is_primary or existing_photos_count == 0

    if set_as_primary:
        for p in db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id)).all():
            p.is_primary = False

    photo = VehiclePhoto(
        id=photo_id,
        vehicle_id=v.id,
        photo_category=photo_category or "main",
        file_name=filename,
        stored_path=storage.get_object_path(storage_key),
        storage_key=storage_key,
        mime_type=mime_type,
        file_size_bytes=len(content),
        sha256=digest,
        is_primary=set_as_primary,
    )
    db.add(photo)

    if set_as_primary:
        v.main_image = f"/api/vehicles/{v.id}/photos/{photo.id}/file"

    db.commit()
    return {
        "id": photo.id,
        "photo_category": photo.photo_category,
        "file_name": photo.file_name,
        "mime_type": photo.mime_type,
        "is_primary": photo.is_primary,
        "uploaded_at": iso(photo.uploaded_at),
        "url": f"/api/vehicles/{v.id}/photos/{photo.id}/file",
    }


def set_primary_photo(db: Session, user_id: str, vehicle_id: str, photo_id: str) -> dict[str, Any]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    target = db.get(VehiclePhoto, photo_id)
    if not target or target.vehicle_id != v.id:
        raise ServiceError("Photo not found")

    for p in db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id)).all():
        p.is_primary = (p.id == photo_id)

    v.main_image = f"/api/vehicles/{v.id}/photos/{target.id}/file"
    db.commit()
    return {"ok": True, "main_image": v.main_image}


def delete_vehicle_photo(db: Session, user_id: str, vehicle_id: str, photo_id: str) -> bool:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    photo = db.get(VehiclePhoto, photo_id)
    if not photo or photo.vehicle_id != v.id:
        raise ServiceError("Photo not found")

    was_primary = photo.is_primary
    if photo.storage_key:
        get_storage().delete_object(photo.storage_key)
    elif photo.stored_path and os.path.exists(photo.stored_path):
        try:
            os.remove(photo.stored_path)
        except OSError:
            pass

    db.delete(photo)
    db.flush()

    if was_primary:
        remaining = db.scalars(
            select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id).order_by(VehiclePhoto.uploaded_at.desc())
        ).first()
        if remaining:
            remaining.is_primary = True
            v.main_image = f"/api/vehicles/{v.id}/photos/{remaining.id}/file"
        else:
            v.main_image = None

    db.commit()
    return True


def get_photo_file(db: Session, user_id: str, vehicle_id: str, photo_id: str) -> tuple[str, str, str]:
    """Retrieve photo file path, MIME type and filename."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    photo = db.get(VehiclePhoto, photo_id)
    if not photo or photo.vehicle_id != v.id:
        raise ServiceError("Photo not found")

    storage = get_storage()
    if photo.storage_key and storage.exists(photo.storage_key):
        return storage.get_object_path(photo.storage_key), photo.mime_type, photo.file_name

    p = Path(photo.stored_path)
    if not p.exists():
        raise ServiceError("Photo file not found in storage")
    return str(p), photo.mime_type, photo.file_name


def add_vehicle_document(
    db: Session,
    user_id: str,
    vehicle_id: str,
    document_type: str,
    document_name: str,
    filename: str,
    content: bytes,
    expiry_date: datetime | None = None,
) -> dict[str, Any]:
    """Attach document to vehicle and register with central document repository."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    if not content:
        raise ServiceError("Uploaded document is empty")
    if len(content) > 10 * 1024 * 1024:
        raise ServiceError("File size exceeds 10 MB limit")

    ext = Path(filename).suffix.lower() or ".pdf"
    mime_type = "application/pdf" if ext == ".pdf" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    digest = hashlib.sha256(content).hexdigest()
    doc_id = new_id("vdoc")

    # Store via StorageAdapter
    clean_name = Path(filename).name[:60]
    storage_key = f"users/{user_id}/vehicles/{v.id}/documents/{doc_id}_{clean_name}"
    storage = get_storage()
    storage.put_object(storage_key, content, mime_type)
    stored_path = storage.get_object_path(storage_key)

    status = "verified"
    if expiry_date:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if expiry_date < now:
            status = "expired"
        elif (expiry_date - now).days <= 30:
            status = "expiring_soon"

    doc = VehicleDocument(
        id=doc_id,
        vehicle_id=v.id,
        document_type=document_type or "other",
        document_name=document_name or filename,
        file_name=filename,
        stored_path=stored_path,
        mime_type=mime_type,
        file_size=len(content),
        expiry_date=expiry_date,
        verification_status=status,
    )
    db.add(doc)

    # Sync with CentralDocument repository
    cat = "insurance" if (document_type or "").lower() in ("insurance", "insurance_policy") else "vehicle"
    cdoc = CentralDocument(
        id=doc_id,
        user_id=v.user_id,
        document_name=document_name or filename,
        document_type=document_type or "other",
        category=cat,
        file_name=filename,
        stored_path=stored_path,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=len(content),
        sha256=digest,
        expiry_date=expiry_date,
        verification_status=status,
        resource_type="VEHICLE",
        resource_id=v.id,
        current_version=1,
        is_active=True,
    )
    db.add(cdoc)
    db.flush()

    # Initial DocumentVersion
    ver = DocumentVersion(
        id=new_id("dver"),
        document_id=cdoc.id,
        version_number=1,
        storage_key=storage_key,
        file_name=filename,
        mime_type=mime_type,
        file_size_bytes=len(content),
        sha256=digest,
        uploaded_by=user_id,
        change_summary="Initial vehicle document upload",
    )
    db.add(ver)

    # Append-only access log
    log = DocumentAccessLog(
        document_id=cdoc.id,
        user_id=user_id,
        action="upload",
        access_channel="web_dashboard",
        purpose="vehicle_document_upload",
    )
    db.add(log)

    db.commit()
    return {
        "id": doc.id,
        "document_type": doc.document_type,
        "document_name": doc.document_name,
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "expiry_date": iso(doc.expiry_date) if doc.expiry_date else None,
        "verification_status": doc.verification_status,
        "uploaded_at": iso(doc.uploaded_at),
        "url": f"/api/vehicles/{v.id}/documents/{doc.id}/file",
    }


def delete_vehicle_document(db: Session, user_id: str, vehicle_id: str, doc_id: str) -> bool:
    """Soft delete vehicle document and sync with central documents."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    doc = db.get(VehicleDocument, doc_id)
    cdoc = db.get(CentralDocument, doc_id)
    if not doc and not cdoc:
        raise ServiceError("Document not found")

    if cdoc:
        cdoc.is_active = False
        cdoc.deleted_at = utcnow()
        log = DocumentAccessLog(
            document_id=cdoc.id,
            user_id=user_id,
            action="delete",
            access_channel="web_dashboard",
            purpose="vehicle_document_deletion",
        )
        db.add(log)

    if doc:
        db.delete(doc)

    db.commit()
    return True


def get_document_file(db: Session, user_id: str, vehicle_id: str, doc_id: str) -> tuple[str, str, str]:
    """Retrieve vehicle document file path, MIME type and filename."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    doc = db.get(VehicleDocument, doc_id)
    cdoc = db.get(CentralDocument, doc_id)
    target = cdoc or doc
    if not target:
        raise ServiceError("Document not found")

    storage = get_storage()
    storage_key = getattr(target, "storage_key", None)
    if storage_key and storage.exists(storage_key):
        return storage.get_object_path(storage_key), target.mime_type, target.file_name

    p = Path(target.stored_path)
    if not p.exists():
        raise ServiceError("Document file not found on disk")
    return str(p), target.mime_type, target.file_name


def list_vehicle_insurance_policies(db: Session, user_id: str, vehicle_id: str) -> list[dict[str, Any]]:
    """List historical and current insurance policies for a vehicle."""
    v = require_vehicle_owner(db, user_id, vehicle_id)
    policies = db.scalars(
        select(VehicleInsurancePolicy)
        .where(VehicleInsurancePolicy.vehicle_id == v.id)
        .order_by(VehicleInsurancePolicy.is_current_policy.desc(), VehicleInsurancePolicy.start_date.desc(), VehicleInsurancePolicy.created_at.desc())
    ).all()
    return [
        {
            "id": p.id,
            "vehicle_id": p.vehicle_id,
            "provider": p.provider,
            "policy_number": p.policy_number,
            "policy_type": p.policy_type,
            "start_date": iso(p.start_date) if p.start_date else None,
            "expiry_date": iso(p.expiry_date) if p.expiry_date else None,
            "document_id": p.document_id,
            "is_current_policy": p.is_current_policy,
            "policy_status": p.policy_status,
            "superseded_by_policy_id": p.superseded_by_policy_id,
            "coverage_details": p.coverage_details,
            "created_at": iso(p.created_at),
        }
        for p in policies
    ]
