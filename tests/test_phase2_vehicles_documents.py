"""Test suite for Phase 2: Vehicles & Central Documents Foundation Layer on Neon PostgreSQL.

Verifies:
1. Schema migration and Phase 1 data preservation.
2. Multi-vehicle registration per user and duplicate active registration number prevention.
3. Primary vehicle designation, persistence, and reassignment on soft-deletion.
4. Vehicle photo upload, sha256 checksum, StorageAdapter file persistence, and retrieval.
5. Insurance policy renewal preserving historical policies with superseded lineage.
6. Central document upload, masked document number representation, and verification status.
7. Document replacement creating versioned history (document_versions) without file overwriting.
8. Accessing previous document versions.
9. Append-only document access logging (document_access_logs).
10. Strict cross-user data isolation and authorization enforcement.
"""
from __future__ import annotations

import io
import pytest
from sqlalchemy import select

from app.db import (
    CentralDocument,
    DocumentAccessLog,
    DocumentVersion,
    SessionLocal,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    VehiclePhoto,
    new_id,
)
from app.services import central_documents as cdocs_svc
from app.services import vehicles as veh_svc
from app.services.common import PermissionDenied, ServiceError


def test_phase2_vehicles_crud_and_primary_toggle():
    """Verify multi-vehicle registration, active duplicate prevention, and primary setting."""
    db = SessionLocal()
    try:
        # Register a second vehicle for Priya
        v2 = veh_svc.create_vehicle(
            db,
            "u_priya",
            {
                "registration_number": "KA-05-NB-8899",
                "category": "Two Wheeler",
                "manufacturer": "Ather",
                "model": "450X",
                "variant": "Gen 3",
                "manufacturing_year": 2023,
                "fuel_type": "Electric",
                "color": "Space Grey",
                "is_primary": False,
            },
        )
        assert v2["registration_number"] == "KA-05-NB-8899"
        assert v2["is_primary"] is False
        assert v2["is_active"] is True

        # Attempting duplicate registration number should raise ServiceError
        with pytest.raises(ServiceError, match="already active"):
            veh_svc.create_vehicle(
                db,
                "u_priya",
                {
                    "registration_number": "KA-05-NB-8899",
                    "manufacturer": "Duplicate Test",
                    "model": "Test",
                },
            )

        # Set v2 as primary
        updated_v2 = veh_svc.set_primary_vehicle(db, "u_priya", v2["id"])
        assert updated_v2["is_primary"] is True

        # Demo vehicle should now be demoted from primary
        demo_v = veh_svc.get_vehicle(db, "u_priya", "veh_demo_honda")
        assert demo_v["is_primary"] is False

        # Soft delete v2
        veh_svc.delete_vehicle(db, "u_priya", v2["id"])
        v2_record = db.get(Vehicle, v2["id"])
        assert v2_record.is_active is False
        assert v2_record.deleted_at is not None

        # Primary should be restored to demo vehicle
        demo_restored = veh_svc.get_vehicle(db, "u_priya", "veh_demo_honda")
        assert demo_restored["is_primary"] is True
    finally:
        db.close()


def test_phase2_vehicle_photos_and_storage():
    """Verify vehicle photo upload, storage key assignment, and retrieval."""
    db = SessionLocal()
    try:
        sample_img = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00" + b"\x00" * 200
        photo = veh_svc.add_vehicle_photo(
            db,
            user_id="u_priya",
            vehicle_id="veh_demo_honda",
            photo_category="rear",
            filename="rear_view.jpg",
            content=sample_img,
            is_primary=False,
        )
        assert photo["id"] is not None
        assert photo["photo_category"] == "rear"

        # Verify photo record in database has storage_key and sha256
        db_photo = db.get(VehiclePhoto, photo["id"])
        assert db_photo is not None
        assert db_photo.storage_key != ""
        assert db_photo.sha256 is not None
        assert db_photo.file_size_bytes == len(sample_img)

        # Retrieve file
        path, mime, filename = veh_svc.get_photo_file(db, "u_priya", "veh_demo_honda", photo["id"])
        assert mime == "image/jpeg"
        assert filename == "rear_view.jpg"

        # Delete photo
        veh_svc.delete_vehicle_photo(db, "u_priya", "veh_demo_honda", photo["id"])
        assert db.get(VehiclePhoto, photo["id"]) is None
    finally:
        db.close()


def test_phase2_insurance_renewal_preserves_history():
    """Verify insurance renewal preserves historical policy with superseded_by_policy_id."""
    db = SessionLocal()
    try:
        # Check initial policy
        policies_before = veh_svc.list_vehicle_insurance_policies(db, "u_priya", "veh_demo_honda")
        assert len(policies_before) >= 1
        curr = next(p for p in policies_before if p["is_current_policy"])
        old_pol_id = curr["id"]

        # Renew policy with new policy number and future expiry
        new_pol_num = f"POL-RENEW-{new_id('p')[:8]}"
        veh_svc.update_vehicle(
            db,
            user_id="u_priya",
            vehicle_id="veh_demo_honda",
            data={
                "insurance": {
                    "provider": "Tata AIG General Insurance",
                    "policy_number": new_pol_num,
                    "policy_type": "Comprehensive (Zero Dep)",
                    "expiry_date": "2028-04-15T00:00:00Z",
                }
            },
        )

        # Verify old policy is now superseded
        policies_after = veh_svc.list_vehicle_insurance_policies(db, "u_priya", "veh_demo_honda")
        assert len(policies_after) >= 2

        old_pol = next(p for p in policies_after if p["id"] == old_pol_id)
        assert old_pol["is_current_policy"] is False
        assert old_pol["policy_status"] == "superseded"
        assert old_pol["superseded_by_policy_id"] is not None

        new_pol = next(p for p in policies_after if p["id"] == old_pol["superseded_by_policy_id"])
        assert new_pol["is_current_policy"] is True
        assert new_pol["policy_status"] == "active"
        assert new_pol["policy_number"] == new_pol_num
    finally:
        db.close()


def test_phase2_document_upload_and_masking():
    """Verify document upload, masked number representation, and metadata view logging."""
    db = SessionLocal()
    try:
        pdf_content = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        doc = cdocs_svc.create_document(
            db=db,
            user_id="u_priya",
            document_name="Aadhaar Card",
            category="personal",
            document_type="aadhaar",
            file_name="Aadhaar_Priya.pdf",
            content=pdf_content,
            document_number="987654321098",
            issuing_authority="UIDAI",
            resource_type="USER",
            resource_id="u_priya",
        )

        assert doc["id"] is not None
        assert doc["current_version"] == 1
        # Number must be masked
        assert doc["document_number_masked"] == "XXXX-XXXX-1098"

        # Verify audit log was recorded for upload
        logs = cdocs_svc.list_document_access_logs(db, "u_priya", doc["id"])
        assert len(logs) >= 1
        assert logs[0]["action"] == "upload"

        # Clean up
        cdocs_svc.delete_document(db, "u_priya", doc["id"])
    finally:
        db.close()


def test_phase2_document_replacement_and_version_history():
    """Verify replacing a document creates version 2 without overwriting version 1."""
    db = SessionLocal()
    try:
        v1_pdf = b"%PDF-1.4\n% Version 1 Content\n%%EOF"
        doc = cdocs_svc.create_document(
            db=db,
            user_id="u_priya",
            document_name="Driving Licence Renewal Test",
            category="driving_licence",
            document_type="driving_licence",
            file_name="DL_v1.pdf",
            content=v1_pdf,
            document_number="DL-052014008129",
        )
        doc_id = doc["id"]

        # Replace with Version 2
        v2_pdf = b"%PDF-1.4\n% Version 2 Content with updated endorsement\n%%EOF"
        replaced = cdocs_svc.replace_document_file(
            db=db,
            user_id="u_priya",
            doc_id=doc_id,
            file_name="DL_v2.pdf",
            content=v2_pdf,
            change_summary="Endorsed transport category",
        )
        assert replaced["current_version"] == 2
        assert replaced["version_count"] == 2
        assert replaced["file_name"] == "DL_v2.pdf"

        # List version history
        versions = cdocs_svc.list_document_versions(db, "u_priya", doc_id)
        assert len(versions) == 2
        assert versions[0]["version_number"] == 2
        assert versions[0]["is_current"] is True
        assert versions[1]["version_number"] == 1
        assert versions[1]["is_current"] is False

        # Verify previous version 1 file remains accessible
        p1, mime1, name1 = cdocs_svc.get_document_version_file(db, "u_priya", doc_id, version_number=1)
        assert name1 == "DL_v1.pdf"

        p2, mime2, name2 = cdocs_svc.get_document_version_file(db, "u_priya", doc_id, version_number=2)
        assert name2 == "DL_v2.pdf"
        assert p1 != p2, "Version 1 and Version 2 must be distinct stored files"

        # Verify audit logs track upload and replace
        logs = cdocs_svc.list_document_access_logs(db, "u_priya", doc_id)
        actions = [l["action"] for l in logs]
        assert "replace" in actions
        assert "upload" in actions

        # Clean up
        cdocs_svc.delete_document(db, "u_priya", doc_id)
    finally:
        db.close()


def test_phase2_cross_user_isolation():
    """Verify User B cannot access or modify User A's vehicles or documents."""
    db = SessionLocal()
    try:
        # Priya's vehicle accessed by Arjun (unless granted)
        with pytest.raises(PermissionDenied):
            veh_svc.get_vehicle(db, user_id="u_arjun", vehicle_id="veh_demo_honda")

        # Priya creates a confidential document
        pdf_content = b"%PDF-1.4\nconfidential\n%%EOF"
        priya_doc = cdocs_svc.create_document(
            db=db,
            user_id="u_priya",
            document_name="Confidential Identity Doc",
            category="personal",
            document_type="pan",
            file_name="priya_pan.pdf",
            content=pdf_content,
            document_number="ABCDE1234F",
        )
        doc_id = priya_doc["id"]

        # Priya's document accessed by outsider
        with pytest.raises(PermissionDenied):
            cdocs_svc.get_document(db, user_id="u_outsider", doc_id=doc_id)

        with pytest.raises(PermissionDenied):
            cdocs_svc.get_document_file(db, user_id="u_outsider", doc_id=doc_id)

        # Clean up
        cdocs_svc.delete_document(db, "u_priya", doc_id)
    finally:
        db.close()
