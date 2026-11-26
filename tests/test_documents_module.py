"""Unit and integration tests for Centralized Documents Management Module."""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.db import Case, CaseMember, CentralDocument, SessionLocal, User, Vehicle, init_db
from app.services import central_documents as central_docs_svc
from app.services.common import PermissionDenied, ServiceError


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    db = SessionLocal()
    # Clean previous records
    db.query(CentralDocument).delete()
    db.commit()
    db.close()


def test_expiry_status_calculation():
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # No expiry date -> valid
    st, days = central_docs_svc.calculate_document_status(None)
    assert st == "valid"
    assert days is None

    # Far future (e.g. 1 year) -> valid
    future_date = now + timedelta(days=365)
    st, days = central_docs_svc.calculate_document_status(future_date)
    assert st == "valid"
    assert days is not None and days >= 364

    # Expiring soon (20 days) -> expiring_soon
    soon_date = now + timedelta(days=20)
    st, days = central_docs_svc.calculate_document_status(soon_date)
    assert st == "expiring_soon"
    assert days is not None and 19 <= days <= 21

    # Expired in past (-5 days) -> expired
    past_date = now - timedelta(days=5)
    st, days = central_docs_svc.calculate_document_status(past_date)
    assert st == "expired"
    assert days is not None and days < 0


def test_list_and_summary_documents():
    client = TestClient(app)

    # Generate synthetic PDF bytes
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    # Upload 1: Driving Licence (Valid)
    res1 = client.post(
        "/api/documents",
        headers={"X-User-Id": "u_priya"},
        data={
            "document_name": "Karnataka Driving Licence",
            "category": "driving_licence",
            "document_type": "driving_licence",
            "document_number": "KA04-2020-001928",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat(),
            "resource_type": "USER",
        },
        files={"file": ("licence.pdf", valid_pdf, "application/pdf")},
    )
    assert res1.status_code == 200, res1.text
    d1 = res1.json()
    assert d1["category"] == "driving_licence"
    assert d1["status"] == "valid"

    # Upload 2: Insurance Policy (Expiring Soon)
    res2 = client.post(
        "/api/documents",
        headers={"X-User-Id": "u_priya"},
        data={
            "document_name": "Tata AIG Insurance",
            "category": "insurance",
            "document_type": "insurance",
            "document_number": "POL-9921",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
            "resource_type": "USER",
        },
        files={"file": ("insurance.pdf", valid_pdf, "application/pdf")},
    )
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["status"] == "expiring_soon"

    # Check Summary statistics
    sum_res = client.get("/api/documents/summary", headers={"X-User-Id": "u_priya"})
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["total"] == 2
    assert summary["valid"] == 1
    assert summary["expiring_soon"] == 1
    assert summary["expired"] == 0


def test_vehicle_document_single_source_of_truth():
    client = TestClient(app)
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    # Upload document to vehicle via central Documents endpoint
    res = client.post(
        "/api/documents",
        headers={"X-User-Id": "u_priya"},
        data={
            "document_name": "Vehicle Purchase Invoice",
            "category": "vehicle",
            "document_type": "purchase_invoice",
            "resource_type": "VEHICLE",
            "resource_id": "veh_demo_honda",
        },
        files={"file": ("invoice.pdf", valid_pdf, "application/pdf")},
    )
    assert res.status_code == 200
    created_id = res.json()["id"]

    # Verify document is visible in central Documents list
    list_res = client.get("/api/documents?category=vehicle", headers={"X-User-Id": "u_priya"})
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["id"] == created_id for d in docs)

    # Verify document is ALSO visible in My Vehicles detail page
    veh_res = client.get("/api/vehicles/veh_demo_honda", headers={"X-User-Id": "u_priya"})
    assert veh_res.status_code == 200
    veh = veh_res.json()
    assert any(d["id"] == created_id for d in veh["documents"])


def test_authorization_protection():
    client = TestClient(app)
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    # Priya creates private document
    res = client.post(
        "/api/documents",
        headers={"X-User-Id": "u_priya"},
        data={
            "document_name": "Priya Confidential Passport",
            "category": "personal",
            "document_type": "passport",
            "resource_type": "USER",
        },
        files={"file": ("passport.pdf", valid_pdf, "application/pdf")},
    )
    assert res.status_code == 200
    doc_id = res.json()["id"]

    # Outsider attempts to read file
    get_res = client.get(f"/api/documents/{doc_id}", headers={"X-User-Id": "u_outsider"})
    assert get_res.status_code == 403

    # Outsider attempts to download file
    dl_res = client.get(f"/api/documents/{doc_id}/file", headers={"X-User-Id": "u_outsider"})
    assert dl_res.status_code == 403

    # Outsider attempts to delete file
    del_res = client.delete(f"/api/documents/{doc_id}", headers={"X-User-Id": "u_outsider"})
    assert del_res.status_code == 403


def test_invalid_file_rejection():
    client = TestClient(app)

    # Fake executable disguised as PDF
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00fake executable content"
    res = client.post(
        "/api/documents",
        headers={"X-User-Id": "u_priya"},
        data={"document_name": "Suspicious File", "category": "personal"},
        files={"file": ("malware.pdf", fake_exe, "application/pdf")},
    )
    assert res.status_code == 400
    assert "Corrupted or invalid PDF" in res.text


def test_metadata_update_and_replace():
    client = TestClient(app)
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    res = client.post(
        "/api/documents",
        headers={"X-User-Id": "u_priya"},
        data={"document_name": "Draft Document", "category": "personal", "document_type": "other"},
        files={"file": ("draft.pdf", valid_pdf, "application/pdf")},
    )
    doc_id = res.json()["id"]

    # Update metadata
    patch_res = client.patch(
        f"/api/documents/{doc_id}",
        headers={"X-User-Id": "u_priya"},
        json={"document_name": "Finalized Personal Affidavit", "notes": "Approved by notary"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["document_name"] == "Finalized Personal Affidavit"
    assert updated["notes"] == "Approved by notary"

    # Replace file
    new_pdf = b"%PDF-1.5\nnew updated content\n%%EOF"
    repl_res = client.post(
        f"/api/documents/{doc_id}/replace",
        headers={"X-User-Id": "u_priya"},
        files={"file": ("updated_affidavit.pdf", new_pdf, "application/pdf")},
    )
    assert repl_res.status_code == 200
    replaced = repl_res.json()
    assert replaced["file_name"] == "updated_affidavit.pdf"

    # Delete document
    del_res = client.delete(f"/api/documents/{doc_id}", headers={"X-User-Id": "u_priya"})
    assert del_res.status_code == 200

    # Ensure deleted document is no longer listed
    get_res = client.get(f"/api/documents/{doc_id}", headers={"X-User-Id": "u_priya"})
    assert get_res.status_code == 400
