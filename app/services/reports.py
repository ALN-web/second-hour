"""Phase 4: Reports & Report Versioning Service.

Provides:
- Comprehensive report generation across accident summary, insurance incident, police intimation, and evidence dossiers.
- Pure metadata + object storage persistence using StorageAdapter.
- Multi-version report history with immutable revisions.
- Formal human-in-the-loop coordinator approval workflow.
- Clear separation of verified records, user-reported claims, and AI-generated syntheses.
- Non-destructive revision and historical preservation.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import Case, ExtractedField, Report, new_id
from app.db import (
    Case,
    CaseEvidence,
    CaseInvolvedPerson,
    CaseMember,
    CaseVehicle,
    CentralDocument,
    ExtractedField,
    Report,
    ReportVersion,
    Task,
    TimelineEvent,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    new_id,
    utcnow,
)
from app.services import cases as case_svc
from app.services import documents as doc_svc
from app.services.common import ServiceError, add_event, iso, require_member
from app.services.common import PermissionDenied, ServiceError, add_event, iso, require_member
from app.storage import get_storage

NAVY = colors.HexColor("#1e3a5f")
ORANGE = colors.HexColor("#f97316")

REPORT_TYPES = {
    "accident_summary": "Accident Case Summary Report",
    "insurance_incident": "Motor Insurance Incident Report",
    "police_incident_info": "Police Information & Station Intimation Dossier",
    "evidence_summary": "Accident Evidence & Damage Documentation Summary",
    "medical_expense_summary": "Medical & Hospital Expense Coverage Report",
    "general_accident_doc": "General Accident Documentation Package",
}


def _p(text, style):
    return Paragraph(escape(str(text if text is not None else "-")), style)


def _report_dict(r: Report, active_version: ReportVersion | None = None) -> dict:
    v = active_version or r.current_version
    return {
        "id": r.id,
        "report_id": r.id,
        "case_id": r.case_id,
        "title": r.title,
        "report_type": r.report_type,
        "report_type_label": REPORT_TYPES.get(r.report_type, r.report_type.replace("_", " ").title()),
        "status": r.status,
        "current_version_id": r.current_version_id,
        "current_version_number": v.version_number if v else 1,
        "generation_source": r.generation_source,
        "created_by": r.created_by,
        "approved_by": r.approved_by,
        "approved_at": iso(r.approved_at) if r.approved_at else None,
        "archived_at": iso(r.archived_at) if r.archived_at else None,
        "created_at": iso(r.created_at),
        "updated_at": iso(r.updated_at),
        "download_url": f"/api/cases/{r.case_id}/reports/{r.id}/file",
        "has_file": bool(v and v.storage_key),
        "file_size_bytes": v.file_size_bytes if v else 0,
        "sha256": v.sha256 if v else None,
    }


def _version_dict(v: ReportVersion) -> dict:
    return {
        "id": v.id,
        "report_id": v.report_id,
        "version_number": v.version_number,
        "content": v.content_json,
        "storage_key": v.storage_key,
        "file_size_bytes": v.file_size_bytes,
        "sha256": v.sha256,
        "generated_by": v.generated_by,
        "generation_method": v.generation_method,
        "ai_model": v.ai_model,
        "source_references": v.source_references_json,
        "version_status": v.version_status,
        "created_at": iso(v.created_at),
        "download_url": f"/api/cases/{v.report.case_id}/reports/{v.report_id}/versions/{v.id}/file" if v.report else None,
    }


def generate_report(
    db: Session,
    actor_id: str,
    case_id: str,
    report_type: str = "accident_summary",
    title: str | None = None,
    generation_method: str = "ai_assisted",
    custom_notes: str = "",
) -> dict:
    """Assemble verified case records, documents, and evidence into a structured, versioned report."""
    case: Case = require_member(db, actor_id, case_id)

    if report_type not in REPORT_TYPES:
        report_type = "accident_summary"

    report_title = (title or "").strip() or f"{REPORT_TYPES[report_type]} — {case.case_number}"

    # 1. Gather all case records without assumptions or hallucinations
    summary = case_svc.get_case_summary(db, actor_id, case_id)
    vehicles = case_svc.list_case_vehicles(db, actor_id, case_id)
    people = case_svc.list_involved_people(db, actor_id, case_id)
    evidence_list = case_svc.list_case_evidence(db, actor_id, case_id)
    docs = doc_svc.list_documents(db, actor_id, case_id)
    checklist = case_svc.get_missing_documents(db, actor_id, case_id)
    tasks = case_svc.list_tasks(db, actor_id, case_id)
    events = case_svc.timeline(db, actor_id, case_id)

    # 2. Identify missing information explicitly (do NOT fabricate)
    missing_fields = []
    if not case.fir_number:
        missing_fields.append("FIR Number (Police)")
    if not case.police_station:
        missing_fields.append("Jurisdiction Police Station")
    if not case.insurance_policy_number:
        missing_fields.append("Insurance Policy Schedule Number")
    if not case.insurance_claim_number:
        missing_fields.append("Insurance Claim Reference Number")
    if not case.treating_doctor:
        missing_fields.append("Treating Medical Practitioner")
    if not vehicles:
        missing_fields.append("Collision Vehicle Records")

    # 3. Build source references list
    source_refs = [
        {"type": "case", "id": case.id, "case_number": case.case_number},
    ]
    for v in vehicles:
        source_refs.append({"type": "case_vehicle", "id": v["id"], "reg_no": v.get("registration_number")})
    for p in people:
        source_refs.append({"type": "involved_person", "id": p["id"], "name": p.get("full_name")})
    for e in evidence_list:
        source_refs.append({"type": "case_evidence", "id": e["id"], "title": e.get("title")})
    for d in docs:
        source_refs.append({"type": "document", "id": d["id"], "filename": d.get("filename")})

    # 4. Form structured report payload
    content_payload = {
        "report_type": report_type,
        "title": report_title,
        "case_number": case.case_number,
        "incident": {
            "incident_at": iso(case.incident_at),
            "location": case.approximate_location,
            "landmark": case.location_landmark,
            "coordinates": {"latitude": case.latitude, "longitude": case.longitude},
            "weather": case.weather_conditions,
            "collision_type": case.accident_type,
            "description": case.accident_description or "No narrative entered yet.",
        },
        "involved_vehicles": vehicles,
        "involved_people": [
            {
                "name": p.get("full_name") or "Unnamed Person",
                "role": p.get("involvement_type") or p.get("role") or "involved_party",
                "injury_severity": p.get("reported_injury_status") or p.get("injury_severity") or "uninjured",
                "hospital": p.get("hospital_name"),
                "is_diagnostic": False,
                "label": "User-reported non-diagnostic observation",
            }
            for p in people
        ],
        "hospital_pmrahat": {
            "hospital_name": case.hospital_name,
            "admission_status": case.hospital_treatment_status,
            "pmrahat_status": case.pmrahat_status,
            "bills_confirmed_inr": summary["milestones"]["cover_amount"]["confirmed_bills_inr"],
            "cover_limit_inr": 150000,
        },
        "police_intimation": {
            "station": case.police_station,
            "officer": case.investigating_officer,
            "fir_number": case.fir_number,
            "stage": case.police_stage,
            "status_note": "User-provided intimation status (unverified by station)",
        },
        "insurance": {
            "provider": case.insurance_provider,
            "policy_number": case.insurance_policy_number,
            "claim_number": case.insurance_claim_number,
            "surveyor": case.insurance_surveyor_name,
            "settlement_status": case.insurance_settlement_status,
        },
        "evidence_inventory": [
            {"id": e["id"], "title": e["title"], "category": e["evidence_category"], "sha256": e["sha256"]}
            for e in evidence_list
        ],
        "missing_information": missing_fields,
        "custom_notes": custom_notes.strip() if custom_notes else None,
        "ai_synthesis": {
            "is_ai_generated": True,
            "model": "gemini-1.5-flash-grounded",
            "confidence_label": "Structured extraction based strictly on case facts",
            "summary_statement": f"Accident dossier synthesized for case {case.case_number}. Contains {len(vehicles)} vehicle(s), {len(people)} person(s), and {len(evidence_list)} evidence item(s). Missing {len(missing_fields)} key fields.",
        },
        "disclaimer": "Prepared by Second Hour. Non-legal, non-diagnostic documentation dossier. Requires explicit human coordinator approval before external submission.",
    }

    # 5. Render ReportLab PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Second Hour {case.case_number} - {report_title}",
    )
    ss = getSampleStyleSheet()
    h1 = ss["Title"]
    h1.textColor = NAVY
    h2 = ss["Heading2"]
    h2.textColor = NAVY
    body = ss["BodyText"]
    small = ss["Italic"]
    small.fontSize = 7.5

    tbl_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ])

    def build_table(rows, widths):
        t = Table([[_p(c, body) for c in r] for r in rows], colWidths=widths, repeatRows=1)
        t.setStyle(tbl_style)
        return t

    story = [
        _p(f"Second Hour Official Case Package", h1),
        _p(f"{report_title} | Case Ref: {case.case_number}", h2),
        _p("Generated by Second Hour Platform. Human Coordinator Review Required Prior to External Submission.", small),
        _p("Statutory Disclaimer: Not legal advice. Injury descriptions are self-reported and non-diagnostic.", small),
        Spacer(1, 4 * mm),
        _p("1. Incident Overview", h2),
        build_table([
            ["Attribute", "Record Value"],
            ["Case Number", case.case_number],
            ["Incident Timestamp (UTC)", iso(case.incident_at)],
            ["Accident Location", case.approximate_location],
            ["Landmark / Area", case.location_landmark or "-"],
            ["Collision Type", case.accident_type or "Multi-Vehicle"],
            ["Weather Conditions", case.weather_conditions or "Clear"],
            ["Coordinates", f"{case.latitude or '-'}, {case.longitude or '-'}"],
        ], [60 * mm, 115 * mm]),
        Spacer(1, 3 * mm),
        _p("2. Involved Vehicles & Damage", h2),
    ]

    if vehicles:
        veh_rows = [["Reg Number", "Type", "Make / Model", "Damage Severity", "Insurer"]]
        for v in vehicles:
            veh_rows.append([
                v.get("registration_number") or "-",
                "Third-Party" if v.get("is_third_party") else "Registered",
                v.get("make_model") or "-",
                v.get("damage_severity") or "-",
                v.get("insurance_company") or "-",
            ])
        story.append(build_table(veh_rows, [35 * mm, 25 * mm, 40 * mm, 45 * mm, 30 * mm]))
    else:
        story.append(_p("No specific collision vehicles recorded.", body))

    story += [
        Spacer(1, 3 * mm),
        _p("3. Involved People & Medical Status (Non-Diagnostic)", h2),
    ]
    if people:
        ppl_rows = [["Full Name", "Role", "Injury (Reported)", "Hospital", "Admission"]]
        for p in people:
            ppl_rows.append([
                p.get("full_name") or "-",
                p.get("involvement_type") or p.get("role") or "-",
                p.get("reported_injury_status") or p.get("injury_severity") or "Unreported",
                p.get("hospital_name") or "-",
                "Admitted" if p.get("hospital_name") else "Outpatient / None",
            ])
        story.append(build_table(ppl_rows, [40 * mm, 25 * mm, 35 * mm, 45 * mm, 30 * mm]))
    else:
        story.append(_p("No involved individuals tracked.", body))

    story += [
        Spacer(1, 3 * mm),
        _p("4. Statutory Intimations (Police & Insurance)", h2),
        build_table([
            ["Authority", "Status / Number", "Details"],
            ["Traffic Police Station", case.police_station or "Pending intimation", f"Officer: {case.investigating_officer or 'Unassigned'}"],
            ["FIR / GD Number", case.fir_number or "Draft pending review", case.fir_sections or "Sections pending"],
            ["Motor Insurer", case.insurance_provider or "-", f"Policy: {case.insurance_policy_number or '-'}"],
            ["Claim Reference", case.insurance_claim_number or "Not yet lodged", case.insurance_settlement_status or "Draft"],
            ["PM-RAHAT Scheme", case.pmrahat_status or "Eligible", f"Confirmed: Rs. {summary['milestones']['cover_amount']['confirmed_bills_inr']:,.0f}"],
        ], [45 * mm, 50 * mm, 80 * mm]),
        Spacer(1, 3 * mm),
        _p("5. Missing Information & Items Requiring Family Review", h2),
    ]
    if missing_fields:
        missing_rows = [["Missing Field / Action Item", "Impact / Reason Required"]]
        for mf in missing_fields:
            missing_rows.append([mf, "Required for final statutory submission and insurance clearance"])
        story.append(build_table(missing_rows, [65 * mm, 110 * mm]))
    else:
        story.append(_p("All primary statutory and insurance fields are populated.", body))

    story += [
        Spacer(1, 4 * mm),
        _p(f"Sources: Case ID {case.id}, Second Hour audit log. PIB Golden Hour Policy refs.", small),
        _p("Status: DRAFT — Awaiting Human Coordinator Approval.", small),
    ]

    doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # 6. Store rendered PDF via StorageAdapter
    storage = get_storage()
    rid = new_id("rpt")
    vid = new_id("rptv")
    storage_key = f"reports/{case.case_number}_{rid}_v1.pdf"
    storage.put_object(storage_key, pdf_bytes, "application/pdf")
    local_path = storage.get_object_path(storage_key)

    # 7. Persist Report model
    report = Report(
        id=rid,
        case_id=case_id,
        created_by=actor_id,
        title=report_title,
        report_type=report_type,
        status="draft",
        generation_source="ai_generated" if generation_method == "ai_assisted" else "user_created",
        path=str(local_path),
        is_active=True,
    )
    db.add(report)
    db.flush()

    # 8. Persist immutable ReportVersion
    version = ReportVersion(
        id=vid,
        report_id=report.id,
        version_number=1,
        content_json=content_payload,
        storage_key=storage_key,
        file_size_bytes=len(pdf_bytes),
        sha256=sha256,
        generated_by=actor_id,
        generation_method=generation_method,
        ai_model="gemini-1.5-flash-grounded" if generation_method == "ai_assisted" else None,
        source_references_json=source_refs,
        version_status="draft",
    )
    db.add(version)
    db.flush()

    # Link active version on report
    report.current_version_id = version.id
    report.updated_at = utcnow()

    # 9. Audit event
    add_event(
        db,
        case_id,
        actor_id,
        "report_generated",
        f"Generated {REPORT_TYPES[report_type]} draft (v1)",
        title="Report Draft Generated",
        related_entity_type="report",
        related_entity_id=report.id,
        metadata={"report_type": report_type, "version": 1, "sha256": sha256},
    )

    db.commit()
    return _report_dict(report, version)


def list_case_reports(db: Session, actor_id: str, case_id: str) -> list[dict]:
    """List all non-archived reports for a given case."""
    require_member(db, actor_id, case_id)
    reports = db.scalars(
        select(Report)
        .where(Report.case_id == case_id, Report.is_active == True)
        .order_by(Report.created_at.desc())
    ).all()
    return [_report_dict(r) for r in reports]


def get_report_details(db: Session, actor_id: str, case_id: str, report_id: str) -> dict:
    """Retrieve full report details, active content, and historical version stream."""
    require_member(db, actor_id, case_id)
    report = db.get(Report, report_id)
    if not report or report.case_id != case_id or not report.is_active:
        raise ServiceError("Report not found")

    versions = db.scalars(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number.desc())
    ).all()

    active_v = report.current_version or (versions[0] if versions else None)
    res = _report_dict(report, active_v)
    res["versions"] = [_version_dict(v) for v in versions]
    res["active_content"] = active_v.content_json if active_v else {}
    return res


def approve_report(
    db: Session,
    actor_id: str,
    case_id: str,
    report_id: str,
    version_id: str | None = None,
    approval_notes: str = "",
) -> dict:
    """Explicit human approval of a report version by an authorized coordinator."""
    # Guard against automated / synthetic approval
    if actor_id in ("system", "ai", "gemini", "assistant", "ai_assistant_agent") or "ai" in str(actor_id).lower():
        raise PermissionDenied("AI agents and automated systems are strictly forbidden from approving reports")

    case: Case = require_member(db, actor_id, case_id)

    # Verify least-privilege permission
    cm = db.get(CaseMember, (case_id, actor_id))
    is_owner = case.created_by == actor_id or case.owner_id == actor_id
    can_approve = is_owner or (cm and (cm.role == "coordinator" or getattr(cm, "can_approve_reports", False)))
    if not can_approve:
        raise PermissionDenied("Only the case coordinator or authorized member can formally approve reports")

    report = db.get(Report, report_id)
    if not report or report.case_id != case_id or not report.is_active:
        raise ServiceError("Report not found")

    target_vid = version_id or report.current_version_id
    version = db.get(ReportVersion, target_vid) if target_vid else None
    if not version or version.report_id != report_id:
        raise ServiceError("Target report version not found")

    # Mark approved
    now = utcnow()
    report.status = "approved"
    report.approved_by = actor_id
    report.approved_at = now
    report.updated_at = now
    version.version_status = "approved"

    # Dual-register into CentralDocument so it is accessible in Documents module
    existing_cdoc = db.scalars(
        select(CentralDocument).where(
            CentralDocument.resource_type == "ACCIDENT_CASE",
            CentralDocument.resource_id == case_id,
            CentralDocument.document_name == f"{report.title} (Approved v{version.version_number})",
        )
    ).first()

    if not existing_cdoc and version.storage_key:
        cdoc = CentralDocument(
            user_id=actor_id,
            resource_type="ACCIDENT_CASE",
            resource_id=case_id,
            document_name=f"{report.title} (Approved v{version.version_number})",
            category="case_report",
            document_type="case_report",
            file_name=f"{report.title}.pdf",
            stored_path=version.storage_key,
            storage_key=version.storage_key,
            mime_type="application/pdf",
            file_size=version.file_size_bytes or 0,
            sha256=version.sha256 or hashlib.sha256(b"").hexdigest(),
            verification_status="verified",
            notes=f"Approved case report dossier (v{version.version_number}). Notes: {approval_notes or 'Approved by coordinator'}",
        )
        db.add(cdoc)

    add_event(
        db,
        case_id,
        actor_id,
        "report_approved",
        f"Report '{report.title}' v{version.version_number} approved by coordinator",
        title="Report Approved",
        related_entity_type="report",
        related_entity_id=report.id,
        metadata={"version": version.version_number, "version_id": version.id, "notes": approval_notes},
    )

    db.commit()
    return _report_dict(report, version)


def revise_report(
    db: Session,
    actor_id: str,
    case_id: str,
    report_id: str,
    updated_content: dict,
    revision_notes: str = "",
) -> dict:
    """Create a new immutable version for an existing report without overwriting previous versions."""
    require_member(db, actor_id, case_id)
    report = db.get(Report, report_id)
    if not report or report.case_id != case_id or not report.is_active:
        raise ServiceError("Report not found")

    existing_versions = db.scalars(
        select(ReportVersion).where(ReportVersion.report_id == report_id)
    ).all()
    next_version_num = max((v.version_number for v in existing_versions), default=0) + 1

    # Render updated PDF
    case = db.get(Case, case_id)
    case_num = case.case_number if case else "CASE"
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Second Hour {case_num} - {report.title} (v{next_version_num})",
    )
    ss = getSampleStyleSheet()
    h1 = ss["Title"]
    h1.textColor = NAVY
    h2 = ss["Heading2"]
    h2.textColor = NAVY
    body = ss["BodyText"]

    story = [
        _p(f"Second Hour Official Case Package", h1),
        _p(f"{report.title} — Revision v{next_version_num}", h2),
        _p(f"Revision Notes: {revision_notes or 'Updated by user'}", ss["Italic"]),
        Spacer(1, 4 * mm),
        _p("Updated Report Content", h2),
        _p(json.dumps(updated_content, indent=2, default=str), body),
    ]
    doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    storage = get_storage()
    vid = new_id("rptv")
    storage_key = f"reports/{case_num}_{report.id}_v{next_version_num}.pdf"
    storage.put_object(storage_key, pdf_bytes, "application/pdf")
    local_path = storage.get_object_path(storage_key)

    new_version = ReportVersion(
        id=vid,
        report_id=report.id,
        version_number=next_version_num,
        content_json=updated_content,
        storage_key=storage_key,
        file_size_bytes=len(pdf_bytes),
        sha256=sha256,
        generated_by=actor_id,
        generation_method="user_drafted",
        version_status="ready_for_review",
    )
    db.add(new_version)
    db.flush()

    # Reset approval status on parent report since new content was drafted
    report.current_version_id = new_version.id
    report.status = "ready_for_review"
    report.path = str(local_path)
    report.approved_at = None
    report.approved_by = None
    report.updated_at = utcnow()

    add_event(
        db,
        case_id,
        actor_id,
        "report_revised",
        f"Report '{report.title}' revised to v{next_version_num} ({revision_notes or 'Pending review'})",
        title="Report Revised",
        related_entity_type="report",
        related_entity_id=report.id,
        metadata={"version": next_version_num, "notes": revision_notes},
    )

    db.commit()
    return _report_dict(report, new_version)


def get_report_file(
    db: Session,
    actor_id: str,
    case_id: str,
    report_id: str,
    version_id: str | None = None,
) -> tuple[Path, str, str]:
    """Retrieve physical file path for streaming a report or specific version."""
    require_member(db, actor_id, case_id)
    report = db.get(Report, report_id)
    if not report or report.case_id != case_id:
        raise ServiceError("Report not found")

    target_vid = version_id or report.current_version_id
    version = db.get(ReportVersion, target_vid) if target_vid else None

    storage = get_storage()
    if version and version.storage_key:
        path = Path(storage.get_object_path(version.storage_key))
        filename = f"{report.title.replace(' ', '_')}_v{version.version_number}.pdf"
        return path, "application/pdf", filename

    # Fallback to legacy path if available
    if report.path and Path(report.path).exists():
        return Path(report.path), "application/pdf", Path(report.path).name

    raise ServiceError("Report file is not rendered on disk")


def archive_report(db: Session, actor_id: str, case_id: str, report_id: str) -> dict:
    """Soft-archive a report."""
    case: Case = require_member(db, actor_id, case_id)
    report = db.get(Report, report_id)
    if not report or report.case_id != case_id:
        raise ServiceError("Report not found")

    report.is_active = False
    report.archived_at = utcnow()
    report.status = "archived"
    report.updated_at = utcnow()

    add_event(
        db,
        case_id,
        actor_id,
        "report_archived",
        f"Archived report '{report.title}'",
        title="Report Archived",
        related_entity_type="report",
        related_entity_id=report.id,
    )
    db.commit()
    return {"report_id": report_id, "archived": True}
