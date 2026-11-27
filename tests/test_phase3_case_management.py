"""Phase 3: Accident Cases & Case Management Test Suite.

Validates:
1. Migration safety and preservation of Phase 1 and Phase 2 entities.
2. Multi-case creation and persistence with unique case reference numbers.
3. Normalized multi-vehicle association (registered and third-party).
4. Involved people tracking with non-diagnostic injury reporting.
5. Evidence uploads via StorageAdapter with SHA-256 validation.
6. Task lifecycle (creation, priority, categories, completion timestamp).
7. Append-only case status transitions and timeline event consistency.
8. Authorization boundaries, cross-user isolation, and member permission enforcement.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete

from app.db import (
    Case,
    CaseEvidence,
    CaseInvolvedPerson,
    CaseMember,
    CaseStatusTransition,
    CaseVehicle,
    CentralDocument,
    SessionLocal,
    Task,
    TimelineEvent,
    User,
    Vehicle,
)
from app.services import cases as case_svc
from app.services.common import PermissionDenied, ServiceError


def test_phase3_migration_and_existing_data_intact():
    """Verify that existing Phase 1 users, Phase 2 vehicles & documents remain intact."""
    db = SessionLocal()
    try:
        priya = db.get(User, "u_priya")
        assert priya is not None
        assert "Priya" in priya.name

        arjun = db.get(User, "u_arjun")
        assert arjun is not None

        honda = db.get(Vehicle, "veh_demo_honda")
        assert honda is not None
        assert honda.registration_number == "KA-01-MJ-2024"

        dl = db.get(CentralDocument, "cdoc_demo_dl")
        assert dl is not None

        demo_case = db.get(Case, "case_demo")
        assert demo_case is not None
        assert demo_case.owner_id == "u_priya"
        assert demo_case.primary_vehicle_id == "veh_demo_honda"
        assert demo_case.is_active is True
    finally:
        db.close()


def test_phase3_multi_case_creation_and_persistence():
    """Verify an authenticated user can create multiple cases with unique case numbers."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        res = case_svc.create_case(
            db=db,
            actor_id="u_priya",
            incident_at=(now - timedelta(hours=3)).isoformat(),
            approximate_location="Indiranagar 100ft Road, Bengaluru",
            title="Two Wheeler Skid — Indiranagar",
            accident_type="Single Vehicle Skid",
            injury_severity="Minor",
            damage_severity="Minor Scratch",
            accident_description="Two-wheeler slipped on wet road near metro station pillar 42.",
        )

        assert res["case_id"] is not None
        assert res["case_number"].startswith("SH-")
        assert res["case_reference_number"] == res["case_number"]
        assert res["status"] == "active"

        # Verify case record in database
        case_rec = db.get(Case, res["case_id"])
        assert case_rec is not None
        assert case_rec.owner_id == "u_priya"
        assert case_rec.title == "Two Wheeler Skid — Indiranagar"
        assert case_rec.is_active is True

        # Verify initial CaseCoordinator member
        cm = db.get(CaseMember, (case_rec.id, "u_priya"))
        assert cm is not None
        assert cm.role == "coordinator"
        assert cm.can_view_case is True
        assert cm.can_upload_evidence is True

        # Verify initial CaseStatusTransition
        transitions = case_svc.list_case_status_transitions(db, "u_priya", case_rec.id)
        assert len(transitions) >= 1
        assert transitions[0]["from_status"] == "none"
        assert transitions[0]["to_status"] == "active"
        assert transitions[0]["transition_trigger"] == "case_creation"

        # Verify timeline event created
        events = case_svc.timeline(db, "u_priya", case_rec.id)
        assert any(e["kind"] == "case_created" for e in events)

        # Test soft deletion
        del_res = case_svc.delete_case(db, "u_priya", case_rec.id)
        assert del_res["deleted"] is True
        db.refresh(case_rec)
        assert case_rec.is_active is False
        assert case_rec.deleted_at is not None

        # Clean up created case and associated child records
        db.execute(delete(CaseMember).where(CaseMember.case_id == case_rec.id))
        db.execute(delete(CaseStatusTransition).where(CaseStatusTransition.case_id == case_rec.id))
        db.execute(delete(TimelineEvent).where(TimelineEvent.case_id == case_rec.id))
        db.delete(case_rec)
        db.commit()
    finally:
        db.close()


def test_phase3_multi_vehicle_and_third_party_association():
    """Verify a case can associate both registered and third-party vehicles."""
    db = SessionLocal()
    try:
        # 1. Associate Priya's registered Honda City
        cv1 = case_svc.add_case_vehicle(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            data={
                "vehicle_id": "veh_demo_honda",
                "vehicle_involvement_type": "primary_subject",
                "damage_severity": "Moderate Frontal Damage",
                "damage_description": "Front bumper cracked, left headlamp lens broken",
            },
        )
        assert cv1["id"] is not None
        assert cv1["registration_number"] == "KA-01-MJ-2024"
        assert cv1["is_third_party"] is False

        # 2. Add an unregistered/third-party vehicle without creating a vehicle registry entry
        cv2 = case_svc.add_case_vehicle(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            data={
                "is_third_party": True,
                "registration_number": "KA-04-TR-9912",
                "make_model": "Ashok Leyland Dost",
                "color": "Commercial Yellow",
                "driver_name": "Suresh Babu",
                "driver_contact": "+91 94480 88771",
                "insurance_company": "United India Insurance",
                "insurance_policy_no": "UII-449102-2026",
                "damage_severity": "Minor Rear Bumper Dent",
                "damage_description": "Scratched rear bumper paint",
            },
        )
        assert cv2["id"] is not None
        assert cv2["registration_number"] == "KA-04-TR-9912"
        assert cv2["is_third_party"] is True

        # Verify both appear in list_case_vehicles
        all_vehs = case_svc.list_case_vehicles(db, "u_priya", "case_demo")
        reg_numbers = [v["registration_number"] for v in all_vehs]
        assert "KA-01-MJ-2024" in reg_numbers
        assert "KA-04-TR-9912" in reg_numbers

        # Verify timeline recorded vehicle association
        events = case_svc.timeline(db, "u_priya", "case_demo")
        assert any(e["kind"] == "vehicle_associated" for e in events)

        # Clean up added vehicle
        case_svc.remove_case_vehicle(db, "u_priya", "case_demo", cv2["id"])
    finally:
        db.close()


def test_phase3_involved_people_tracking():
    """Verify adding, updating and listing involved people with reported injuries."""
    db = SessionLocal()
    try:
        # Add a passenger
        p1 = case_svc.add_involved_person(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            data={
                "full_name": "Kavita Sharma",
                "involvement_type": "passenger",
                "relationship_to_coordinator": "Mother-in-law",
                "contact_number": "+91 98450 44332",
                "reported_injury_status": "minor",
                "injury_description": "Mild seatbelt contusion on collarbone, ambulatory",
                "hospital_name": "Sample City Hospital Emergency Room",
            },
        )
        assert p1["id"] is not None
        assert p1["full_name"] == "Kavita Sharma"
        assert p1["reported_injury_status"] == "minor"

        # Update injury status
        updated = case_svc.update_involved_person(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            person_id=p1["id"],
            data={"reported_injury_status": "uninjured", "notes": "Discharged after x-ray clearance"},
        )
        assert updated["reported_injury_status"] == "uninjured"
        assert updated["notes"] == "Discharged after x-ray clearance"

        # Verify in list
        people = case_svc.list_involved_people(db, "u_priya", "case_demo")
        assert any(p["id"] == p1["id"] for p in people)

        # Clean up
        case_svc.remove_involved_person(db, "u_priya", "case_demo", p1["id"])
    finally:
        db.close()


def test_phase3_case_evidence_upload_and_storage():
    """Verify evidence file upload via StorageAdapter, SHA-256 calculation, and retrieval."""
    db = SessionLocal()
    try:
        test_img = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00" + b"\x42" * 512
        ev = case_svc.upload_case_evidence(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            title="Skid Marks on Lane 2",
            file_name="skid_marks_lane2.jpg",
            content=test_img,
            mime_type="image/jpeg",
            evidence_category="skid_marks",
            description="Tire skid marks extending 12 meters before collision point",
            evidence_source="user_upload",
            geo_latitude=12.9281,
            geo_longitude=77.6273,
        )

        assert ev["id"] is not None
        assert ev["title"] == "Skid Marks on Lane 2"
        assert ev["evidence_category"] == "skid_marks"
        assert ev["sha256"] is not None
        assert ev["file_size_bytes"] == len(test_img)

        # Retrieve file binary from storage adapter
        path, mime, filename = case_svc.get_case_evidence_file(db, "u_priya", "case_demo", ev["id"])
        assert mime == "image/jpeg"
        assert filename == "skid_marks_lane2.jpg"
        assert Path(path).exists()
        assert Path(path).read_bytes() == test_img

        # Verify listed in case evidence
        all_ev = case_svc.list_case_evidence(db, "u_priya", "case_demo")
        assert any(e["id"] == ev["id"] for e in all_ev)

        # Clean up
        case_svc.delete_case_evidence(db, "u_priya", "case_demo", ev["id"])
    finally:
        db.close()


def test_phase3_tasks_lifecycle():
    """Verify task creation with category/priority and completion timestamp recording."""
    db = SessionLocal()
    try:
        task = case_svc.create_task(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            title="Obtain Certified Copy of Station GD Entry",
            description="Visit HSR Layout station and collect certified GD extract for insurance claim",
            priority="high",
            category="police",
            due_at=(datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            due_source="Police Documentation Norms",
        )
        assert task["task_id"] is not None
        assert task["title"] == "Obtain Certified Copy of Station GD Entry"
        assert task["category"] == "police"
        assert task["status"] == "open"

        # Update status to completed
        updated = case_svc.set_task_status(db, "u_priya", "case_demo", task["task_id"], "completed")
        assert updated["status"] == "completed"
        assert updated["completed_at"] is not None

        # Verify timeline event recorded
        events = case_svc.timeline(db, "u_priya", "case_demo")
        assert any(e["kind"] == "task_status" for e in events)

        # Clean up task
        t_rec = db.get(Task, task["task_id"])
        if t_rec:
            db.delete(t_rec)
            db.commit()
    finally:
        db.close()


def test_phase3_status_transitions_append_only_history():
    """Verify state transitions preserve complete append-only audit trail."""
    db = SessionLocal()
    try:
        # Status change: active -> under_review
        t1 = case_svc.update_case_status(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            new_status="under_review",
            reason="Insurance surveyor reviewing vehicle damage",
            trigger="surveyor_appointment",
        )
        assert t1["status"] == "under_review"
        assert t1["previous_status"] == "active"

        # Status change: under_review -> active
        t2 = case_svc.update_case_status(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            new_status="active",
            reason="Survey completed, continuing hospital follow-up",
            trigger="manual_user_action",
        )
        assert t2["status"] == "active"
        assert t2["previous_status"] == "under_review"

        # Verify append-only transitions list contains both
        history = case_svc.list_case_status_transitions(db, "u_priya", "case_demo")
        assert len(history) >= 2
        triggers = [h["transition_trigger"] for h in history]
        assert "surveyor_appointment" in triggers
        assert "manual_user_action" in triggers
    finally:
        db.close()


def test_phase3_authorization_isolation_and_member_permissions():
    """Verify unauthorized outsider cannot view case and member least-privilege defaults hold."""
    db = SessionLocal()
    try:
        # Outsider cannot view workspace
        with pytest.raises(PermissionDenied):
            case_svc.get_case_workspace(db, actor_id="u_outsider", case_id="case_demo")

        # Outsider cannot upload evidence
        with pytest.raises(PermissionDenied):
            case_svc.upload_case_evidence(
                db=db,
                actor_id="u_outsider",
                case_id="case_demo",
                title="Malicious injection attempt",
                file_name="exploit.jpg",
                content=b"test",
                mime_type="image/jpeg",
            )

        # Check Arjun's member permissions: by default can_view_medical is False
        arjun_member = db.get(CaseMember, ("case_demo", "u_arjun"))
        assert arjun_member is not None
        assert arjun_member.can_view_case is True
        assert arjun_member.can_view_medical is False

        # Coordinator (Priya) can update member permissions
        updated_arjun = case_svc.update_case_member_permissions(
            db=db,
            actor_id="u_priya",
            case_id="case_demo",
            member_id="u_arjun",
            permissions={"can_view_documents": True, "can_manage_tasks": True},
        )
        assert updated_arjun["can_view_documents"] is True

        # Non-coordinator (Arjun) cannot update member permissions
        with pytest.raises(PermissionDenied):
            case_svc.update_case_member_permissions(
                db=db,
                actor_id="u_arjun",
                case_id="case_demo",
                member_id="u_priya",
                permissions={"role": "viewer"},
            )
    finally:
        db.close()
