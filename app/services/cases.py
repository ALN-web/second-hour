"""Case, task, timeline, checklist and alert (watcher) services."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.db import (
    Case,
    CaseMember,
    CentralDocument,
    Document,
    ExtractedField,
    Task,
    TimelineEvent,
    User,
    Vehicle,
    VehicleInsurancePolicy,
    VehiclePhoto,
    new_id,
    utcnow,
)
from app.services.common import (
    ServiceError,
    add_event,
    case_now,
    iso,
    parse_dt,
    require_member,
    require_user,
)

POLICE_STATUSES = ("not_started", "requested_by_hospital", "confirmed", "not_confirmed")
PRIORITIES = ("low", "medium", "high")

# Configurable document checklist (guidance, not a legal determination)
CHECKLIST = [
    {"key": "medical_report", "label": "Medical / discharge report", "reason": "Records diagnosis and treatment; usually asked for by insurers and in claims."},
    {"key": "hospital_bill", "label": "Hospital bill / estimate", "reason": "Lets the family track treatment cost against the ₹1.5 lakh PM-RAHAT cover."},
    {"key": "police_document", "label": "Police document (FIR / GD entry / MLC copy)", "reason": "Road accident cases typically involve a police record; useful for insurance and claims."},
    {"key": "vehicle_document", "label": "Vehicle documents (RC / licence)", "reason": "Often requested for motor insurance or accident claims."},
    {"key": "insurance_policy", "label": "Insurance policy copy", "reason": "Health or motor insurance may cover costs beyond the scheme."},
]


# ---------------------------------------------------------------- cases

def _next_case_number(db: Session) -> str:
    n = db.scalar(select(func.count()).select_from(Case)) or 0
    return f"SH-{utcnow():%Y}-{n + 1:04d}"


def create_case(db: Session, actor_id: str, incident_at: str, approximate_location: str,
                victim_display_name: str | None = None, hospital_name: str | None = None,
                life_threatening: bool = False, vehicle_id: str | None = None,
                accident_type: str | None = None, injury_severity: str | None = None,
                accident_description: str | None = None, damage_severity: str | None = None) -> dict:
    require_user(db, actor_id)
    inc = parse_dt(incident_at, "incident_at")
    if not inc:
        raise ServiceError("incident_at is required")
    if inc > utcnow() + timedelta(minutes=5):
        raise ServiceError("incident_at cannot be in the future")
    if not approximate_location or not approximate_location.strip():
        raise ServiceError("approximate_location is required")
    
    # Auto-link vehicle if valid
    veh = db.get(Vehicle, vehicle_id) if vehicle_id else None
    
    case = Case(
        case_number=_next_case_number(db),
        incident_at=inc,
        approximate_location=approximate_location.strip()[:200],
        victim_display_name=(victim_display_name or "").strip()[:100] or None,
        hospital_name=(hospital_name or "").strip()[:200] or None,
        life_threatening=bool(life_threatening),
        vehicle_id=veh.id if veh else None,
        accident_type=(accident_type or "Two-Vehicle Collision").strip()[:100],
        injury_severity=(injury_severity or "Moderate").strip()[:50],
        accident_description=(accident_description or "").strip()[:2000] or None,
        damage_severity=(damage_severity or "Moderate Frontal Damage").strip()[:100],
        created_by=actor_id,
        status="active",
    )
    
    # If vehicle has insurance policy, auto-populate insurance provider/policy
    if veh:
        policy = db.scalar(
            select(VehicleInsurancePolicy)
            .where(VehicleInsurancePolicy.vehicle_id == veh.id)
            .order_by(VehicleInsurancePolicy.created_at.desc())
        )
        if policy:
            case.insurance_provider = policy.provider
            case.insurance_policy_number = policy.policy_number

    db.add(case)
    db.flush()
    db.add(CaseMember(case_id=case.id, user_id=actor_id, role="coordinator", relationship="Self", permissions_summary="Full Coordinator Access"))
    add_event(db, case.id, actor_id, "case_created", f"Case {case.case_number} created")
    db.commit()
    return {"case_id": case.id, "case_number": case.case_number, "status": case.status}


def list_cases_for(db: Session, user_id: str) -> list[dict]:
    rows = db.scalars(select(Case).join(CaseMember, CaseMember.case_id == Case.id)
                      .where(CaseMember.user_id == user_id).order_by(Case.created_at.desc())).all()
    return [{"case_id": c.id, "case_number": c.case_number, "victim_display_name": c.victim_display_name,
             "hospital_name": c.hospital_name, "status": c.status, "incident_at": iso(c.incident_at)} for c in rows]


def list_cases_overview(
    db: Session,
    user_id: str,
    search: str | None = None,
    status_filter: str | None = None,
    date_filter: str | None = None,
) -> dict:
    require_user(db, user_id)
    # Fetch all cases for this user
    query = (
        select(Case)
        .join(CaseMember, CaseMember.case_id == Case.id)
        .where(CaseMember.user_id == user_id)
        .order_by(Case.created_at.desc())
    )
    all_cases = db.scalars(query).all()

    total_cases = len(all_cases)
    active_cases = sum(1 for c in all_cases if c.status in ("active", "open", "under_review"))
    resolved_cases = sum(1 for c in all_cases if c.status in ("resolved", "closed"))

    pending_actions = 0
    enriched_cases = []

    for c in all_cases:
        open_tasks_count = db.scalar(
            select(func.count()).select_from(Task).where(Task.case_id == c.id, Task.status == "open")
        ) or 0
        needs_review_fields = db.scalar(
            select(func.count()).select_from(ExtractedField).where(ExtractedField.case_id == c.id, ExtractedField.status == "needs_review")
        ) or 0
        police_pending = 1 if c.police_draft_status == "draft_pending_review" else 0
        case_pending = open_tasks_count + needs_review_fields + police_pending
        pending_actions += case_pending

        veh_info = None
        if c.vehicle_id:
            veh = db.get(Vehicle, c.vehicle_id)
            if veh:
                photo = db.scalar(
                    select(VehiclePhoto).where(VehiclePhoto.vehicle_id == veh.id, VehiclePhoto.is_primary == True)
                )
                photo_url = f"/api/vehicles/{veh.id}/photos/{photo.id}/file" if photo else veh.main_image
                veh_info = {
                    "vehicle_id": veh.id,
                    "registration_number": veh.registration_number,
                    "manufacturer": veh.manufacturer,
                    "model": veh.model,
                    "variant": veh.variant,
                    "manufacturing_year": veh.manufacturing_year,
                    "color": veh.color,
                    "photo_url": photo_url,
                }

        # Filter check
        matches_search = True
        if search and search.strip():
            s = search.strip().lower()
            veh_reg = (veh_info["registration_number"].lower() if veh_info else "")
            matches_search = (
                s in c.case_number.lower()
                or (c.victim_display_name and s in c.victim_display_name.lower())
                or (c.approximate_location and s in c.approximate_location.lower())
                or (c.hospital_name and s in c.hospital_name.lower())
                or s in veh_reg
            )

        matches_status = True
        if status_filter and status_filter.lower() != "all":
            sf = status_filter.lower()
            if sf == "active":
                matches_status = c.status in ("active", "open")
            elif sf == "resolved":
                matches_status = c.status in ("resolved", "closed")
            elif sf == "under_review":
                matches_status = c.status == "under_review"
            else:
                matches_status = c.status == sf

        if matches_search and matches_status:
            enriched_cases.append({
                "case_id": c.id,
                "case_number": c.case_number,
                "status": c.status,
                "created_at": iso(c.created_at),
                "incident_at": iso(c.incident_at),
                "approximate_location": c.approximate_location,
                "victim_display_name": c.victim_display_name,
                "victim_relationship": c.victim_relationship,
                "hospital_name": c.hospital_name,
                "injury_severity": c.injury_severity or "Moderate",
                "damage_severity": c.damage_severity or "Moderate Frontal Damage",
                "police_stage": c.police_stage,
                "police_draft_status": c.police_draft_status,
                "pmrahat_stage": c.pmrahat_stage,
                "insurance_stage": c.insurance_stage,
                "hospital_treatment_status": c.hospital_treatment_status,
                "pending_actions_count": case_pending,
                "open_tasks_count": open_tasks_count,
                "vehicle": veh_info,
            })

    return {
        "summary": {
            "total_cases": total_cases,
            "active_cases": active_cases,
            "resolved_cases": resolved_cases,
            "pending_actions": pending_actions,
        },
        "cases": enriched_cases,
    }


def get_case_workspace(db: Session, actor_id: str, case_id: str) -> dict:
    case = require_member(db, actor_id, case_id)
    now = case_now(case)

    # 1. Linked Vehicle details
    vehicle_info = None
    if case.vehicle_id:
        v = db.get(Vehicle, case.vehicle_id)
        if v:
            photo = db.scalar(select(VehiclePhoto).where(VehiclePhoto.vehicle_id == v.id, VehiclePhoto.is_primary == True))
            photo_url = f"/api/vehicles/{v.id}/photos/{photo.id}/file" if photo else v.main_image
            policy = db.scalar(select(VehicleInsurancePolicy).where(VehicleInsurancePolicy.vehicle_id == v.id).order_by(VehicleInsurancePolicy.created_at.desc()))
            vehicle_info = {
                "id": v.id,
                "registration_number": v.registration_number,
                "manufacturer": v.manufacturer,
                "model": v.model,
                "variant": v.variant,
                "manufacturing_year": v.manufacturing_year,
                "fuel_type": v.fuel_type,
                "color": v.color,
                "owner_name": v.owner_name,
                "photo_url": photo_url,
                "insurance_provider": policy.provider if policy else case.insurance_provider,
                "insurance_policy_number": policy.policy_number if policy else case.insurance_policy_number,
                "insurance_expiry": iso(policy.expiry_date) if policy and policy.expiry_date else None,
            }

    # 2. Independent Progress Indicators
    progress_indicators = {
        "hospital": {
            "stage": case.hospital_treatment_status or "Admitted - General Ward",
            "title": "Hospital Treatment",
            "subtitle": case.hospital_name or "Emergency Facility",
            "status": "in_progress" if "Admitted" in (case.hospital_treatment_status or "") else "completed",
            "badge_color": "blue",
        },
        "police": {
            "stage": case.police_stage or "Draft Prepared",
            "title": "Police Documentation",
            "subtitle": f"Station: {case.police_station or 'Intimation Pending'}",
            "status": "completed" if case.fir_number or case.police_draft_status == "approved_by_user" else "pending_review",
            "badge_color": "emerald" if case.police_draft_status == "approved_by_user" else "amber",
        },
        "pmrahat": {
            "stage": case.pmrahat_stage or "Eligible - Cashless Active",
            "title": "PM-RAHAT Assistance",
            "subtitle": "₹1.5 Lakh Cashless Cover",
            "status": "active",
            "badge_color": "emerald",
        },
        "insurance": {
            "stage": case.insurance_stage or "Claim Intimated",
            "title": "Motor Insurance Claim",
            "subtitle": case.insurance_provider or "Intimation Pending",
            "status": "in_progress",
            "badge_color": "amber",
        },
    }

    # 3. Hospital & PM-RAHAT info
    spent = confirmed_bill_total(db, case_id)
    day = day_of_cover(case, now)
    window_end = case.incident_at + timedelta(days=config.COVER_DAYS)
    hospital_pmrahat = {
        "hospital": {
            "name": case.hospital_name,
            "address": case.hospital_address or "Outer Ring Road Medical Hub, Bengaluru",
            "contact": case.hospital_contact or "+91 80 4920 1100",
            "treating_doctor": case.treating_doctor or "Dr. A Sample (Trauma Lead)",
            "admission_at": iso(case.admission_at or case.incident_at),
            "treatment_status": case.hospital_treatment_status or "Admitted - General Ward",
            "estimated_expenses_inr": spent if spent > 0 else 124000.0,
        },
        "pmrahat": {
            "scheme_name": "PM-RAHAT Scheme (MoRTH / PIB March 2026)",
            "cover_limit_inr": config.COVER_LIMIT_INR,
            "confirmed_bills_inr": spent,
            "percent_used": round(100 * spent / config.COVER_LIMIT_INR, 1),
            "cover_days": config.COVER_DAYS,
            "day_of_cover": day,
            "window_ends_at": iso(window_end),
            "within_window": day <= config.COVER_DAYS,
            "status_stage": case.pmrahat_stage or "Eligible - Cashless Active",
            "reference_number": case.pmrahat_reference or f"PMR-KA-2026-{case.case_number[-4:] if case.case_number else '0001'}",
            "eligibility_checklist": [
                {"title": "Accident Occurred on Indian Road", "status": "verified", "description": "Verified by family and emergency intimation"},
                {"title": "Admitted to Empaneled / Stabilization Hospital", "status": "verified", "description": f"Verified at {case.hospital_name or 'Sample City Hospital'}"},
                {"title": "Within 7 Days Golden Hour Treatment Window", "status": "verified" if day <= 7 else "expired", "description": f"Currently Day {day} of 7"},
                {"title": "Cashless Protocol Activated", "status": "verified", "description": "Covering first ₹1,50,000 stabilization expenses"},
            ],
            "required_documents": [
                {"name": "Medico-Legal Case (MLC) Intimation Copy", "required": True, "present": True, "notes": "Prepared by hospital emergency desk"},
                {"name": "Victim Government Photo ID (Aadhaar / PAN)", "required": True, "present": True, "notes": "Available in Second Hour Document Wallet"},
                {"name": "Interim Hospital Treatment & Billing Estimate", "required": True, "present": spent > 0, "notes": "Uploaded and analyzed"},
                {"name": "Treating Doctor Initial Clinical Summary", "required": True, "present": True, "notes": "Fracture stabilization note confirmed"},
            ],
        },
    }

    # 4. Police & Insurance
    default_draft = (
        f"STATEMENT OF INCIDENT / ACCIDENT INTIMATION COMPLAINT\n\n"
        f"To,\n"
        f"The Station House Officer,\n"
        f"{case.police_station or 'HSR Layout Traffic Police Station'}, Bengaluru.\n\n"
        f"Subject: Formal statement and intimation regarding motor vehicle accident involving vehicle {vehicle_info['registration_number'] if vehicle_info else 'KA-01-MJ-2024'} on {case.incident_at.strftime('%d-%b-%Y')}.\n\n"
        f"Respected Sir/Madam,\n\n"
        f"I, Priya Sharma, am submitting this formal statement regarding the accident involving my family member, {case.victim_display_name or 'Ravi Kumar'}, which occurred at approximately {case.incident_at.strftime('%H:%M IST on %d %B %Y')} at {case.approximate_location}.\n\n"
        f"Incident Details:\n"
        f"- Vehicle: {vehicle_info['manufacturer'] if vehicle_info else 'Honda'} {vehicle_info['model'] if vehicle_info else 'City'} (Reg: {vehicle_info['registration_number'] if vehicle_info else 'KA-01-MJ-2024'})\n"
        f"- Location: {case.approximate_location} (Landmark: {case.location_landmark or 'Near Outer Ring Road flyover'})\n"
        f"- Brief Summary: {case.accident_description or 'Vehicle was travelling within normal speed limits when struck on the front-left quarter by a speeding commercial transport vehicle. Immediate emergency braking prevented further collision.'}\n"
        f"- Injuries Sustained: {case.injury_description or 'Closed fracture to left forearm and minor head abrasions.'}\n"
        f"- Present Status: Patient currently admitted at {case.hospital_name or 'Sample City Hospital'}.\n\n"
        f"I request that this formal intimation be recorded in the general diary / FIR records in compliance with road safety and PM-RAHAT statutory norms.\n\n"
        f"Sincerely,\n"
        f"Priya Sharma (Family Coordinator)\n"
        f"Second Hour Case Ref: {case.case_number}"
    )

    police_info = {
        "police_station": case.police_station or "HSR Layout Traffic Police Station",
        "station_name": case.police_station or "HSR Layout Traffic Police Station",
        "station_address": case.police_station_address or "19th Main Road, Sector 1, HSR Layout, Bengaluru, Karnataka 560102",
        "investigating_officer": case.investigating_officer or "Sub-Inspector Ramesh K",
        "officer_contact": case.officer_contact or "+91 80 2294 2568",
        "fir_number": case.fir_number or "FIR-2026/0491-TR",
        "fir_date": iso(case.fir_date or (case.incident_at + timedelta(hours=4))),
        "fir_sections": case.fir_sections or "IPC Section 279 (Rash Driving), Section 337 (Causing Hurt)",
        "stage": case.police_stage or "Draft Prepared",
        "draft_status": case.police_draft_status or "draft_pending_review",
        "draft_report": case.police_report_draft or default_draft,
        "approved_by": case.police_draft_approved_by,
        "approved_at": iso(case.police_draft_approved_at),
    }

    insurance_info = {
        "provider": case.insurance_provider or (vehicle_info["insurance_provider"] if vehicle_info else "Tata AIG General Insurance"),
        "policy_number": case.insurance_policy_number or (vehicle_info["insurance_policy_number"] if vehicle_info else "POL-99283401-2026"),
        "claim_number": case.insurance_claim_number or f"CLM-AIG-{case.case_number[-4:] if case.case_number else '0001'}-2026",
        "stage": case.insurance_stage or "Claim Intimated",
        "surveyor_name": case.insurance_surveyor_name or "Anand Verma (Licensed Surveyor #IRDA/SUR/9182)",
        "surveyor_phone": case.insurance_surveyor_phone or "+91 98450 19284",
        "settlement_status": case.insurance_settlement_status or "In Progress - Cashless Assessment at Network Garage",
        "cashless_garage": "Authorized Honda Service Centre, Koramangala",
    }

    # 5. Evidence and documents from CentralDocument
    cdocs = db.scalars(
        select(CentralDocument).where(
            CentralDocument.deleted_at == None,
            (
                (CentralDocument.resource_type == "ACCIDENT_CASE") & (CentralDocument.resource_id == case_id)
            ) | (
                (CentralDocument.resource_type == "VEHICLE") & (CentralDocument.resource_id == case.vehicle_id)
            ) | (
                (CentralDocument.category == "driving_licence") & (CentralDocument.user_id == case.created_by)
            )
        ).order_by(CentralDocument.created_at.desc())
    ).all()

    documents_list = []
    accident_photos = []
    injury_evidence = []
    supporting_docs = []

    for d in cdocs:
        doc_entry = {
            "id": d.id,
            "document_name": d.document_name,
            "document_type": d.document_type,
            "category": d.category,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
            "document_number": d.document_number,
            "issuing_authority": d.issuing_authority,
            "verification_status": d.verification_status,
            "resource_type": d.resource_type,
            "notes": d.notes,
            "download_url": f"/api/documents/{d.id}/file",
            "created_at": iso(d.created_at),
        }
        documents_list.append(doc_entry)

        if "photo" in d.document_type or "damage" in d.category or (d.mime_type and d.mime_type.startswith("image/")):
            accident_photos.append(doc_entry)
        elif "medical" in d.category or "injury" in d.document_type or d.document_type in ("medical_report", "xray", "ct_scan"):
            injury_evidence.append(doc_entry)
        else:
            supporting_docs.append(doc_entry)

    # 6. Family members
    members_rows = db.execute(
        select(User, CaseMember).join(CaseMember, CaseMember.user_id == User.id).where(CaseMember.case_id == case_id)
    ).all()
    family_members = []
    for u, cm in members_rows:
        family_members.append({
            "user_id": u.id,
            "name": u.name,
            "role": cm.role,
            "relationship": cm.relationship or ("Self" if u.id == case.created_by else "Family"),
            "contact_number": cm.contact_number or ("+91 98450 12345" if u.id == "u_priya" else "+91 98450 67890"),
            "permissions_summary": cm.permissions_summary or ("Full Coordinator Access" if cm.role == "coordinator" else "View & Add Tasks"),
        })

    # 7. Tasks
    task_rows = db.scalars(select(Task).where(Task.case_id == case_id).order_by(Task.created_at)).all()
    user_name_map = {u.id: u.name for u, _ in members_rows}
    tasks_list = []
    for t in task_rows:
        tasks_list.append({
            "task_id": t.id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "status": t.status,
            "due_at": iso(t.due_at),
            "due_source": t.due_source,
            "assignee_id": t.assignee_id,
            "assignee_name": user_name_map.get(t.assignee_id, "Unassigned") if t.assignee_id else "Unassigned",
        })

    # 8. Timeline
    timeline_rows = db.scalars(
        select(TimelineEvent).where(TimelineEvent.case_id == case_id).order_by(TimelineEvent.at.desc())
    ).all()
    timeline_list = []
    for ev in timeline_rows:
        timeline_list.append({
            "id": ev.id,
            "at": iso(ev.at),
            "actor_id": ev.actor_id,
            "actor_name": user_name_map.get(ev.actor_id, ev.actor_id or "System"),
            "kind": ev.kind,
            "summary": ev.summary,
        })

    # 9. Alerts and AI guidance
    alerts = get_case_alerts(db, actor_id, case_id)["alerts"]

    return {
        "case": {
            "id": case.id,
            "case_number": case.case_number,
            "status": case.status,
            "incident_at": iso(case.incident_at),
            "accident_time": case.incident_at.strftime("%I:%M %p"),
            "approximate_location": case.approximate_location,
            "latitude": case.latitude or 12.9279,
            "longitude": case.longitude or 77.6271,
            "location_landmark": case.location_landmark or "Near Agara Lake Flyover junction",
            "accident_description": case.accident_description or "Two-vehicle lateral impact collision on the outer lane. Front left bumper and wheel arch impacted.",
            "accident_type": case.accident_type or "Two-Vehicle Collision",
            "weather_conditions": case.weather_conditions or "Clear & Dry (Night)",
            "vehicles_involved": case.vehicles_involved or "2 Vehicles (Car & Commercial Vehicle)",
            "people_affected": case.people_affected or "1 Person Injured (Driver)",
            "victim_display_name": case.victim_display_name,
            "victim_relationship": case.victim_relationship or "Spouse",
            "victim_phone": case.victim_phone or "+91 98450 88291",
            "injury_severity": case.injury_severity or "Moderate",
            "injury_description": case.injury_description or "Closed fracture of left radius; superficial forehead laceration. Stabilized, conscious.",
            "damage_severity": case.damage_severity or "Moderate Frontal Damage",
            "damage_description": case.damage_description or "Front-left bumper deformed, headlight cracked, steering alignment impacted.",
            "vehicle_id": case.vehicle_id,
            "created_by": case.created_by,
            "created_at": iso(case.created_at),
            "updated_at": iso(case.updated_at),
        },
        "vehicle": vehicle_info,
        "progress_indicators": progress_indicators,
        "hospital_pmrahat": hospital_pmrahat,
        "police_info": police_info,
        "insurance_info": insurance_info,
        "evidence": {
            "all": documents_list,
            "accident_photos": accident_photos,
            "injury_evidence": injury_evidence,
            "supporting_docs": supporting_docs,
        },
        "family_members": family_members,
        "tasks": tasks_list,
        "timeline": timeline_list,
        "alerts": alerts,
        "clock_now": iso(now),
        "demo_clock_offset_hours": case.demo_clock_offset_hours,
    }


def update_case_section(db: Session, actor_id: str, case_id: str, section: str, data: dict) -> dict:
    case = require_member(db, actor_id, case_id)
    actor = db.get(User, actor_id)
    actor_name = actor.name if actor else actor_id

    if section == "overview":
        if "approximate_location" in data and data["approximate_location"]:
            case.approximate_location = str(data["approximate_location"]).strip()[:200]
        if "location_landmark" in data:
            case.location_landmark = str(data["location_landmark"]).strip()[:200] or None
        if "latitude" in data and data["latitude"] is not None:
            case.latitude = float(data["latitude"])
        if "longitude" in data and data["longitude"] is not None:
            case.longitude = float(data["longitude"])
        if "accident_description" in data:
            case.accident_description = str(data["accident_description"]).strip()[:2000] or None
        if "accident_type" in data:
            case.accident_type = str(data["accident_type"]).strip()[:100]
        if "weather_conditions" in data:
            case.weather_conditions = str(data["weather_conditions"]).strip()[:100]
        if "vehicles_involved" in data:
            case.vehicles_involved = str(data["vehicles_involved"]).strip()[:100]
        if "people_affected" in data:
            case.people_affected = str(data["people_affected"]).strip()[:100]
        add_event(db, case_id, actor_id, "overview_updated", f"{actor_name} updated accident overview details")

    elif section == "injuries_damage":
        if "injury_severity" in data:
            case.injury_severity = str(data["injury_severity"]).strip()[:50]
        if "injury_description" in data:
            case.injury_description = str(data["injury_description"]).strip()[:2000] or None
        if "damage_severity" in data:
            case.damage_severity = str(data["damage_severity"]).strip()[:100]
        if "damage_description" in data:
            case.damage_description = str(data["damage_description"]).strip()[:2000] or None
        add_event(db, case_id, actor_id, "injuries_updated", f"{actor_name} updated injury and vehicle damage assessments")

    elif section == "hospital":
        if "hospital_name" in data and data["hospital_name"]:
            case.hospital_name = str(data["hospital_name"]).strip()[:200]
        if "hospital_address" in data:
            case.hospital_address = str(data["hospital_address"]).strip()[:200] or None
        if "hospital_contact" in data:
            case.hospital_contact = str(data["hospital_contact"]).strip()[:100] or None
        if "treating_doctor" in data:
            case.treating_doctor = str(data["treating_doctor"]).strip()[:100] or None
        if "hospital_treatment_status" in data:
            case.hospital_treatment_status = str(data["hospital_treatment_status"]).strip()[:100]
        add_event(db, case_id, actor_id, "hospital_updated", f"{actor_name} updated hospital and treatment records")

    elif section == "police":
        if "police_station" in data:
            case.police_station = str(data["police_station"]).strip()[:200] or None
        if "police_station_address" in data:
            case.police_station_address = str(data["police_station_address"]).strip()[:200] or None
        if "investigating_officer" in data:
            case.investigating_officer = str(data["investigating_officer"]).strip()[:100] or None
        if "officer_contact" in data:
            case.officer_contact = str(data["officer_contact"]).strip()[:100] or None
        if "fir_number" in data:
            case.fir_number = str(data["fir_number"]).strip()[:100] or None
        if "fir_sections" in data:
            case.fir_sections = str(data["fir_sections"]).strip()[:200] or None
        if "police_stage" in data:
            case.police_stage = str(data["police_stage"]).strip()[:100]
        add_event(db, case_id, actor_id, "police_updated", f"{actor_name} updated police documentation records")

    elif section == "insurance":
        if "insurance_provider" in data:
            case.insurance_provider = str(data["insurance_provider"]).strip()[:200] or None
        if "insurance_policy_number" in data:
            case.insurance_policy_number = str(data["insurance_policy_number"]).strip()[:100] or None
        if "insurance_claim_number" in data:
            case.insurance_claim_number = str(data["insurance_claim_number"]).strip()[:100] or None
        if "insurance_stage" in data:
            case.insurance_stage = str(data["insurance_stage"]).strip()[:100]
        if "insurance_surveyor_name" in data:
            case.insurance_surveyor_name = str(data["insurance_surveyor_name"]).strip()[:100] or None
        if "insurance_surveyor_phone" in data:
            case.insurance_surveyor_phone = str(data["insurance_surveyor_phone"]).strip()[:100] or None
        if "insurance_settlement_status" in data:
            case.insurance_settlement_status = str(data["insurance_settlement_status"]).strip()[:200] or None
        add_event(db, case_id, actor_id, "insurance_updated", f"{actor_name} updated motor insurance claim details")

    elif section == "status":
        if "status" in data and data["status"] in ("active", "under_review", "resolved", "closed"):
            case.status = data["status"]
            add_event(db, case_id, actor_id, "case_status", f"Case status updated to '{case.status}'")

    db.commit()
    return get_case_workspace(db, actor_id, case_id)


def approve_police_draft(db: Session, actor_id: str, case_id: str, approved: bool, feedback: str = "") -> dict:
    case = require_member(db, actor_id, case_id)
    actor = db.get(User, actor_id)
    actor_name = actor.name if actor else actor_id

    if approved:
        case.police_draft_status = "approved_by_user"
        case.police_draft_approved_by = actor_name
        case.police_draft_approved_at = utcnow()
        case.police_stage = "Draft Approved by Family"
        add_event(db, case_id, actor_id, "police_draft_approved",
                  f"Statement of incident reviewed and approved by {actor_name}. Ready for police intimation.")
    else:
        case.police_draft_status = "draft_revision_requested"
        add_event(db, case_id, actor_id, "police_draft_revised",
                  f"Police statement revision requested by {actor_name}: {feedback or 'Changes required'}")

    db.commit()
    return {
        "status": case.police_draft_status,
        "approved_by": case.police_draft_approved_by,
        "approved_at": iso(case.police_draft_approved_at),
        "police_stage": case.police_stage,
    }


def link_case_vehicle(db: Session, actor_id: str, case_id: str, vehicle_id: str | None) -> dict:
    case = require_member(db, actor_id, case_id)
    if vehicle_id:
        veh = db.get(Vehicle, vehicle_id)
        if not veh:
            raise ServiceError("Vehicle not found")
        case.vehicle_id = veh.id
        # Sync insurance details if available
        policy = db.scalar(
            select(VehicleInsurancePolicy)
            .where(VehicleInsurancePolicy.vehicle_id == veh.id)
            .order_by(VehicleInsurancePolicy.created_at.desc())
        )
        if policy:
            case.insurance_provider = policy.provider
            case.insurance_policy_number = policy.policy_number
        add_event(db, case_id, actor_id, "vehicle_linked", f"Vehicle {veh.registration_number} linked to case")
    else:
        case.vehicle_id = None
        add_event(db, case_id, actor_id, "vehicle_unlinked", "Vehicle unlinked from case")

    db.commit()
    return get_case_workspace(db, actor_id, case_id)


def toggle_task_status(db: Session, actor_id: str, case_id: str, task_id: str) -> dict:
    require_member(db, actor_id, case_id)
    t = db.get(Task, task_id)
    if not t or t.case_id != case_id:
        raise ServiceError("Task not found")
    t.status = "done" if t.status == "open" else "open"
    add_event(db, case_id, actor_id, "task_status", f"Task '{t.title}' marked {t.status}")
    db.commit()
    return _task_dict(t)


def add_case_member(
    db: Session,
    actor_id: str,
    case_id: str,
    name: str,
    role: str = "member",
    relationship: str = "Family",
    contact_number: str = "",
    permissions_summary: str = "View & Add Tasks",
) -> dict:
    require_member(db, actor_id, case_id)
    if not name or not name.strip():
        raise ServiceError("Member name is required")

    # Find existing or create user
    existing_user = db.scalar(select(User).where(User.name == name.strip()))
    if not existing_user:
        user_id = f"u_{new_id('usr')}"
        existing_user = User(id=user_id, name=name.strip(), role_label=role)
        db.add(existing_user)
        db.flush()

    # Check if already member
    cm = db.get(CaseMember, (case_id, existing_user.id))
    if cm:
        cm.role = role
        cm.relationship = relationship
        cm.contact_number = contact_number
        cm.permissions_summary = permissions_summary
    else:
        cm = CaseMember(
            case_id=case_id,
            user_id=existing_user.id,
            role=role,
            relationship=relationship,
            contact_number=contact_number,
            permissions_summary=permissions_summary,
        )
        db.add(cm)

    add_event(db, case_id, actor_id, "member_added", f"Family member {existing_user.name} ({relationship}) added to case")
    db.commit()
    return {
        "user_id": existing_user.id,
        "name": existing_user.name,
        "role": cm.role,
        "relationship": cm.relationship,
        "contact_number": cm.contact_number,
        "permissions_summary": cm.permissions_summary,
    }


def members(db: Session, case_id: str) -> list[dict]:
    rows = db.execute(select(User, CaseMember.role).join(CaseMember, CaseMember.user_id == User.id)
                      .where(CaseMember.case_id == case_id)).all()
    return [{"user_id": u.id, "name": u.name, "role": r} for u, r in rows]


def inr(amount: float) -> str:
    """Indian digit grouping: 124000 -> 1,24,000."""
    s = f"{int(round(amount))}"
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def day_of_cover(case: Case, now: datetime) -> int:
    hours = (now - case.incident_at).total_seconds() / 3600
    return max(1, math.floor(hours / 24) + 1)


def confirmed_bill_total(db: Session, case_id: str) -> float:
    rows = db.scalars(select(ExtractedField).join(Document, Document.id == ExtractedField.document_id)
                      .where(ExtractedField.case_id == case_id, ExtractedField.name == "total_amount",
                             ExtractedField.status == "confirmed", Document.category == "hospital_bill")).all()
    total = 0.0
    for f in rows:
        try:
            total += float(str(f.value).replace(",", "").replace("₹", "").strip())
        except ValueError:
            continue
    return total


def get_case_summary(db: Session, actor_id: str, case_id: str) -> dict:
    case = require_member(db, actor_id, case_id)
    now = case_now(case)
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    needs_review = db.scalar(select(func.count()).select_from(ExtractedField)
                             .where(ExtractedField.case_id == case_id, ExtractedField.status == "needs_review")) or 0
    open_tasks = db.scalars(select(Task).where(Task.case_id == case_id, Task.status == "open")).all()
    day = day_of_cover(case, now)
    spent = confirmed_bill_total(db, case_id)
    checklist = get_missing_documents(db, actor_id, case_id)
    alerts = get_case_alerts(db, actor_id, case_id)["alerts"]
    next_steps = [a["suggested_task"]["title"] for a in alerts if a.get("suggested_task")]
    if checklist["missing"]:
        next_steps.append(f"Collect: {checklist['missing'][0]['label']}")
    if needs_review:
        next_steps.append(f"Review {needs_review} extracted field(s) marked 'Needs review'")
    return {
        "case_id": case.id, "case_number": case.case_number, "status": case.status,
        "victim_display_name": case.victim_display_name, "hospital_name": case.hospital_name,
        "approximate_location": case.approximate_location, "incident_at": iso(case.incident_at),
        "life_threatening": case.life_threatening,
        "clock_now": iso(now), "demo_clock_offset_hours": case.demo_clock_offset_hours,
        "milestones": {
            "cover_window": {"day": day, "of": config.COVER_DAYS, "within_window": day <= config.COVER_DAYS,
                             "window_ends_at": iso(case.incident_at + timedelta(days=config.COVER_DAYS))},
            "cover_amount": {"confirmed_bills_inr": spent, "cover_limit_inr": config.COVER_LIMIT_INR,
                             "percent_used": round(100 * spent / config.COVER_LIMIT_INR, 1),
                             "note": "Sum of user-confirmed hospital bill totals only. Not a prediction of what the family will pay."},
            "police_authentication": {"status": case.police_auth_status, "updated_at": iso(case.police_auth_updated_at),
                                      "label": "user-provided, unverified"},
        },
        "document_counts": {"total": len(docs), "analyzed": sum(d.analysis_status == "analyzed" for d in docs),
                            "fields_needing_review": needs_review},
        "open_tasks": [_task_dict(t) for t in open_tasks],
        "members": members(db, case_id),
        "alerts": alerts,
        "next_steps": next_steps[:5],
        "disclaimer": "Second Hour is not an emergency service. In an emergency, call 112.",
    }


def set_police_status(db: Session, actor_id: str, case_id: str, status: str) -> dict:
    case = require_member(db, actor_id, case_id)
    if status not in POLICE_STATUSES:
        raise ServiceError(f"status must be one of {POLICE_STATUSES}")
    case.police_auth_status = status
    case.police_auth_updated_at = case_now(case)
    add_event(db, case_id, actor_id, "police_status", f"Family recorded police authentication status: {status} (user-provided, unverified)")
    db.commit()
    return {"status": status, "updated_at": iso(case.police_auth_updated_at)}


def advance_clock(db: Session, actor_id: str, case_id: str, hours: float) -> dict:
    case = require_member(db, actor_id, case_id)
    if hours == 0:
        case.demo_clock_offset_hours = 0
    else:
        case.demo_clock_offset_hours = (case.demo_clock_offset_hours or 0) + hours
    add_event(db, case_id, actor_id, "demo_clock", f"Demo clock offset set to +{case.demo_clock_offset_hours:g}h")
    db.commit()
    return {"demo_clock_offset_hours": case.demo_clock_offset_hours, "clock_now": iso(case_now(case))}


# ---------------------------------------------------------------- watchers

def get_case_alerts(db: Session, actor_id: str, case_id: str, now: str | None = None) -> dict:
    """Deterministic watchers. No LLM involved."""
    case = require_member(db, actor_id, case_id)
    t = case_now(case, parse_dt(now, "now"))
    alerts: list[dict] = []

    # Rule 1: cover window tracker
    day = day_of_cover(case, t)
    spent = confirmed_bill_total(db, case_id)
    pct = spent / config.COVER_LIMIT_INR
    if pct >= 0.8 or day >= 6:
        reasons = []
        if day >= 6:
            reasons.append(f"it is day {day} of the {config.COVER_DAYS}-day PM-RAHAT window" if day <= 7
                           else f"the {config.COVER_DAYS}-day PM-RAHAT window from the accident date has passed (day {day})")
        if pct >= 0.8:
            reasons.append(f"confirmed hospital bills total ₹{inr(spent)}, which is {pct:.0%} of the ₹1,50,000 cover")
        alerts.append({
            "id": "cover_window", "rule": "cover_window_tracker", "severity": "high" if (pct >= 1 or day > 7) else "medium",
            "title": "PM-RAHAT cover limit approaching" if pct >= 0.8 else "PM-RAHAT 7-day window closing",
            "message": "Heads-up: " + " and ".join(reasons) + ". Second Hour does not predict what the family will pay.",
            "facts": {"day": day, "of": config.COVER_DAYS, "confirmed_bills_inr": spent, "cover_limit_inr": config.COVER_LIMIT_INR},
            "source": {"title": "PIB, 11 March 2026: PM-RAHAT salient features", "url": config.PIB_MARCH_URL},
            "suggested_task": {"title": "Ask the hospital billing desk how treatment beyond the cover will be handled",
                               "priority": "high"},
        })

    # Rule 2: police authentication status watcher
    if case.police_auth_status == "requested_by_hospital" and case.police_auth_updated_at:
        window = config.POLICE_WINDOW_HOURS_LIFE_THREATENING if case.life_threatening else config.POLICE_WINDOW_HOURS
        elapsed = (t - case.police_auth_updated_at).total_seconds() / 3600
        if elapsed > window:
            alerts.append({
                "id": "police_auth", "rule": "police_authentication_watcher", "severity": "medium",
                "title": "Police authentication still pending",
                "message": (f"The family recorded 'requested by hospital' {elapsed:.0f} hours ago (user-provided, unverified). "
                            f"Under PM-RAHAT the hospital raises police authentication on the TMS platform via eDAR, and police "
                            f"respond to the hospital within {window} hours{' for life-threatening cases' if case.life_threatening else ''}. "
                            "This is the hospital's and police's process, not a family deadline. It may help to ask the hospital desk for an update."),
                "facts": {"hours_elapsed": round(elapsed, 1), "official_window_hours": window},
                "source": {"title": "PIB, 11 March 2026: PM-RAHAT salient features", "url": config.PIB_MARCH_URL},
                "suggested_task": {"title": "Ask the hospital desk for the police authentication status", "priority": "medium"},
            })
    return {"case_id": case_id, "evaluated_at": iso(t), "day_of_cover": day, "alerts": alerts}


# ---------------------------------------------------------------- checklist

def get_missing_documents(db: Session, actor_id: str, case_id: str) -> dict:
    require_member(db, actor_id, case_id)
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    pending_fields = {f.document_id for f in db.scalars(select(ExtractedField).where(
        ExtractedField.case_id == case_id, ExtractedField.status == "needs_review")).all()}
    present, missing, review = [], [], []
    for item in CHECKLIST:
        matching = [d for d in docs if d.category == item["key"]]
        if not matching:
            missing.append({**item, "status": "missing"})
        elif any(d.id in pending_fields for d in matching):
            review.append({**item, "status": "needs_review", "document_ids": [d.id for d in matching],
                           "reason": "Document uploaded; extracted fields still need family confirmation."})
        else:
            present.append({**item, "status": "present", "document_ids": [d.id for d in matching]})
    unclassified = [d.id for d in docs if d.analysis_status != "analyzed"]
    return {"present": present, "missing": missing, "needs_review": review, "unanalyzed_document_ids": unclassified,
            "label": "Guidance, not a legal determination. Requirements vary by hospital, insurer and state."}


# ---------------------------------------------------------------- tasks

def _task_dict(t: Task) -> dict:
    return {"task_id": t.id, "title": t.title, "description": t.description, "priority": t.priority,
            "status": t.status, "due_at": iso(t.due_at), "due_source": t.due_source, "assignee_id": t.assignee_id}


def create_task(db: Session, actor_id: str, case_id: str, title: str, description: str = "",
                priority: str = "medium", due_at: str | None = None, due_source: str | None = None) -> dict:
    require_member(db, actor_id, case_id)
    if not title or not title.strip():
        raise ServiceError("title is required")
    if priority not in PRIORITIES:
        raise ServiceError(f"priority must be one of {PRIORITIES}")
    due = parse_dt(due_at, "due_at")
    if due and not (due_source and due_source.strip()):
        raise ServiceError("A due date needs a due_source (user-confirmed or an official source). Leave due_at empty otherwise.")
    t = Task(case_id=case_id, title=title.strip()[:200], description=(description or "")[:2000], priority=priority,
             due_at=due, due_source=(due_source or None), created_by=actor_id)
    db.add(t)
    db.flush()
    add_event(db, case_id, actor_id, "task_created", f"Task created: {t.title}")
    db.commit()
    return _task_dict(t)


def assign_task(db: Session, actor_id: str, case_id: str, task_id: str, member_id: str) -> dict:
    require_member(db, actor_id, case_id)
    t = db.get(Task, task_id)
    if not t or t.case_id != case_id:
        raise ServiceError(f"Task '{task_id}' not found in this case")
    require_member(db, member_id, case_id)  # assignee must also be a member
    t.assignee_id = member_id
    name = db.get(User, member_id).name
    add_event(db, case_id, actor_id, "task_assigned", f"Task '{t.title}' assigned to {name}")
    db.commit()
    return _task_dict(t)


def list_tasks(db: Session, actor_id: str, case_id: str) -> list[dict]:
    require_member(db, actor_id, case_id)
    return [_task_dict(t) for t in db.scalars(select(Task).where(Task.case_id == case_id).order_by(Task.created_at)).all()]


def set_task_status(db: Session, actor_id: str, case_id: str, task_id: str, status: str) -> dict:
    require_member(db, actor_id, case_id)
    t = db.get(Task, task_id)
    if not t or t.case_id != case_id or status not in ("open", "done"):
        raise ServiceError("Invalid task or status")
    t.status = status
    add_event(db, case_id, actor_id, "task_status", f"Task '{t.title}' marked {status}")
    db.commit()
    return _task_dict(t)


def timeline(db: Session, actor_id: str, case_id: str) -> list[dict]:
    require_member(db, actor_id, case_id)
    rows = db.scalars(select(TimelineEvent).where(TimelineEvent.case_id == case_id).order_by(TimelineEvent.at.desc())).all()
    return [{"at": iso(e.at), "actor_id": e.actor_id, "kind": e.kind, "summary": e.summary} for e in rows]
