"""Phase 4: Reports, Insurance Claims & External Submissions Test Suite.

Validates:
1. Migration safety and live Neon schema verification (all 4 Phase 4 tables present).
2. Existing Phase 1, Phase 2, and Phase 3 entities remain intact.
3. Case can support multiple report types (accident_summary, insurance_incident, etc.).
4. Report generation creates a persisted draft with structured, grounded case facts.
5. ReportLab PDF generation and storage via StorageAdapter with SHA-256 validation.
6. Explicit flagging of missing information without data fabrication.
7. Explicit labeling and distinction of AI-generated summaries (is_ai_generated: True).
8. Immutable version history: revising an approved report creates v2 without overwriting v1.
9. Human coordinator approval workflow (records user ID + timestamp, creates central document, blocks AI self-approval).
10. Insurance claims management: vehicle & policy linkage, status tracking, timeline events.
11. External submissions tracking: strict distinction between draft, submitted, and acknowledged.
12. Manual submission confirmation and formal authority acknowledgement recording.
13. Access control, coordinator authorization, and cross-case isolation.
14. FastAPI REST API endpoints integration for reports, claims, and submissions.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.api import app
from app.db import (
    Case,
    CentralDocument,
    ExternalSubmission,
    InsuranceClaim,
    Report,
    ReportVersion,
    SessionLocal,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    engine,
)
from app.services import claims as claim_svc
from app.services import reports as report_svc
from app.services import submissions as sub_svc
from app.services.common import NotFoundError, PermissionDenied, ServiceError


client = TestClient(app)


def test_phase4_schema_and_prior_phases_intact():
    """Verify Phase 4 tables exist on live database and prior phase records are intact."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify all 4 Phase 4 tables exist
    for table in ["reports", "report_versions", "insurance_claims", "external_submissions"]:
        assert table in tables, f"Expected table '{table}' in database"

    # Verify key columns on reports
    report_cols = {col["name"] for col in inspector.get_columns("reports")}
    assert "current_version_id" in report_cols
    assert "report_type" in report_cols
    assert "status" in report_cols
    assert "approved_by" in report_cols

    # Verify key columns on report_versions
    rv_cols = {col["name"] for col in inspector.get_columns("report_versions")}
    assert "content_json" in rv_cols
    assert "sha256" in rv_cols
    assert "storage_key" in rv_cols
    assert "generation_method" in rv_cols

    # Verify prior phase demo data intact
    db = SessionLocal()
    try:
        priya = db.get(User, "u_priya")
        assert priya is not None
        honda = db.get(Vehicle, "veh_demo_honda")
        assert honda is not None
        case_demo = db.get(Case, "case_demo")
        assert case_demo is not None
    finally:
        db.close()


def test_generate_report_draft_grounded_and_pdf_created():
    """Verify report draft generation extracts facts, builds PDF, calculates SHA-256 and flags missing data."""
    db = SessionLocal()
    try:
        report = report_svc.generate_report(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            report_type="accident_summary",
            custom_notes="Automated test report draft generation.",
        )

        assert report is not None
        assert report["id"].startswith("rpt_")
        assert report["case_id"] == "case_demo"
        assert report["report_type"] == "accident_summary"
        assert report["status"] == "draft"
        assert report["current_version_id"] is not None
        assert report["generation_source"] == "ai_generated"

        # Check report version in DB
        version = db.get(ReportVersion, report["current_version_id"])
        assert version is not None
        assert version.version_number == 1
        assert version.generation_method == "ai_assisted"
        assert len(version.sha256) == 64  # Valid SHA-256 hex digest
        assert version.storage_key.endswith(".pdf")

        # Check content grounding
        content = version.content_json
        assert content["case_number"].startswith("SH-2026-")
        assert content["ai_synthesis"]["is_ai_generated"] is True
        assert "incident" in content
        assert "disclaimer" in content
        assert "missing_information" in content
        assert isinstance(content["missing_information"], list)

        # Check PDF file exists on physical storage
        pdf_path, media_type, filename = report_svc.get_report_file(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            report_id=report["id"],
            version_id=version.id,
        )
        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            header = f.read(4)
            assert header == b"%PDF"
    finally:
        db.close()


def test_report_multiple_types_supported():
    """Verify system supports multiple report types for the same case."""
    db = SessionLocal()
    try:
        for rtype in ["insurance_incident", "police_incident_info", "evidence_summary"]:
            rpt = report_svc.generate_report(
                db=db,
                actor_id="u_priya",
                case_id="case_demo",
                report_type=rtype,
            )
            assert rpt["report_type"] == rtype
            assert rpt["status"] == "draft"
    finally:
        db.close()


def test_report_versioning_and_human_approval_workflow():
    """Verify human coordinator approval dual-registers document, and revision creates immutable v2."""
    db = SessionLocal()
    try:
        # 1. Generate initial draft
        report = report_svc.generate_report(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            report_type="accident_summary",
            title="Dossier For Versioning Test",
        )
        report_id = report["id"]
        v1_id = report["current_version_id"]
        assert report["status"] == "draft"

        # 2. Coordinator approves report
        approved = report_svc.approve_report(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            report_id=report_id,
            version_id=v1_id,
            approval_notes="Reviewed and approved for submission",
        )
        assert approved["status"] == "approved"
        assert approved["approved_by"] == "u_priya"
        assert approved["approved_at"] is not None

        # Verify dual registration into CentralDocument
        cdoc = db.query(CentralDocument).filter(
            CentralDocument.user_id == "u_priya",
            CentralDocument.document_name.contains("Dossier For Versioning Test"),
        ).first()
        assert cdoc is not None
        assert cdoc.document_type == "case_report"

        # 3. Revise approved report -> must create version 2 without overwriting v1
        v1_record = db.get(ReportVersion, v1_id)
        updated_content = dict(v1_record.content_json)
        updated_content["user_revision_notes"] = "Added supplementary witness statement"

        revised = report_svc.revise_report(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            report_id=report_id,
            updated_content=updated_content,
            revision_notes="Revised version 2 with witness note",
        )

        assert revised["status"] == "ready_for_review"
        assert revised["current_version_number"] == 2
        assert revised["current_version_id"] != v1_id

        # Verify version 1 is still present and intact in database
        v1 = db.get(ReportVersion, v1_id)
        assert v1 is not None
        assert v1.version_number == 1

        # Verify version 2 exists and has updated content
        v2 = db.get(ReportVersion, revised["current_version_id"])
        assert v2.version_number == 2
        assert v2.content_json["user_revision_notes"] == "Added supplementary witness statement"
    finally:
        db.close()


def test_ai_cannot_self_approve():
    """Verify that automated agents or AI cannot approve their own generated reports."""
    db = SessionLocal()
    try:
        report = report_svc.generate_report(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            report_type="accident_summary",
        )

        # AI actor_id attempting approval must raise PermissionDenied
        with pytest.raises(PermissionDenied) as exc:
            report_svc.approve_report(
                db=db,
                actor_id="ai",
                case_id="case_demo",
                report_id=report["id"],
            )
        assert "AI agents and automated systems are strictly forbidden" in str(exc.value)
    finally:
        db.close()


def test_insurance_claim_lifecycle():
    """Verify motor insurance claim creation, policy linkage, and status transitions."""
    db = SessionLocal()
    try:
        # Create claim
        claim = claim_svc.create_insurance_claim(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            data={
                "claim_type": "own_damage",
                "insurer_name": "Tata AIG General Insurance",
                "policy_number": "POL-99283401-2026",
                "estimated_amount": 52000.0,
                "description": "Front bumper damage and left fender scratch from side collision.",
                "cashless_garage": "Authorized Honda Service Center, Koramangala",
            },
        )

        assert claim["id"].startswith("claim_")
        assert claim["case_id"] == "case_demo"
        assert claim["vehicle_id"] == "veh_demo_honda"
        assert claim["claim_status"] == "draft"
        assert claim["estimated_amount"] == 52000.0
        assert claim["claim_reference_number"].startswith("CLM-")

        # Update claim details
        updated = claim_svc.update_claim(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            claim_id=claim["id"],
            data={
                "surveyor_name": "S. Raghavan",
                "surveyor_phone": "+91 98450 11223",
            },
        )
        assert updated["surveyor_name"] == "S. Raghavan"

        # Transition status
        transitioned = claim_svc.update_claim_status(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            claim_id=claim["id"],
            new_status="submitted",
            notes="Claim lodged via insurer web portal",
        )
        assert transitioned["claim_status"] == "submitted"
        assert transitioned["filed_at"] is not None
    finally:
        db.close()


def test_external_submission_lifecycle_and_verification_rules():
    """Verify external submission tracking: draft vs submitted vs acknowledged."""
    db = SessionLocal()
    try:
        # 1. Create submission record
        sub = sub_svc.create_external_submission(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            data={
                "external_org_name": "Cubbon Park Traffic Police Station",
                "external_org_type": "police",
                "submission_method": "manual_user_submission",
                "metadata": {"officer_in_charge": "Insp. Kumar", "station_code": "CP-04"},
            },
        )

        assert sub["id"].startswith("exsub_")
        assert sub["submission_status"] == "draft"
        assert sub["submitted_at"] is None
        assert sub["acknowledged_at"] is None

        # 2. User confirms physical handover / dispatch
        confirmed = sub_svc.confirm_manual_submission(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            submission_id=sub["id"],
            external_reference_number="GD-ENTRY-2026-8891",
            notes="Handed over physical FIR copy and evidence CD at station desk",
        )
        assert confirmed["submission_status"] == "submitted"
        assert confirmed["submitted_at"] is not None
        assert confirmed["external_reference_number"] == "GD-ENTRY-2026-8891"

        # 3. Formal acknowledgement requires valid reference number
        with pytest.raises(ServiceError):
            sub_svc.record_submission_acknowledgement(
                db=db,
                actor_id="u_priya",
                case_id="case_demo",
                submission_id=sub["id"],
                external_reference_number="",  # Empty reference must fail
            )

        ack = sub_svc.record_submission_acknowledgement(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            submission_id=sub["id"],
            external_reference_number="POLICE-ACK-2026-9921",
        )
        assert ack["submission_status"] == "acknowledged"
        assert ack["acknowledged_at"] is not None
        assert ack["external_reference_number"] == "POLICE-ACK-2026-9921"
    finally:
        db.close()


def test_external_submission_failure_recording():
    """Verify delivery failures or authority rejections are accurately recorded."""
    db = SessionLocal()
    try:
        sub = sub_svc.create_external_submission(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            data={
                "external_org_name": "City Hospital Legal Desk",
                "external_org_type": "hospital",
                "submission_method": "email",
            },
        )

        failed = sub_svc.record_submission_failure(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            submission_id=sub["id"],
            failure_reason="Hospital mail server returned 550 Mailbox full",
        )
        assert failed["submission_status"] == "failed"
        assert failed["failure_reason"] == "Hospital mail server returned 550 Mailbox full"
    finally:
        db.close()


def test_unauthorized_user_blocked_from_case_reports_and_claims():
    """Verify security isolation: non-members cannot generate reports or view claims."""
    db = SessionLocal()
    try:
        # u_outsider is not a member of case_demo
        with pytest.raises(PermissionDenied):
            report_svc.generate_report(
                db=db,
                actor_id="u_outsider",
                case_id="case_demo",
                report_type="accident_summary",
            )

        with pytest.raises(PermissionDenied):
            claim_svc.create_insurance_claim(
                db=db,
                actor_id="u_outsider",
                case_id="case_demo",
                data={
                    "claim_type": "own_damage",
                    "insurer_name": "Unauthorized Insurer",
                    "policy_number": "UNAUTH-123",
                },
            )
    finally:
        db.close()


def test_api_reports_claims_and_submissions_endpoints():
    """Verify FastAPI endpoints for Reports, Claims, and Submissions."""
    headers = {"x-user-id": "u_priya"}

    # 1. List case reports
    res = client.get("/api/cases/case_demo/reports", headers=headers)
    assert res.status_code == 200
    reports = res.json()
    assert isinstance(reports, list)
    assert len(reports) > 0

    report_id = reports[0]["id"]

    # 2. Get report detail
    res_det = client.get(f"/api/cases/case_demo/reports/{report_id}", headers=headers)
    assert res_det.status_code == 200
    det = res_det.json()
    assert det["id"] == report_id
    assert "versions" in det
    assert "active_content" in det

    # 3. List insurance claims
    res_clm = client.get("/api/cases/case_demo/claims", headers=headers)
    assert res_clm.status_code == 200
    claims = res_clm.json()
    assert isinstance(claims, list)

    # 4. List external submissions
    res_sub = client.get("/api/cases/case_demo/submissions", headers=headers)
    assert res_sub.status_code == 200
    submissions = res_sub.json()
    assert isinstance(submissions, list)

    # 5. Case workspace includes reports, claims, submissions
    res_ws = client.get("/api/cases/case_demo/workspace", headers=headers)
    assert res_ws.status_code == 200
    ws = res_ws.json()
    assert "reports" in ws
    assert "claims" in ws
    assert "submissions" in ws
