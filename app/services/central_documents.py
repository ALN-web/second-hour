"""Centralized Documents Management Service.

Provides a unified document repository for:
1. Personal documents & Driving Licence (USER)
2. Registered Vehicle documents (VEHICLE)
3. Accident Case documents (ACCIDENT_CASE)

Maintains single source of truth, document version history, and append-only access auditing.
"""
from __future__ import annotations

import hashlib
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from app import config
from app.db import (
    Case,
    CaseMember,
    CentralDocument,
    DocumentAccessLog,
    DocumentVersion,
    User,
    Vehicle,
    new_id,
    utcnow,
)
from app.services.common import PermissionDenied, ServiceError, iso
from app.storage import get_storage

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return clean[:100] or "document.pdf"


def _mask_doc_number(doc_type: str, number: str | None) -> str | None:
    """Mask sensitive national and financial document numbers."""
    if not number:
        return None
    clean = re.sub(r"\s+", "", str(number))
    if len(clean) <= 4:
        return f"****{clean}"
    if doc_type.lower() in ("aadhaar", "uidai"):
        return f"XXXX-XXXX-{clean[-4:]}"
    elif doc_type.lower() == "pan":
        return f"{clean[:2]}XXXXX{clean[-2:]}"
    return f"{clean[:3]}****{clean[-4:]}"


def _validate_file(filename: str, content: bytes) -> tuple[str, str]:
    if not content:
        raise ServiceError("Uploaded file is empty")
    if len(content) > MAX_FILE_BYTES:
        raise ServiceError(f"File size exceeds maximum allowed limit of {MAX_FILE_BYTES // (1024 * 1024)} MB")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ServiceError(f"Unsupported file format '{ext}'. Allowed formats: PDF, PNG, JPG, JPEG, WEBP")

    # Magic byte verification
    mime_type, _ = mimetypes.guess_type(filename)
    if ext == ".pdf":
        if not content.startswith(b"%PDF"):
            raise ServiceError("Corrupted or invalid PDF file header")
        mime_type = "application/pdf"
    elif ext in (".jpg", ".jpeg"):
        if not (content.startswith(b"\xff\xd8\xff")):
            raise ServiceError("Corrupted or invalid JPEG image header")
        mime_type = "image/jpeg"
    elif ext == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ServiceError("Corrupted or invalid PNG image header")
        mime_type = "image/png"
    elif ext == ".webp":
        if not (content.startswith(b"RIFF") and b"WEBP" in content[:16]):
            raise ServiceError("Corrupted or invalid WEBP image header")
        mime_type = "image/webp"

    return ext, mime_type or "application/octet-stream"


def calculate_document_status(expiry_date: datetime | None) -> tuple[str, int | None]:
    """Calculates status: 'valid', 'expiring_soon', or 'expired' and days_left."""
    if expiry_date is None:
        return "valid", None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days_left = (expiry_date.date() - now.date()).days
    if days_left < 0:
        return "expired", days_left
    elif days_left <= 30:
        return "expiring_soon", days_left
    else:
        return "valid", days_left


def record_document_access(
    db: Session,
    document_id: str,
    user_id: str,
    action: str,  # 'view', 'download', 'upload', 'replace', 'delete'
    access_channel: str = "web_dashboard",
    purpose: str | None = None,
    case_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DocumentAccessLog:
    """Record an append-only audit trail event for document access."""
    log_entry = DocumentAccessLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        access_channel=access_channel,
        purpose=purpose,
        case_id=case_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log_entry)
    db.flush()
    return log_entry


def _check_access(db: Session, user_id: str, doc: CentralDocument) -> None:
    """Verifies that user_id has permission to view/modify this document."""
    if doc.user_id == user_id:
        return

    # If linked to a vehicle, check vehicle owner
    if doc.resource_type == "VEHICLE" and doc.resource_id:
        veh = db.get(Vehicle, doc.resource_id)
        if veh and veh.user_id == user_id and veh.is_active:
            return

    # If linked to an accident case, check case membership
    if doc.resource_type == "ACCIDENT_CASE" and doc.resource_id:
        member = db.get(CaseMember, (doc.resource_id, user_id))
        if member:
            return

    raise PermissionDenied("You do not have permission to access this document")


def _get_accessible_filters(db: Session, user_id: str) -> Any:
    """Returns SQLAlchemy condition matching all documents accessible to user_id."""
    user_vehicles = db.scalars(
        select(Vehicle.id).where(Vehicle.user_id == user_id, Vehicle.is_active.is_(True), Vehicle.deleted_at.is_(None))
    ).all()
    user_cases = db.scalars(select(CaseMember.case_id).where(CaseMember.user_id == user_id)).all()

    conditions = [CentralDocument.user_id == user_id]
    if user_vehicles:
        conditions.append(
            and_(CentralDocument.resource_type == "VEHICLE", CentralDocument.resource_id.in_(user_vehicles))
        )
    if user_cases:
        conditions.append(
            and_(CentralDocument.resource_type == "ACCIDENT_CASE", CentralDocument.resource_id.in_(user_cases))
        )

    return and_(CentralDocument.deleted_at.is_(None), CentralDocument.is_active.is_(True), or_(*conditions))


def _resolve_resource_meta(db: Session, doc: CentralDocument) -> tuple[str, dict[str, Any] | None]:
    """Resolves human-friendly resource badge and metadata."""
    if doc.resource_type == "VEHICLE" and doc.resource_id:
        veh = db.get(Vehicle, doc.resource_id)
        if veh:
            label = f"{veh.registration_number} · {veh.manufacturer} {veh.model}"
            meta = {
                "vehicle_id": veh.id,
                "registration_number": veh.registration_number,
                "manufacturer": veh.manufacturer,
                "model": veh.model,
                "variant": veh.variant,
            }
            return label, meta

    elif doc.resource_type == "ACCIDENT_CASE" and doc.resource_id:
        case = db.get(Case, doc.resource_id)
        if case:
            label = f"{case.case_number} · {case.victim_display_name or 'Accident Case'}"
            meta = {
                "case_id": case.id,
                "case_number": case.case_number,
                "victim_name": case.victim_display_name,
                "hospital": case.hospital_name,
            }
            return label, meta

    return "Personal Profile", None


def doc_to_dict(db: Session, doc: CentralDocument) -> dict[str, Any]:
    """Converts a CentralDocument instance to a rich client-facing dict."""
    status, days_left = calculate_document_status(doc.expiry_date)
    resource_label, resource_meta = _resolve_resource_meta(db, doc)

    # Check version count
    version_count = len(
        db.scalars(select(DocumentVersion.id).where(DocumentVersion.document_id == doc.id)).all()
    )
    if version_count == 0:
        version_count = doc.current_version or 1

    return {
        "id": doc.id,
        "user_id": doc.user_id,
        "document_name": doc.document_name,
        "document_type": doc.document_type,
        "category": doc.category,
        "file_name": doc.file_name,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "sha256": doc.sha256,
        "document_number": doc.document_number,
        "document_number_masked": _mask_doc_number(doc.document_type, doc.document_number),
        "issuing_authority": doc.issuing_authority,
        "issue_date": doc.issue_date.isoformat(timespec="minutes") if doc.issue_date else None,
        "expiry_date": doc.expiry_date.isoformat(timespec="minutes") if doc.expiry_date else None,
        "verification_status": doc.verification_status,
        "notes": doc.notes,
        "resource_type": doc.resource_type,
        "resource_id": doc.resource_id,
        "resource_label": resource_label,
        "resource_meta": resource_meta,
        "current_version": doc.current_version or 1,
        "version_count": version_count,
        "status": status,
        "days_left": days_left,
        "download_url": f"/api/documents/{doc.id}/file",
        "preview_url": f"/api/documents/{doc.id}/file",
        "created_at": doc.created_at.isoformat(timespec="minutes") if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat(timespec="minutes") if doc.updated_at else None,
    }


def list_documents(
    db: Session,
    user_id: str,
    category: str | None = None,
    status: str | None = None,
    vehicle_id: str | None = None,
    case_id: str | None = None,
    search: str | None = None,
    sort_by: str = "uploaded_at",
    sort_dir: str = "desc",
) -> list[dict[str, Any]]:
    """Lists accessible documents with full filtering, sorting and search."""
    stmt = select(CentralDocument).where(_get_accessible_filters(db, user_id))

    # Category filtering (including smart aliases)
    if category and category != "all":
        cat_lower = category.lower().strip()
        if cat_lower == "personal":
            stmt = stmt.where(CentralDocument.category.in_(["personal", "identity", "address_proof"]))
        elif cat_lower == "driving_licence":
            stmt = stmt.where(
                or_(
                    CentralDocument.category == "driving_licence",
                    CentralDocument.document_type == "driving_licence",
                )
            )
        elif cat_lower == "vehicle":
            stmt = stmt.where(
                or_(
                    CentralDocument.category == "vehicle",
                    CentralDocument.resource_type == "VEHICLE",
                )
            )
        elif cat_lower == "insurance":
            stmt = stmt.where(
                or_(
                    CentralDocument.category == "insurance",
                    CentralDocument.document_type.in_(["insurance", "insurance_policy"]),
                )
            )
        elif cat_lower == "medical":
            stmt = stmt.where(
                or_(
                    CentralDocument.category == "medical",
                    CentralDocument.document_type.in_(["medical_report", "hospital_bill", "prescription", "diagnostic_report"]),
                )
            )
        elif cat_lower == "accident_case":
            stmt = stmt.where(
                or_(
                    CentralDocument.category == "accident_case",
                    CentralDocument.resource_type == "ACCIDENT_CASE",
                )
            )
        else:
            stmt = stmt.where(CentralDocument.category == cat_lower)

    # Filter by vehicle
    if vehicle_id and vehicle_id != "all":
        stmt = stmt.where(and_(CentralDocument.resource_type == "VEHICLE", CentralDocument.resource_id == vehicle_id))

    # Filter by case
    if case_id and case_id != "all":
        stmt = stmt.where(and_(CentralDocument.resource_type == "ACCIDENT_CASE", CentralDocument.resource_id == case_id))

    # Free text search
    if search and search.strip():
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                CentralDocument.document_name.ilike(q),
                CentralDocument.file_name.ilike(q),
                CentralDocument.document_number.ilike(q),
                CentralDocument.issuing_authority.ilike(q),
            )
        )

    # Sorting
    if sort_by == "name":
        order_col = CentralDocument.document_name.asc() if sort_dir == "asc" else CentralDocument.document_name.desc()
    elif sort_by == "expiry":
        order_col = CentralDocument.expiry_date.asc() if sort_dir == "asc" else CentralDocument.expiry_date.desc()
    else:
        order_col = CentralDocument.created_at.asc() if sort_dir == "asc" else CentralDocument.created_at.desc()

    docs = db.scalars(stmt.order_by(order_col)).all()

    # Status post-filter
    res = []
    for d in docs:
        d_dict = doc_to_dict(db, d)
        if status and status != "all":
            if d_dict["status"] != status:
                continue
        res.append(d_dict)

    return res


def get_document_summary(db: Session, user_id: str) -> dict[str, Any]:
    """Generates wallet metrics: category counts, status breakdown, upcoming expiries."""
    all_docs = db.scalars(select(CentralDocument).where(_get_accessible_filters(db, user_id))).all()

    total_count = len(all_docs)
    category_counts: dict[str, int] = {
        "all": total_count,
        "personal": 0,
        "driving_licence": 0,
        "vehicle": 0,
        "insurance": 0,
        "medical": 0,
        "accident_case": 0,
    }

    valid_count = 0
    expiring_soon_count = 0
    expired_count = 0
    critical_alerts = []

    for d in all_docs:
        # Category breakdown
        cat = d.category.lower() if d.category else "other"
        if cat in ("personal", "identity", "address_proof"):
            category_counts["personal"] += 1
        elif cat == "driving_licence" or d.document_type == "driving_licence":
            category_counts["driving_licence"] += 1
        elif cat == "vehicle" or d.resource_type == "VEHICLE":
            category_counts["vehicle"] += 1
        elif cat == "insurance" or d.document_type in ("insurance", "insurance_policy"):
            category_counts["insurance"] += 1
        elif cat == "medical" or d.document_type in ("medical_report", "hospital_bill"):
            category_counts["medical"] += 1
        elif cat == "accident_case" or d.resource_type == "ACCIDENT_CASE":
            category_counts["accident_case"] += 1

        # Status breakdown
        st, days = calculate_document_status(d.expiry_date)
        if st == "valid":
            valid_count += 1
        elif st == "expiring_soon":
            expiring_soon_count += 1
            critical_alerts.append({
                "id": d.id,
                "document_name": d.document_name,
                "days_left": days,
                "expiry_date": d.expiry_date.isoformat(timespec="minutes") if d.expiry_date else None,
                "type": "expiring_soon",
            })
        elif st == "expired":
            expired_count += 1
            critical_alerts.append({
                "id": d.id,
                "document_name": d.document_name,
                "days_left": days,
                "expiry_date": d.expiry_date.isoformat(timespec="minutes") if d.expiry_date else None,
                "type": "expired",
            })

    return {
        "total": total_count,
        "valid": valid_count,
        "expiring_soon": expiring_soon_count,
        "expired": expired_count,
        "total_count": total_count,
        "valid_count": valid_count,
        "expiring_soon_count": expiring_soon_count,
        "expired_count": expired_count,
        "categories": category_counts,
        "category_counts": category_counts,
        "critical_alerts": critical_alerts[:5],
    }


def get_document(
    db: Session,
    user_id: str,
    doc_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Retrieves document metadata and logs view event."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    # Append-only audit log
    record_document_access(
        db,
        document_id=doc.id,
        user_id=user_id,
        action="view_metadata",
        access_channel="web_dashboard",
        purpose="user_view_metadata",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()

    return doc_to_dict(db, doc)


def create_document(
    db: Session,
    user_id: str,
    document_name: str,
    category: str,
    document_type: str,
    file_name: str,
    content: bytes,
    document_number: str | None = None,
    issuing_authority: str | None = None,
    issue_date: datetime | None = None,
    expiry_date: datetime | None = None,
    notes: str | None = None,
    resource_type: str = "USER",
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Uploads document to private object storage, creates central record, version 1, and access log."""
    ext, mime_type = _validate_file(file_name, content)
    safe_name = _sanitize_filename(file_name)
    digest = hashlib.sha256(content).hexdigest()
    doc_id = new_id("cdoc")

    # Resource association verification
    if resource_type == "VEHICLE" and resource_id:
        veh = db.get(Vehicle, resource_id)
        if not veh or veh.user_id != user_id or not veh.is_active:
            raise PermissionDenied("You do not own this vehicle")
    elif resource_type == "ACCIDENT_CASE" and resource_id:
        member = db.get(CaseMember, (resource_id, user_id))
        if not member:
            raise PermissionDenied("You are not a member of this accident case")
    else:
        resource_type = "USER"
        resource_id = user_id

    # Storage key: users/{user_id}/documents/{doc_id}/v1_{safe_name}
    storage_key = f"users/{user_id}/documents/{doc_id}/v1_{safe_name}"
    storage = get_storage()
    storage.put_object(storage_key, content, mime_type)
    stored_path = storage.get_object_path(storage_key)

    doc = CentralDocument(
        id=doc_id,
        user_id=user_id,
        document_name=document_name.strip() or safe_name,
        document_type=document_type.strip().lower() or "other",
        category=category.strip().lower() or "other",
        file_name=safe_name,
        stored_path=stored_path,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=len(content),
        sha256=digest,
        document_number=document_number.strip() if document_number else None,
        issuing_authority=issuing_authority.strip() if issuing_authority else None,
        issue_date=issue_date,
        expiry_date=expiry_date,
        verification_status="verified",
        notes=notes.strip() if notes else None,
        resource_type=resource_type,
        resource_id=resource_id,
        current_version=1,
        is_active=True,
    )
    db.add(doc)
    db.flush()

    # Initial DocumentVersion
    version = DocumentVersion(
        id=new_id("dver"),
        document_id=doc.id,
        version_number=1,
        storage_key=storage_key,
        file_name=safe_name,
        mime_type=mime_type,
        file_size_bytes=len(content),
        sha256=digest,
        uploaded_by=user_id,
        change_summary="Initial document upload",
    )
    db.add(version)

    # Append-only audit log
    record_document_access(
        db,
        document_id=doc.id,
        user_id=user_id,
        action="upload",
        access_channel="web_dashboard",
        purpose="user_document_upload",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()
    db.refresh(doc)
    return doc_to_dict(db, doc)


def update_document(
    db: Session,
    user_id: str,
    doc_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Updates document metadata."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    if "document_name" in data and data["document_name"]:
        doc.document_name = str(data["document_name"]).strip()
    if "category" in data and data["category"]:
        doc.category = str(data["category"]).strip().lower()
    if "document_type" in data and data["document_type"]:
        doc.document_type = str(data["document_type"]).strip().lower()
    if "document_number" in data:
        doc.document_number = str(data["document_number"]).strip() if data["document_number"] else None
    if "issuing_authority" in data:
        doc.issuing_authority = str(data["issuing_authority"]).strip() if data["issuing_authority"] else None
    if "notes" in data:
        doc.notes = str(data["notes"]).strip() if data["notes"] else None

    if "issue_date" in data:
        if isinstance(data["issue_date"], datetime):
            doc.issue_date = data["issue_date"]
        elif isinstance(data["issue_date"], str) and data["issue_date"]:
            try:
                doc.issue_date = datetime.fromisoformat(data["issue_date"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        elif data["issue_date"] is None:
            doc.issue_date = None

    if "expiry_date" in data:
        if isinstance(data["expiry_date"], datetime):
            doc.expiry_date = data["expiry_date"]
        elif isinstance(data["expiry_date"], str) and data["expiry_date"]:
            try:
                doc.expiry_date = datetime.fromisoformat(data["expiry_date"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        elif data["expiry_date"] is None:
            doc.expiry_date = None

    if "resource_type" in data and "resource_id" in data:
        res_type = data["resource_type"]
        res_id = data["resource_id"]
        if res_type == "VEHICLE" and res_id:
            veh = db.get(Vehicle, res_id)
            if not veh or veh.user_id != user_id or not veh.is_active:
                raise PermissionDenied("You do not own this vehicle")
            doc.resource_type = "VEHICLE"
            doc.resource_id = res_id
        elif res_type == "ACCIDENT_CASE" and res_id:
            member = db.get(CaseMember, (res_id, user_id))
            if not member:
                raise PermissionDenied("You are not a member of this accident case")
            doc.resource_type = "ACCIDENT_CASE"
            doc.resource_id = res_id
        elif res_type == "USER":
            doc.resource_type = "USER"
            doc.resource_id = user_id

    doc.updated_at = utcnow()
    db.commit()
    db.refresh(doc)
    return doc_to_dict(db, doc)


def replace_document_file(
    db: Session,
    user_id: str,
    doc_id: str,
    file_name: str,
    content: bytes,
    change_summary: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Replaces document file with a new version while archiving and preserving previous version."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    ext, mime_type = _validate_file(file_name, content)
    safe_name = _sanitize_filename(file_name)
    digest = hashlib.sha256(content).hexdigest()

    # Ensure existing versions exist; if version 1 wasn't archived yet, archive current document as v1
    existing_versions = db.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_number.desc())
    ).all()

    if not existing_versions:
        # Archive current document as version 1
        current_v = DocumentVersion(
            id=new_id("dver"),
            document_id=doc.id,
            version_number=1,
            storage_key=doc.storage_key or f"users/{doc.user_id}/documents/{doc.id}/v1_{doc.file_name}",
            file_name=doc.file_name,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size,
            sha256=doc.sha256 or digest,
            uploaded_by=doc.user_id,
            change_summary="Original version",
            created_at=doc.created_at,
        )
        db.add(current_v)
        db.flush()
        next_version_num = 2
    else:
        next_version_num = max(v.version_number for v in existing_versions) + 1

    # Store new version with versioned storage key
    storage_key = f"users/{user_id}/documents/{doc_id}/v{next_version_num}_{safe_name}"
    storage = get_storage()
    storage.put_object(storage_key, content, mime_type)
    stored_path = storage.get_object_path(storage_key)

    new_version = DocumentVersion(
        id=new_id("dver"),
        document_id=doc.id,
        version_number=next_version_num,
        storage_key=storage_key,
        file_name=safe_name,
        mime_type=mime_type,
        file_size_bytes=len(content),
        sha256=digest,
        uploaded_by=user_id,
        change_summary=change_summary or f"Replaced with version {next_version_num}",
    )
    db.add(new_version)

    # Update active document pointer to new version
    doc.file_name = safe_name
    doc.stored_path = stored_path
    doc.storage_key = storage_key
    doc.mime_type = mime_type
    doc.file_size = len(content)
    doc.sha256 = digest
    doc.current_version = next_version_num
    doc.updated_at = utcnow()

    # Append-only audit log
    record_document_access(
        db,
        document_id=doc.id,
        user_id=user_id,
        action="replace",
        access_channel="web_dashboard",
        purpose=f"replaced_to_version_{next_version_num}",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()
    db.refresh(doc)
    return doc_to_dict(db, doc)


def list_document_versions(db: Session, user_id: str, doc_id: str) -> list[dict[str, Any]]:
    """Retrieve full revision history for a document."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    versions = db.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_number.desc())
    ).all()

    # If no recorded versions yet, synthesize current version
    if not versions:
        return [
            {
                "version_number": 1,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "sha256": doc.sha256,
                "uploaded_by": doc.user_id,
                "change_summary": "Original file",
                "is_current": True,
                "created_at": iso(doc.created_at),
                "download_url": f"/api/documents/{doc.id}/versions/1/file",
            }
        ]

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "file_name": v.file_name,
            "file_size": v.file_size_bytes,
            "mime_type": v.mime_type,
            "sha256": v.sha256,
            "uploaded_by": v.uploaded_by,
            "change_summary": v.change_summary,
            "is_current": v.version_number == doc.current_version,
            "created_at": iso(v.created_at),
            "download_url": f"/api/documents/{doc.id}/versions/{v.version_number}/file",
        }
        for v in versions
    ]


def get_document_version_file(
    db: Session,
    user_id: str,
    doc_id: str,
    version_number: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str, str]:
    """Retrieve file path, MIME type, and filename for a specific historical version."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    ver = db.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id, DocumentVersion.version_number == version_number)
    ).first()

    storage = get_storage()
    if ver:
        file_path = storage.get_object_path(ver.storage_key)
        mime = ver.mime_type
        filename = ver.file_name
    elif version_number == 1 or version_number == doc.current_version:
        file_path = storage.get_object_path(doc.storage_key or doc.stored_path)
        mime = doc.mime_type
        filename = doc.file_name
    else:
        raise ServiceError(f"Version {version_number} not found for document")

    # Record access log
    record_document_access(
        db,
        document_id=doc.id,
        user_id=user_id,
        action="download",
        access_channel="web_dashboard",
        purpose=f"download_version_{version_number}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()

    return file_path, mime, filename


def list_document_access_logs(db: Session, user_id: str, doc_id: str) -> list[dict[str, Any]]:
    """Retrieve append-only audit trail of document view/download/replace events."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    logs = db.scalars(
        select(DocumentAccessLog).where(DocumentAccessLog.document_id == doc.id).order_by(DocumentAccessLog.accessed_at.desc()).limit(100)
    ).all()

    return [
        {
            "id": log.id,
            "document_id": log.document_id,
            "user_id": log.user_id,
            "action": log.action,
            "access_channel": log.access_channel,
            "purpose": log.purpose,
            "case_id": log.case_id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "accessed_at": iso(log.accessed_at),
        }
        for log in logs
    ]


def delete_document(db: Session, user_id: str, doc_id: str, hard: bool = False) -> None:
    """Soft deletes document after verifying authorization, recording access audit log."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    doc.deleted_at = utcnow()
    doc.is_active = False

    # Record append-only audit log
    record_document_access(
        db,
        document_id=doc.id,
        user_id=user_id,
        action="delete",
        access_channel="web_dashboard",
        purpose="user_delete_document",
    )

    db.commit()


def get_document_file(
    db: Session,
    user_id: str,
    doc_id: str,
    action: str = "download",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str, str]:
    """Retrieves file path, MIME type and filename for download or preview, logging the event."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None or not doc.is_active:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    storage = get_storage()
    if doc.storage_key and storage.exists(doc.storage_key):
        file_path = storage.get_object_path(doc.storage_key)
    else:
        path = Path(doc.stored_path)
        if not path.exists():
            raise ServiceError(f"Stored file '{doc.file_name}' not found on server")
        file_path = str(path)

    # Record access log
    record_document_access(
        db,
        document_id=doc.id,
        user_id=user_id,
        action=action,
        access_channel="web_dashboard",
        purpose=f"document_{action}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()

    return file_path, doc.mime_type, doc.file_name
