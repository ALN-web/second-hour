"""Reset the DB and seed demo users, one simulated case, and two SYNTHETIC sample PDFs.

Run:  python -m scripts.seed
All names and data are fictional. SAMPLE – SYNTHETIC DATA.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from app import config  # noqa: E402
from app.db import Base, Case, CaseMember, SessionLocal, TimelineEvent, User, engine  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
WATERMARK = "SAMPLE – SYNTHETIC DATA"


def _pdf(path: Path, title: str, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.8, 0.1, 0.1)
    c.drawString(20 * mm, h - 15 * mm, WATERMARK + " – fictional names, not a real document")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, h - 30 * mm, title)
    c.setFont("Helvetica", 11)
    y = h - 45 * mm
    for line in lines:
        c.drawString(20 * mm, y, line)
        y -= 7 * mm
    c.saveState()
    c.setFont("Helvetica-Bold", 40)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.translate(w / 2, h / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "SAMPLE – SYNTHETIC")
    c.restoreState()
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(20 * mm, 15 * mm, WATERMARK)
    c.save()


def make_demo_assets(incident_ist: datetime) -> None:
    config.DEMO_ASSETS_DIR.mkdir(exist_ok=True)
    d = incident_ist.strftime("%d-%m-%Y")
    _pdf(config.DEMO_ASSETS_DIR / "sample_hospital_bill.pdf", "Sample City Hospital – Interim Bill", [
        "Hospital Name: Sample City Hospital, Bengaluru",
        "Bill No: SCH-2026-00417",
        "Patient Name: Ravi K",
        f"Admission Date: {d}",
        "",
        "Room charges (2 days) ........................ Rs. 18,000",
        "Emergency & stabilisation .................... Rs. 22,000",
        "Orthopaedic procedure (left forearm) ......... Rs. 61,000",
        "Medicines & consumables ...................... Rs. 14,500",
        "Investigations (X-ray, CT) ................... Rs. 8,500",
        "",
        "Grand Total: Rs. 1,24,000",
        "",
        "Billing desk: Sample City Hospital (fictional)",
    ])
    _pdf(config.DEMO_ASSETS_DIR / "sample_medical_report.pdf", "Sample City Hospital – Medical Report", [
        "Hospital Name: Sample City Hospital, Bengaluru",
        "Patient Name: Ravi K",
        f"Admission Date: {d}",
        "Treating Doctor: Dr. A Sample",
        "Diagnosis: Closed fracture of left radius; minor head abrasion",
        "Clinical findings: Conscious, oriented. Vitals stable after stabilisation.",
        "Plan: Orthopaedic fixation, observation for 48 hours.",
        "",
        "This medical report is synthetic sample data for a hackathon demo.",
    ])


def seed() -> dict:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    if config.UPLOAD_DIR.exists():
        shutil.rmtree(config.UPLOAD_DIR)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    now_ist = datetime.now(IST)
    incident_ist = (now_ist - timedelta(days=1)).replace(hour=21, minute=30, second=0, microsecond=0)
    incident_utc = incident_ist.astimezone(timezone.utc).replace(tzinfo=None)

    db = SessionLocal()
    db.add_all([User(id="u_priya", name="Priya", role_label="Family coordinator"),
                User(id="u_arjun", name="Arjun", role_label="Brother"),
                User(id="u_outsider", name="Outsider (demo)", role_label="Not a case member")])
    db.flush()
    case = Case(id="case_demo", case_number="SH-2026-0001", incident_at=incident_utc,
                approximate_location="Outer Ring Road, Bengaluru", victim_display_name="Ravi K",
                hospital_name="Sample City Hospital", life_threatening=False, created_by="u_priya",
                police_auth_status="not_started")
    db.add(case)
    db.flush()
    db.add_all([CaseMember(case_id=case.id, user_id="u_priya", role="coordinator"),
                CaseMember(case_id=case.id, user_id="u_arjun", role="member"),
                TimelineEvent(case_id=case.id, actor_id="u_priya", kind="case_created",
                              summary="Case SH-2026-0001 created (simulated demo case)")])
    db.commit()
    db.close()
    make_demo_assets(incident_ist)
    return {"case_id": "case_demo", "incident_at_utc": incident_utc.isoformat()}


if __name__ == "__main__":
    out = seed()
    print("Seeded:", out)
    print("Demo assets:", config.DEMO_ASSETS_DIR)
