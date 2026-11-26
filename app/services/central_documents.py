"""Centralized Documents Management Service.

Provides a unified document repository for:
1. Personal documents & Driving Licence (USER)
2. Registered Vehicle documents (VEHICLE)
3. Accident Case documents (ACCIDENT_CASE)

Maintains single source of truth across all views.
"""
from __future__ import annotations

import hashlib
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import config
from app.db import Case, CaseMember, CentralDocument, User, Vehicle, new_id, utcnow
from app.services.common import PermissionDenied, ServiceError

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return clean[:100] or "document.pdf"


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


def _check_access(db: Session, user_id: str, doc: CentralDocument) -> None:
    """Verifies that user_id has permission to view/modify this document."""
    if doc.user_id == user_id:
        return

    # If linked to a vehicle, check vehicle owner
    if doc.resource_type == "VEHICLE" and doc.resource_id:
        veh = db.get(Vehicle, doc.resource_id)
        if veh and veh.user_id == user_id:
            return

    # If linked to an accident case, check case membership
    if doc.resource_type == "ACCIDENT_CASE" and doc.resource_id:
        member = db.get(CaseMember, (doc.resource_id, user_id))
        if member:
            return

    raise PermissionDenied("You do not have permission to access this document")


def _get_accessible_filters(db: Session, user_id: str) -> Any:
    """Returns SQLAlchemy condition matching all documents accessible to user_id."""
    user_vehicles = db.scalars(select(Vehicle.id).where(Vehicle.user_id == user_id)).all()
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

    return and_(CentralDocument.deleted_at.is_(None), or_(*conditions))


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
        "issuing_authority": doc.issuing_authority,
        "issue_date": doc.issue_date.isoformat(timespec="minutes") if doc.issue_date else None,
        "expiry_date": doc.expiry_date.isoformat(timespec="minutes") if doc.expiry_date else None,
        "verification_status": doc.verification_status,
        "notes": doc.notes,
        "resource_type": doc.resource_type,
        "resource_id": doc.resource_id,
        "resource_label": resource_label,
        "resource_meta": resource_meta,
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
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                CentralDocument.document_name.ilike(term),
                CentralDocument.file_name.ilike(term),
                CentralDocument.document_number.ilike(term),
                CentralDocument.issuing_authority.ilike(term),
                CentralDocument.notes.ilike(term),
            )
        )

    # Sorting
    if sort_by == "document_name":
        order_col = CentralDocument.document_name.asc() if sort_dir == "asc" else CentralDocument.document_name.desc()
    elif sort_by == "expiry_date":
        order_col = CentralDocument.expiry_date.asc() if sort_dir == "asc" else CentralDocument.expiry_date.desc()
    else:
        order_col = CentralDocument.created_at.asc() if sort_dir == "asc" else CentralDocument.created_at.desc()

    stmt = stmt.order_by(order_col)
    docs = db.scalars(stmt).all()

    # Convert to dicts
    results = [doc_to_dict(db, d) for d in docs]

    # Status filtering (post-calculation)
    if status and status != "all":
        results = [d for d in results if d["status"] == status]

    return results


def get_document_summary(db: Session, user_id: str) -> dict[str, Any]:
    """Dynamically computes document statistics from stored metadata."""
    stmt = select(CentralDocument).where(_get_accessible_filters(db, user_id))
    docs = db.scalars(stmt).all()

    total = len(docs)
    valid_count = 0
    expiring_soon_count = 0
    expired_count = 0

    category_counts: dict[str, int] = {
        "personal": 0,
        "driving_licence": 0,
        "vehicle": 0,
        "insurance": 0,
        "medical": 0,
        "accident_case": 0,
        "other": 0,
    }

    for d in docs:
        st, _ = calculate_document_status(d.expiry_date)
        if st == "valid":
            valid_count += 1
        elif st == "expiring_soon":
            expiring_soon_count += 1
        elif st == "expired":
            expired_count += 1

        # Count categories
        cat = d.category or "other"
        if cat in category_counts:
            category_counts[cat] += 1
        elif d.resource_type == "VEHICLE":
            category_counts["vehicle"] += 1
        elif d.resource_type == "ACCIDENT_CASE":
            category_counts["accident_case"] += 1
        else:
            category_counts["other"] += 1

        # Cross-category counts
        if d.document_type == "driving_licence" and cat != "driving_licence":
            category_counts["driving_licence"] += 1
        if (cat == "vehicle" or d.resource_type == "VEHICLE") and d.document_type in ("insurance", "insurance_policy") and cat != "insurance":
            category_counts["insurance"] += 1
        if d.document_type in ("medical_report", "hospital_bill") and cat != "medical":
            category_counts["medical"] += 1

    return {
        "total": total,
        "valid": valid_count,
        "expiring_soon": expiring_soon_count,
        "expired": expired_count,
        "categories": category_counts,
    }


def get_document(db: Session, user_id: str, doc_id: str) -> dict[str, Any]:
    """Retrieves an individual document after verifying authorization."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)
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
) -> dict[str, Any]:
    """Uploads and creates a new CentralDocument record."""
    ext, mime_type = _validate_file(file_name, content)
    doc_id = new_id("cdoc")
    safe_name = _sanitize_filename(file_name)
    digest = hashlib.sha256(content).hexdigest()

    # Validate resource ownership
    if resource_type == "VEHICLE":
        if not resource_id:
            raise ServiceError("Vehicle ID is required for vehicle documents")
        veh = db.get(Vehicle, resource_id)
        if not veh or veh.user_id != user_id:
            raise PermissionDenied("You do not have permission to associate documents with this vehicle")
    elif resource_type == "ACCIDENT_CASE":
        if not resource_id:
            raise ServiceError("Case ID is required for accident case documents")
        member = db.get(CaseMember, (resource_id, user_id))
        if not member:
            raise PermissionDenied("You do not have permission to associate documents with this accident case")
    else:
        resource_type = "USER"
        resource_id = user_id

    # Store file in user's documents directory
    dest_dir = config.CENTRAL_DOCS_DIR / user_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{doc_id}_{safe_name}"
    dest_path.write_bytes(content)

    doc = CentralDocument(
        id=doc_id,
        user_id=user_id,
        document_name=document_name.strip() or safe_name,
        document_type=document_type.strip().lower() or "other",
        category=category.strip().lower() or "other",
        file_name=safe_name,
        stored_path=str(dest_path),
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
    )
    db.add(doc)
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
    if not doc or doc.deleted_at is not None:
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
            if not veh or veh.user_id != user_id:
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
) -> dict[str, Any]:
    """Replaces the underlying physical document file while preserving metadata."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    ext, mime_type = _validate_file(file_name, content)
    safe_name = _sanitize_filename(file_name)
    digest = hashlib.sha256(content).hexdigest()

    dest_dir = config.CENTRAL_DOCS_DIR / user_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{doc_id}_{safe_name}"
    dest_path.write_bytes(content)

    doc.file_name = safe_name
    doc.stored_path = str(dest_path)
    doc.mime_type = mime_type
    doc.file_size = len(content)
    doc.sha256 = digest
    doc.updated_at = utcnow()

    db.commit()
    db.refresh(doc)
    return doc_to_dict(db, doc)


def delete_document(db: Session, user_id: str, doc_id: str, hard: bool = False) -> None:
    """Soft deletes or removes a document after verifying authorization."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    if hard:
        # Also clean up disk file
        try:
            p = Path(doc.stored_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass
        db.delete(doc)
    else:
        doc.deleted_at = utcnow()

    db.commit()


def get_document_file(db: Session, user_id: str, doc_id: str) -> tuple[str, str, str]:
    """Retrieves file path, MIME type and filename for download or preview."""
    doc = db.get(CentralDocument, doc_id)
    if not doc or doc.deleted_at is not None:
        raise ServiceError("Document not found")
    _check_access(db, user_id, doc)

    path = Path(doc.stored_path)
    if not path.exists():
        raise ServiceError(f"Stored file '{doc.file_name}' not found on server")

    return str(path), doc.mime_type, doc.file_name
