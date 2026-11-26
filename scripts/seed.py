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
from app.db import (  # noqa: E402
    Base,
    Case,
    CaseMember,
    SessionLocal,
    TimelineEvent,
    User,
    Vehicle,
    VehicleDocument,
    VehicleInsurancePolicy,
    VehiclePhoto,
    engine,
)

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

    # Generate vehicle documents
    config.VEHICLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    _pdf(config.VEHICLE_DOCS_DIR / "RC_KA01MJ2024.pdf", "Form 23 – Certificate of Registration", [
        "Government of Karnataka – Motor Vehicles Department",
        "Registration Authority: RTO Bengaluru Central (KA-01)",
        "Registration Mark: KA-01-MJ-2024",
        "Owner Name: Priya Sharma",
        "Class of Vehicle: Motor Car (LMV)",
        "Maker: Honda Cars India Ltd",
        "Maker's Classification: City ZX CVT (Petrol)",
        "Chassis No: MAKGM2657HM019284",
        "Engine No: L15Z19827364",
        "Fuel: Petrol / Bharat Stage VI",
        "Seating Capacity: 5 in all",
        "Unladen Weight: 1153 kg",
        "Registration Date: 16-04-2024",
        "Fitness Valid Upto: 15-04-2039",
    ])
    _pdf(config.VEHICLE_DOCS_DIR / "Policy_POL99283401.pdf", "Tata AIG Private Car Package Policy", [
        "Tata AIG General Insurance Company Limited",
        "Certificate of Insurance cum Policy Schedule",
        "Policy Number: POL-99283401-2026",
        "Insured Name: Priya Sharma",
        "Vehicle Reg No: KA-01-MJ-2024",
        "Make / Model: Honda City ZX (Petrol, 1498 cc)",
        "Insured Declared Value (IDV): Rs. 14,20,000",
        "Period of Insurance: 16-04-2025 to 15-04-2026",
        "Coverage: Comprehensive (OD + TP + Roadside Assist)",
        "Compulsory Personal Accident (Owner-Driver): Rs. 15,00,000",
        "Cashless Claims Assistance: 1800-266-7780",
    ])
    _pdf(config.VEHICLE_DOCS_DIR / "PUC_Valid_2026.pdf", "Pollution Under Control Certificate", [
        "Department of Transport – Government of Karnataka",
        "Authorised Emission Testing Centre #KA01-084",
        "Certificate No: KA01004928172",
        "Vehicle Registration: KA-01-MJ-2024",
        "Date of Testing: 16-04-2025",
        "Valid Upto: 15-04-2026",
        "Emission Norms: Bharat Stage VI",
        "Carbon Monoxide (CO): 0.12% (Limit: 0.50%) – PASS",
        "Hydrocarbon (HC): 82 ppm (Limit: 750 ppm) – PASS",
    ])

    # Generate clean demo vehicle image
    config.VEHICLE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    photo_path = config.VEHICLE_PHOTOS_DIR / "vpho_demo_1.jpg"
    if not photo_path.exists():
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (800, 500), color=(14, 30, 56))
        d_ctx = ImageDraw.Draw(img)
        # Background gradient blocks
        d_ctx.rectangle([0, 360, 800, 500], fill=(20, 42, 74))
        d_ctx.line([0, 360, 800, 360], fill=(249, 115, 22), width=3)
        # Stylized sedan car shape
        # Roof/cabin
        d_ctx.polygon([(260, 240), (340, 160), (520, 160), (620, 240)], fill=(240, 245, 250))
        d_ctx.polygon([(280, 235), (345, 175), (510, 175), (595, 235)], fill=(30, 58, 95))
        # Body
        d_ctx.rounded_rectangle([140, 235, 680, 350], radius=16, fill=(245, 248, 252), outline=(200, 215, 230), width=2)
        # Headlights & Taillights
        d_ctx.rectangle([145, 250, 175, 275], fill=(249, 115, 22))
        d_ctx.rectangle([645, 250, 675, 275], fill=(56, 189, 248))
        # Front/rear wheels
        d_ctx.ellipse([210, 310, 290, 390], fill=(15, 23, 42), outline=(148, 163, 184), width=6)
        d_ctx.ellipse([235, 335, 265, 365], fill=(203, 213, 225))
        d_ctx.ellipse([530, 310, 610, 390], fill=(15, 23, 42), outline=(148, 163, 184), width=6)
        d_ctx.ellipse([555, 335, 585, 365], fill=(203, 213, 225))
        # Text label banner
        d_ctx.rounded_rectangle([250, 410, 550, 455], radius=8, fill=(11, 26, 46), outline=(249, 115, 22), width=1)
        d_ctx.text((280, 425), "KA-01-MJ-2024  ·  Honda City ZX", fill=(255, 255, 255))
        img.save(str(photo_path), "JPEG", quality=90)


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
                hospital_name="Sample City Hospital", vehicle_id="veh_demo_honda", life_threatening=False, created_by="u_priya",
                police_auth_status="not_started")
    db.add(case)
    db.flush()

    # Seed demo vehicle for Priya
    veh = Vehicle(
        id="veh_demo_honda",
        user_id="u_priya",
        registration_number="KA-01-MJ-2024",
        category="Four Wheeler",
        manufacturer="Honda",
        model="City",
        variant="ZX CVT",
        manufacturing_year=2024,
        fuel_type="Petrol",
        color="Platinum White Pearl",
        chassis_number="MAKGM2657HM019284",
        engine_number="L15Z19827364",
        vin="MAKGM2657HM019284",
        engine_capacity="1498 cc",
        transmission="Automatic (CVT)",
        owner_name="Priya Sharma",
        ownership_type="Individual",
        relationship_to_user="Self",
        main_image="/api/vehicles/veh_demo_honda/photos/vpho_demo_1/file",
    )
    db.add(veh)
    db.flush()

    # Seed insurance policy expiring in 28 days
    policy_expiry = incident_utc + timedelta(days=28)
    policy_start = policy_expiry - timedelta(days=365)
    ins = VehicleInsurancePolicy(
        id="vpol_demo_1",
        vehicle_id="veh_demo_honda",
        provider="Tata AIG General Insurance",
        policy_number="POL-99283401-2026",
        policy_type="Comprehensive",
        start_date=policy_start,
        expiry_date=policy_expiry,
        document_id="vdoc_demo_ins",
    )
    db.add(ins)

    # Seed vehicle documents
    rc_doc = VehicleDocument(
        id="vdoc_demo_rc",
        vehicle_id="veh_demo_honda",
        document_type="rc",
        document_name="Registration Certificate (RC)",
        file_name="RC_KA01MJ2024.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "RC_KA01MJ2024.pdf"),
        mime_type="application/pdf",
        file_size=14200,
        expiry_date=incident_utc + timedelta(days=365 * 14),
        verification_status="verified",
    )
    ins_doc = VehicleDocument(
        id="vdoc_demo_ins",
        vehicle_id="veh_demo_honda",
        document_type="insurance",
        document_name="Tata AIG Comprehensive Policy",
        file_name="Policy_POL99283401.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "Policy_POL99283401.pdf"),
        mime_type="application/pdf",
        file_size=18400,
        expiry_date=policy_expiry,
        verification_status="expiring_soon",
    )
    puc_doc = VehicleDocument(
        id="vdoc_demo_puc",
        vehicle_id="veh_demo_honda",
        document_type="puc",
        document_name="Pollution Under Control Certificate",
        file_name="PUC_Valid_2026.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "PUC_Valid_2026.pdf"),
        mime_type="application/pdf",
        file_size=12100,
        expiry_date=policy_expiry,
        verification_status="verified",
    )
    db.add_all([rc_doc, ins_doc, puc_doc])

    # Seed vehicle photo
    photo = VehiclePhoto(
        id="vpho_demo_1",
        vehicle_id="veh_demo_honda",
        photo_category="main",
        file_name="honda_city_main.jpg",
        stored_path=str(config.VEHICLE_PHOTOS_DIR / "vpho_demo_1.jpg"),
        mime_type="image/jpeg",
        is_primary=True,
    )
    db.add(photo)
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
