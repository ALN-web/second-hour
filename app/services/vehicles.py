"""Vehicle management service for Second Hour."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import VEHICLE_DOCS_DIR, VEHICLE_PHOTOS_DIR
from app.db import CentralDocument, User, Vehicle, VehicleDocument, VehicleInsurancePolicy, VehiclePhoto, new_id, utcnow
from app.services.common import PermissionDenied, ServiceError, iso


def require_vehicle_owner(db: Session, user_id: str, vehicle_id: str) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if not v:
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
        "insurance": {
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
    vehicles = db.scalars(select(Vehicle).where(Vehicle.user_id == user_id).order_by(Vehicle.created_at.desc())).all()
    results = []
    for v in vehicles:
        ins = db.scalars(
            select(VehicleInsurancePolicy).where(VehicleInsurancePolicy.vehicle_id == v.id).order_by(VehicleInsurancePolicy.created_at.desc())
        ).first()
        vdoc_ids = set(db.scalars(select(VehicleDocument.id).where(VehicleDocument.vehicle_id == v.id)).all())
        cdoc_ids = set(db.scalars(select(CentralDocument.id).where(CentralDocument.resource_type == "VEHICLE", CentralDocument.resource_id == v.id, CentralDocument.deleted_at.is_(None))).all())
        doc_count = len(vdoc_ids.union(cdoc_ids))
        photo_count = len(db.scalars(select(VehiclePhoto.id).where(VehiclePhoto.vehicle_id == v.id)).all())
        results.append(vehicle_summary_dict(v, ins, doc_count, photo_count))
    return results


def get_vehicle(db: Session, user_id: str, vehicle_id: str) -> dict[str, Any]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    insurance = db.scalars(
        select(VehicleInsurancePolicy).where(VehicleInsurancePolicy.vehicle_id == v.id).order_by(VehicleInsurancePolicy.created_at.desc())
    ).first()
    status, days_left = calculate_insurance_status(insurance.expiry_date if insurance else None)

    photos = db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id).order_by(VehiclePhoto.uploaded_at.desc())).all()
    vdocs = db.scalars(select(VehicleDocument).where(VehicleDocument.vehicle_id == v.id).order_by(VehicleDocument.uploaded_at.desc())).all()
    cdocs = db.scalars(select(CentralDocument).where(CentralDocument.resource_type == "VEHICLE", CentralDocument.resource_id == v.id, CentralDocument.deleted_at.is_(None)).order_by(CentralDocument.created_at.desc())).all()

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
                "url": f"/api/vehicles/{v.id}/documents/{cd.id}/file",
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
    v = Vehicle(
        id=new_id("veh"),
        user_id=user_id,
        registration_number=data["registration_number"].upper().strip(),
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
    )
    db.add(v)
    db.flush()

    # Optional initial insurance
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
        )
        db.add(pol)

    db.commit()
    return get_vehicle(db, user_id, v.id)


def update_vehicle(db: Session, user_id: str, vehicle_id: str, data: dict[str, Any]) -> dict[str, Any]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    fields = [
        "registration_number", "category", "manufacturer", "model", "variant",
        "manufacturing_year", "fuel_type", "color", "chassis_number", "engine_number",
        "vin", "engine_capacity", "transmission", "owner_name", "ownership_type",
        "relationship_to_user", "main_image"
    ]
    for f in fields:
        if f in data:
            val = data[f]
            if f == "registration_number" and val:
                val = str(val).upper().strip()
            setattr(v, f, val)

    v.updated_at = utcnow()

    # Insurance update if included
    if "insurance" in data and isinstance(data["insurance"], dict):
        ins_data = data["insurance"]
        pol = db.scalars(
            select(VehicleInsurancePolicy).where(VehicleInsurancePolicy.vehicle_id == v.id).order_by(VehicleInsurancePolicy.created_at.desc())
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

        if pol:
            if "provider" in ins_data:
                pol.provider = ins_data["provider"]
            if "policy_number" in ins_data:
                pol.policy_number = ins_data["policy_number"]
            if "policy_type" in ins_data:
                pol.policy_type = ins_data["policy_type"]
            pol.start_date = start_dt
            pol.expiry_date = exp_dt
        elif ins_data.get("provider") and ins_data.get("policy_number"):
            pol = VehicleInsurancePolicy(
                id=new_id("vpol"),
                vehicle_id=v.id,
                provider=ins_data["provider"],
                policy_number=ins_data["policy_number"],
                policy_type=ins_data.get("policy_type", "Comprehensive"),
                start_date=start_dt,
                expiry_date=exp_dt,
            )
            db.add(pol)

    db.commit()
    return get_vehicle(db, user_id, v.id)


def delete_vehicle(db: Session, user_id: str, vehicle_id: str) -> bool:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    # Remove files
    photos = db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id)).all()
    for p in photos:
        try:
            if os.path.exists(p.stored_path):
                os.remove(p.stored_path)
        except OSError:
            pass

    docs = db.scalars(select(VehicleDocument).where(VehicleDocument.vehicle_id == v.id)).all()
    for d in docs:
        try:
            if os.path.exists(d.stored_path):
                os.remove(d.stored_path)
        except OSError:
            pass

    db.delete(v)
    db.commit()
    return True


def add_vehicle_photo(
    db: Session, user_id: str, vehicle_id: str, photo_category: str, filename: str, content: bytes, is_primary: bool = False
) -> dict[str, Any]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    photo_id = new_id("vpho")
    ext = Path(filename).suffix.lower() or ".jpg"
    safe_filename = f"{photo_id}{ext}"
    stored_path = VEHICLE_PHOTOS_DIR / safe_filename

    with open(stored_path, "wb") as f:
        f.write(content)

    existing_photos_count = len(db.scalars(select(VehiclePhoto.id).where(VehiclePhoto.vehicle_id == v.id)).all())
    set_as_primary = is_primary or existing_photos_count == 0

    if set_as_primary:
        # Demote existing primary photos
        for p in db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id)).all():
            p.is_primary = False

    photo = VehiclePhoto(
        id=photo_id,
        vehicle_id=v.id,
        photo_category=photo_category or "main",
        file_name=filename,
        stored_path=str(stored_path),
        mime_type="image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/webp",
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
    try:
        if os.path.exists(photo.stored_path):
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


def get_photo_file(db: Session, user_id: str, vehicle_id: str, photo_id: str) -> tuple[Path, str, str]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    photo = db.get(VehiclePhoto, photo_id)
    if not photo or photo.vehicle_id != v.id:
        raise ServiceError("Photo not found")
    path = Path(photo.stored_path)
    if not path.exists():
        raise ServiceError("Photo file not found on disk")
    return path, photo.mime_type, photo.file_name


def add_vehicle_document(
    db: Session, user_id: str, vehicle_id: str, document_type: str, document_name: str, filename: str, content: bytes, expiry_date: datetime | None = None
) -> dict[str, Any]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    doc_id = new_id("vdoc")
    ext = Path(filename).suffix.lower() or ".pdf"
    safe_filename = f"{doc_id}{ext}"
    stored_path = VEHICLE_DOCS_DIR / safe_filename

    with open(stored_path, "wb") as f:
        f.write(content)

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
        stored_path=str(stored_path),
        mime_type="application/pdf" if ext == ".pdf" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png",
        file_size=len(content),
        expiry_date=expiry_date,
        verification_status=status,
    )
    db.add(doc)

    # Sync with CentralDocument (single source of truth)
    cat = "insurance" if (document_type or "").lower() in ("insurance", "insurance_policy") else "vehicle"
    cdoc = CentralDocument(
        id=doc_id,
        user_id=v.user_id,
        document_name=document_name or filename,
        document_type=document_type or "other",
        category=cat,
        file_name=filename,
        stored_path=str(stored_path),
        mime_type=doc.mime_type,
        file_size=len(content),
        expiry_date=expiry_date,
        verification_status=status,
        resource_type="VEHICLE",
        resource_id=v.id,
    )
    db.add(cdoc)
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
    v = require_vehicle_owner(db, user_id, vehicle_id)
    doc = db.get(VehicleDocument, doc_id)
    cdoc = db.get(CentralDocument, doc_id)
    if not doc and not cdoc:
        raise ServiceError("Document not found")

    stored_path = doc.stored_path if doc else (cdoc.stored_path if cdoc else None)
    if stored_path:
        try:
            if os.path.exists(stored_path):
                os.remove(stored_path)
        except OSError:
            pass

    if doc:
        db.delete(doc)
    if cdoc:
        cdoc.deleted_at = utcnow()
        db.delete(cdoc)
    db.commit()
    return True


def get_document_file(db: Session, user_id: str, vehicle_id: str, doc_id: str) -> tuple[Path, str, str]:
    v = require_vehicle_owner(db, user_id, vehicle_id)
    doc = db.get(VehicleDocument, doc_id)
    if not doc:
        cdoc = db.get(CentralDocument, doc_id)
        if cdoc and cdoc.resource_type == "VEHICLE" and cdoc.resource_id == v.id and cdoc.deleted_at is None:
            p = Path(cdoc.stored_path)
            if not p.exists():
                raise ServiceError("Document file not found on disk")
            return p, cdoc.mime_type, cdoc.file_name
        raise ServiceError("Document not found")
    path = Path(doc.stored_path)
    if not path.exists():
        raise ServiceError("Document file not found on disk")
    return path, doc.mime_type, doc.file_name
