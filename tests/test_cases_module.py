"""Tests for Second Hour Case Management Module."""
import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.db import Case, SessionLocal
from scripts.seed import seed


@pytest.fixture(autouse=True)
def _reseed():
    seed()


client = TestClient(app)


def test_cases_overview_summary_and_cards():
    resp = client.get("/api/cases/overview", headers={"X-User-Id": "u_priya"})
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "cases" in data

    summary = data["summary"]
    assert summary["total_cases"] >= 1
    assert summary["active_cases"] >= 1
    assert summary["pending_actions"] >= 1

    case = data["cases"][0]
    assert case["case_id"] == "case_demo"
    assert case["case_number"] == "SH-2026-0001"
    assert case["victim_display_name"] == "Ravi Kumar"
    assert case["hospital_name"] == "Sample City Hospital"
    assert case["injury_severity"] == "Moderate"
    assert case["vehicle"] is not None
    assert case["vehicle"]["registration_number"] == "KA-01-MJ-2024"
    assert case["vehicle"]["manufacturer"] == "Honda"
    assert case["vehicle"]["model"] == "City"
    assert case["pending_actions_count"] >= 1


def test_cases_overview_search_and_filters():
    # Search by registration number
    resp = client.get("/api/cases/overview?search=KA-01-MJ-2024", headers={"X-User-Id": "u_priya"})
    assert resp.status_code == 200
    assert len(resp.json()["cases"]) == 1

    # Search by non-existent term
    resp = client.get("/api/cases/overview?search=NONEXISTENT_XYZ", headers={"X-User-Id": "u_priya"})
    assert resp.status_code == 200
    assert len(resp.json()["cases"]) == 0

    # Filter by status active
    resp = client.get("/api/cases/overview?status=active", headers={"X-User-Id": "u_priya"})
    assert resp.status_code == 200
    assert len(resp.json()["cases"]) >= 1

    # Filter by resolved status (none currently)
    resp = client.get("/api/cases/overview?status=resolved", headers={"X-User-Id": "u_priya"})
    assert resp.status_code == 200
    assert len(resp.json()["cases"]) == 0


def test_case_workspace_complete_details():
    resp = client.get("/api/cases/case_demo/workspace", headers={"X-User-Id": "u_priya"})
    assert resp.status_code == 200
    ws = resp.json()

    # Case details
    c = ws["case"]
    assert c["case_number"] == "SH-2026-0001"
    assert c["approximate_location"] == "Outer Ring Road near Agara Flyover, Bengaluru"
    assert c["latitude"] == 12.9279
    assert c["longitude"] == 77.6271
    assert c["accident_type"] == "Two-Vehicle Collision"
    assert c["victim_display_name"] == "Ravi Kumar"
    assert c["injury_severity"] == "Moderate"

    # Linked vehicle
    v = ws["vehicle"]
    assert v is not None
    assert v["registration_number"] == "KA-01-MJ-2024"
    assert v["manufacturer"] == "Honda"
    assert v["model"] == "City"
    assert v["insurance_policy_number"] == "POL-99283401-2026"

    # Independent progress indicators (Hospital, Police, PM-RAHAT, Insurance)
    prog = ws["progress_indicators"]
    assert "hospital" in prog
    assert "police" in prog
    assert "pmrahat" in prog
    assert "insurance" in prog
    assert prog["hospital"]["stage"] == "Admitted - General Ward"
    assert prog["pmrahat"]["stage"] == "Eligible - Cashless Active"

    # Hospital & PM-RAHAT
    hp = ws["hospital_pmrahat"]
    assert hp["hospital"]["name"] == "Sample City Hospital"
    assert hp["pmrahat"]["cover_limit_inr"] == 150000
    assert len(hp["pmrahat"]["eligibility_checklist"]) == 4

    # Police & Insurance
    pol = ws["police_info"]
    assert pol["police_station"] == "HSR Layout Traffic Police Station"
    assert pol["fir_number"] == "FIR-2026/0491-TR"
    assert "STATEMENT OF INCIDENT" in pol["draft_report"]
    assert pol["draft_status"] == "draft_pending_review"

    ins = ws["insurance_info"]
    assert ins["provider"] == "Tata AIG General Insurance"
    assert ins["policy_number"] == "POL-99283401-2026"
    assert ins["surveyor_name"] == "Anand Verma (IRDA/SUR/9182)"

    # Evidence & documents
    ev = ws["evidence"]
    assert len(ev["all"]) >= 2
    assert len(ev["supporting_docs"]) >= 1

    # Family members
    members = ws["family_members"]
    assert len(members) >= 2
    priya = next(m for m in members if m["name"] == "Priya")
    assert priya["role"] == "coordinator"
    assert priya["relationship"] == "Spouse"

    # Tasks & timeline
    assert len(ws["tasks"]) >= 3
    assert len(ws["timeline"]) >= 4


def test_police_draft_explicit_user_approval_workflow():
    # 1. Initially draft is pending review
    resp = client.get("/api/cases/case_demo/workspace", headers={"X-User-Id": "u_priya"})
    assert resp.json()["police_info"]["draft_status"] == "draft_pending_review"

    # 2. User explicitly reviews and approves
    approve_resp = client.post(
        "/api/cases/case_demo/police/approve",
        headers={"X-User-Id": "u_priya"},
        json={"approved": True, "feedback": "Reviewed and verified."},
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "approved_by_user"
    assert approved_data["approved_by"] == "Priya"
    assert approved_data["approved_at"] is not None

    # 3. Workspace reflects the user-approved state
    resp2 = client.get("/api/cases/case_demo/workspace", headers={"X-User-Id": "u_priya"})
    ws2 = resp2.json()
    assert ws2["police_info"]["draft_status"] == "approved_by_user"
    assert ws2["police_info"]["approved_by"] == "Priya"
    assert ws2["progress_indicators"]["police"]["stage"] == "Draft Approved by Family"


def test_section_updates_and_tasks():
    # Update hospital section
    patch_resp = client.patch(
        "/api/cases/case_demo/section",
        headers={"X-User-Id": "u_priya"},
        json={
            "section": "hospital",
            "data": {
                "hospital_name": "Sample City Hospital - Special Trauma Wing",
                "treating_doctor": "Dr. R Nair (Senior Ortho)",
                "hospital_treatment_status": "Under Observation",
            },
        },
    )
    assert patch_resp.status_code == 200
    updated_ws = patch_resp.json()
    assert updated_ws["hospital_pmrahat"]["hospital"]["name"] == "Sample City Hospital - Special Trauma Wing"
    assert updated_ws["hospital_pmrahat"]["hospital"]["treating_doctor"] == "Dr. R Nair (Senior Ortho)"

    # Toggle task status
    task_id = updated_ws["tasks"][0]["task_id"]
    initial_status = updated_ws["tasks"][0]["status"]
    toggle_resp = client.post(
        f"/api/cases/case_demo/tasks/{task_id}/toggle",
        headers={"X-User-Id": "u_priya"},
    )
    assert toggle_resp.status_code == 200
    new_status = toggle_resp.json()["status"]
    assert new_status != initial_status

    # Add a new task
    create_task_resp = client.post(
        "/api/cases/case_demo/tasks/create",
        headers={"X-User-Id": "u_priya"},
        json={
            "title": "Pick up prescribed orthopaedic medicines",
            "description": "Prescription from Dr. R Nair",
            "priority": "high",
            "due_at": "2026-11-28T10:00:00Z",
            "due_source": "Hospital Doctor Discharge Plan",
        },
    )
    assert create_task_resp.status_code == 200
    created_task = create_task_resp.json()
    assert created_task["title"] == "Pick up prescribed orthopaedic medicines"
    assert created_task["priority"] == "high"


def test_outsider_access_denied():
    # u_outsider is not a member of case_demo
    resp = client.get("/api/cases/case_demo/workspace", headers={"X-User-Id": "u_outsider"})
    assert resp.status_code == 403

    # Attempt to approve police draft blocked
    resp_approve = client.post(
        "/api/cases/case_demo/police/approve",
        headers={"X-User-Id": "u_outsider"},
        json={"approved": True},
    )
    assert resp_approve.status_code == 403
