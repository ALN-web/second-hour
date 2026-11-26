"""Tests for Second Hour vehicle management service and authorization."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.db import SessionLocal, User, Vehicle
from app.services import vehicles as veh_svc
from scripts.seed import seed

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    seed()


def test_list_vehicles_for_priya():
    res = client.get("/api/vehicles", headers={"X-User-Id": "u_priya"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    v = data[0]
    assert v["registration_number"] == "KA-01-MJ-2024"
    assert v["manufacturer"] == "Honda"
    assert v["model"] == "City"
    assert v["insurance"]["status"] in ("active", "expiring_soon")


def test_vehicle_ownership_enforcement():
    # Outsider cannot get Priya's vehicle
    res = client.get("/api/vehicles/veh_demo_honda", headers={"X-User-Id": "u_outsider"})
    assert res.status_code == 403


def test_create_and_update_vehicle():
    new_veh = {
        "registration_number": "KA-05-AB-1234",
        "category": "Two Wheeler",
        "manufacturer": "Ather",
        "model": "450X",
        "variant": "Gen 3",
        "manufacturing_year": 2023,
        "fuel_type": "Electric",
        "color": "Space Grey",
        "owner_name": "Priya Sharma",
        "ownership_type": "Individual",
        "insurance": {
            "provider": "Digit Insurance",
            "policy_number": "DIG-88992211",
            "policy_type": "Comprehensive",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        },
    }
    create_res = client.post("/api/vehicles", json=new_veh, headers={"X-User-Id": "u_priya"})
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["registration_number"] == "KA-05-AB-1234"
    assert created["insurance"]["provider"] == "Digit Insurance"
    assert created["insurance"]["status"] == "active"

    # Update color and variant
    update_res = client.put(
        f"/api/vehicles/{created['id']}",
        json={"color": "True Red", "variant": "Apex Edition"},
        headers={"X-User-Id": "u_priya"},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["color"] == "True Red"
    assert updated["variant"] == "Apex Edition"


def test_insurance_expiry_calculation():
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Active (> 30 days)
    status, days = veh_svc.calculate_insurance_status(now + timedelta(days=60))
    assert status == "active"
    assert days == 60

    # Expiring soon (<= 30 days)
    status, days = veh_svc.calculate_insurance_status(now + timedelta(days=15))
    assert status == "expiring_soon"
    assert days == 15

    # Expired
    status, days = veh_svc.calculate_insurance_status(now - timedelta(days=5))
    assert status == "expired"
    assert days == -5

    # Not provided
    status, days = veh_svc.calculate_insurance_status(None)
    assert status == "not_provided"
    assert days is None
