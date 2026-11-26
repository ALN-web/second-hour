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
    CentralDocument,
    EmergencyContact,
    EmergencyContactPermission,
    MedicalInformation,
    SessionLocal,
    Task,
    TimelineEvent,
    User,
    UserAddress,
    UserNotificationPreference,
    UserPrivacyPreference,
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
    _pdf(config.VEHICLE_DOCS_DIR / "PUC_Expired_2025.pdf", "Pollution Under Control Certificate (Expired)", [
        "Department of Transport – Government of Karnataka",
        "Authorised Emission Testing Centre #KA01-084",
        "Certificate No: KA01003819271",
        "Vehicle Registration: KA-01-MJ-2024",
        "Date of Testing: 16-04-2024",
        "Valid Upto: 15-04-2025",
        "Emission Norms: Bharat Stage VI",
        "STATUS: EXPIRED / HISTORICAL RECORD",
    ])

    # Generate personal documents for Priya
    priya_docs_dir = config.CENTRAL_DOCS_DIR / "u_priya"
    priya_docs_dir.mkdir(parents=True, exist_ok=True)
    _pdf(priya_docs_dir / "Driving_Licence_KA05.pdf", "Indian Union Driving Licence", [
        "Government of Karnataka – Transport Department",
        "Licencing Authority: RTO Bengaluru South (KA-05)",
        "Licence No: KA05-2020-0081928",
        "Name: Priya Sharma",
        "Son/Daughter/Wife of: Rajesh Sharma",
        "Date of Birth: 14-08-1994",
        "Blood Group: B+ Positive",
        "Vehicles Authorised to Drive: LMV (Motor Car), MCWG (Motor Cycle with Gear)",
        "Date of Issue: 20-05-2020",
        "Validity (Non-Transport): 19-05-2038",
        "Organ Donor Pledge: YES",
    ])
    _pdf(priya_docs_dir / "PAN_Card_ABCPS1234F.pdf", "Permanent Account Number Card", [
        "Income Tax Department – Government of India",
        "Permanent Account Number: ABCPS1234F",
        "Name: Priya Sharma",
        "Father's Name: Rajesh Sharma",
        "Date of Birth: 14-08-1994",
        "QR Code Verified · Electronic Permanent Account Number",
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
    u_priya = User(
        id="u_priya",
        name="Priya",
        role_label="Family coordinator",
        email="priya.sharma@example.com",
        email_verified=True,
        phone="+91 98450 88291",
        phone_verified=True,
        date_of_birth="1992-06-14",
        gender="female",
        preferred_language="English",
        account_status="Active",
    )
    u_arjun = User(
        id="u_arjun",
        name="Arjun Sharma",
        role_label="Brother",
        email="arjun.sharma@example.com",
        email_verified=True,
        phone="+91 98450 12345",
        phone_verified=True,
        preferred_language="English",
        account_status="Active",
    )
    u_outsider = User(
        id="u_outsider",
        name="Outsider (demo)",
        role_label="Not a case member",
        email="outsider@example.com",
        email_verified=False,
        phone="+91 99999 00000",
        phone_verified=False,
    )
    db.add_all([u_priya, u_arjun, u_outsider])
    db.flush()

    # Seed Emergency Contacts for Priya
    ec1 = EmergencyContact(
        id="ec_arjun",
        user_id="u_priya",
        full_name="Arjun Sharma",
        relationship="Sibling",
        mobile_number="+91 98450 12345",
        alternate_number="+91 80 2521 9988",
        email="arjun.sharma@example.com",
        priority=1,
        is_primary=True,
        preferred_contact_method="phone",
    )
    ec2 = EmergencyContact(
        id="ec_ramesh",
        user_id="u_priya",
        full_name="Dr. Ramesh Sharma",
        relationship="Parent",
        mobile_number="+91 98450 54321",
        email="dr.ramesh@example.com",
        priority=2,
        is_primary=False,
        preferred_contact_method="phone",
    )
    db.add_all([ec1, ec2])
    db.flush()

    # Seed Permissions for Emergency Contacts
    perm1 = EmergencyContactPermission(
        id="ecp_arjun",
        contact_id=ec1.id,
        can_notify_accident=True,
        can_receive_case_updates=True,
        can_access_case=True,
        permitted_case_ids='["case_demo"]',
        can_view_limited_case_info=True,
        can_view_medical=False,
        can_view_documents=True,
    )
    perm2 = EmergencyContactPermission(
        id="ecp_ramesh",
        contact_id=ec2.id,
        can_notify_accident=True,
        can_receive_case_updates=False,
        can_access_case=False,
        permitted_case_ids="[]",
        can_view_limited_case_info=True,
        can_view_medical=False,
        can_view_documents=False,
    )
    db.add_all([perm1, perm2])

    # Seed Medical Information for Priya (Optional, restricted)
    med = MedicalInformation(
        id="med_priya",
        user_id="u_priya",
        blood_group="O+",
        allergies="Penicillin (Mild urticaria / hives)",
        medical_conditions="None recorded",
        medications="None ongoing",
        emergency_notes="Primary emergency contact is brother Arjun Sharma (+91 98450 12345)",
        share_with_ems=True,
        share_with_ai=False,
    )
    db.add(med)

    # Seed Address for Priya
    addr_curr = UserAddress(
        id="addr_priya_curr",
        user_id="u_priya",
        address_type="current",
        address_line_1="#402, Green Glen Layout",
        address_line_2="Near Bellandur Lake Road, Outer Ring Road",
        city="Bengaluru",
        state="Karnataka",
        pin_code="560103",
        country="India",
        is_same_as_current=False,
    )
    addr_perm = UserAddress(
        id="addr_priya_perm",
        user_id="u_priya",
        address_type="permanent",
        address_line_1="#402, Green Glen Layout",
        address_line_2="Near Bellandur Lake Road, Outer Ring Road",
        city="Bengaluru",
        state="Karnataka",
        pin_code="560103",
        country="India",
        is_same_as_current=True,
    )
    db.add_all([addr_curr, addr_perm])

    # Seed Privacy Preferences for Priya
    priv = UserPrivacyPreference(
        id="priv_priya",
        user_id="u_priya",
        ai_data_access_enabled=True,
        ai_include_medical=False,
        ai_include_documents=True,
        ai_include_vehicles=True,
        ai_include_cases=True,
        allow_emergency_broadcast=True,
    )
    db.add(priv)

    # Seed Notification Preferences for Priya
    notif = UserNotificationPreference(
        id="notif_priya",
        user_id="u_priya",
        email_notifications=True,
        sms_notifications=True,
        in_app_notifications=True,
        whatsapp_notifications=False,
        accident_alerts=True,
        case_updates=True,
        document_expiry_reminders=True,
        insurance_renewal_reminders=True,
        pending_task_reminders=True,
    )
    db.add(notif)
    db.flush()
    case = Case(
        id="case_demo",
        case_number="SH-2026-0001",
        status="active",
        incident_at=incident_utc,
        approximate_location="Outer Ring Road near Agara Flyover, Bengaluru",
        latitude=12.9279,
        longitude=77.6271,
        location_landmark="Agara Lake junction towards HSR Layout",
        accident_description="Two-vehicle lateral impact collision on the outer lane. Front left bumper and wheel arch impacted by an overtaking commercial truck during moderate traffic.",
        accident_type="Two-Vehicle Collision",
        weather_conditions="Clear & Dry (Night)",
        vehicles_involved="2 Vehicles (Honda City & Commercial Lorry)",
        people_affected="1 Person Injured (Driver - Ravi Kumar)",
        victim_display_name="Ravi Kumar",
        victim_relationship="Spouse",
        victim_phone="+91 98450 88291",
        injury_severity="Moderate",
        injury_description="Closed fracture of left radius; superficial forehead contusion. Vitals stable after emergency stabilization.",
        damage_severity="Moderate Frontal Damage",
        damage_description="Front bumper dislodged, left headlamp unit broken, left front fender dented, steering pull observed.",
        vehicle_id="veh_demo_honda",
        hospital_name="Sample City Hospital",
        hospital_address="Outer Ring Road Medical Hub, Bellandur, Bengaluru 560103",
        hospital_contact="+91 80 4920 1100",
        treating_doctor="Dr. A Sample (Trauma & Orthopaedic Lead)",
        admission_at=incident_utc + timedelta(minutes=45),
        hospital_treatment_status="Admitted - General Ward",
        life_threatening=False,
        pmrahat_status="eligible_active",
        pmrahat_reference="PMR-KA-2026-0001",
        pmrahat_stage="Eligible - Cashless Active",
        police_auth_status="requested_by_hospital",
        police_auth_updated_at=incident_utc + timedelta(hours=2),
        police_station="HSR Layout Traffic Police Station",
        police_station_address="19th Main Road, Sector 1, HSR Layout, Bengaluru 560102",
        investigating_officer="Sub-Inspector Ramesh K",
        officer_contact="+91 80 2294 2568",
        fir_number="FIR-2026/0491-TR",
        fir_date=incident_utc + timedelta(hours=4),
        fir_sections="IPC Section 279 (Rash Driving), Section 337 (Causing Hurt)",
        police_stage="Draft Prepared",
        police_draft_status="draft_pending_review",
        police_draft_approved_by=None,
        police_draft_approved_at=None,
        insurance_provider="Tata AIG General Insurance",
        insurance_policy_number="POL-99283401-2026",
        insurance_claim_number="CLM-AIG-0001-2026",
        insurance_stage="Claim Intimated",
        insurance_surveyor_name="Anand Verma (IRDA/SUR/9182)",
        insurance_surveyor_phone="+91 98450 19284",
        insurance_settlement_status="In Progress - Cashless Assessment at Network Garage",
        created_by="u_priya",
    )
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

    # Seed Central Documents (single source of truth across Personal, Vehicle and Case views)
    cdoc_dl = CentralDocument(
        id="cdoc_demo_dl",
        user_id="u_priya",
        document_name="Driving Licence — Karnataka State",
        document_type="driving_licence",
        category="driving_licence",
        file_name="Driving_Licence_KA05.pdf",
        stored_path=str(config.CENTRAL_DOCS_DIR / "u_priya" / "Driving_Licence_KA05.pdf"),
        mime_type="application/pdf",
        file_size=16200,
        document_number="KA05-2020-0081928",
        issuing_authority="RTO Bengaluru South (KA-05)",
        issue_date=incident_utc - timedelta(days=365 * 6),
        expiry_date=incident_utc + timedelta(days=365 * 12),
        verification_status="verified",
        notes="Class: LMV + MCWG. Organ Donor: Yes",
        resource_type="USER",
        resource_id="u_priya",
    )
    cdoc_pan = CentralDocument(
        id="cdoc_demo_pan",
        user_id="u_priya",
        document_name="PAN Card — Income Tax Dept",
        document_type="pan",
        category="personal",
        file_name="PAN_Card_ABCPS1234F.pdf",
        stored_path=str(config.CENTRAL_DOCS_DIR / "u_priya" / "PAN_Card_ABCPS1234F.pdf"),
        mime_type="application/pdf",
        file_size=15100,
        document_number="ABCPS1234F",
        issuing_authority="Income Tax Department",
        issue_date=incident_utc - timedelta(days=365 * 8),
        expiry_date=None,
        verification_status="verified",
        notes="Primary tax identity proof",
        resource_type="USER",
        resource_id="u_priya",
    )
    cdoc_rc = CentralDocument(
        id="vdoc_demo_rc",
        user_id="u_priya",
        document_name="Registration Certificate (RC)",
        document_type="rc",
        category="vehicle",
        file_name="RC_KA01MJ2024.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "RC_KA01MJ2024.pdf"),
        mime_type="application/pdf",
        file_size=14200,
        document_number="KA-01-MJ-2024",
        issuing_authority="RTO Bengaluru Central (KA-01)",
        issue_date=incident_utc - timedelta(days=365 * 2),
        expiry_date=incident_utc + timedelta(days=365 * 13),
        verification_status="verified",
        notes="Honda City ZX CVT. Bharat Stage VI",
        resource_type="VEHICLE",
        resource_id="veh_demo_honda",
    )
    cdoc_ins = CentralDocument(
        id="vdoc_demo_ins",
        user_id="u_priya",
        document_name="Tata AIG Comprehensive Policy",
        document_type="insurance",
        category="insurance",
        file_name="Policy_POL99283401.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "Policy_POL99283401.pdf"),
        mime_type="application/pdf",
        file_size=18400,
        document_number="POL-99283401-2026",
        issuing_authority="Tata AIG General Insurance Co Ltd",
        issue_date=policy_start,
        expiry_date=policy_expiry,
        verification_status="expiring_soon",
        notes="IDV: ₹14,20,000. Cashless network valid nationwide",
        resource_type="VEHICLE",
        resource_id="veh_demo_honda",
    )
    cdoc_puc = CentralDocument(
        id="vdoc_demo_puc",
        user_id="u_priya",
        document_name="Pollution Under Control Certificate",
        document_type="puc",
        category="vehicle",
        file_name="PUC_Valid_2026.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "PUC_Valid_2026.pdf"),
        mime_type="application/pdf",
        file_size=12100,
        document_number="KA01004928172",
        issuing_authority="Authorised Emission Testing Centre #KA01-084",
        issue_date=incident_utc - timedelta(days=337),
        expiry_date=policy_expiry,
        verification_status="expiring_soon",
        notes="BS-VI emission standards compliant",
        resource_type="VEHICLE",
        resource_id="veh_demo_honda",
    )
    cdoc_puc_exp = CentralDocument(
        id="cdoc_demo_puc_exp",
        user_id="u_priya",
        document_name="PUC Certificate (Previous Year)",
        document_type="puc",
        category="vehicle",
        file_name="PUC_Expired_2025.pdf",
        stored_path=str(config.VEHICLE_DOCS_DIR / "PUC_Expired_2025.pdf"),
        mime_type="application/pdf",
        file_size=11900,
        document_number="KA01003819271",
        issuing_authority="Authorised Emission Testing Centre #KA01-084",
        issue_date=incident_utc - timedelta(days=700),
        expiry_date=incident_utc - timedelta(days=120),
        verification_status="expired",
        notes="Historical record - renewed with 2026 certificate",
        resource_type="VEHICLE",
        resource_id="veh_demo_honda",
    )
    cdoc_bill = CentralDocument(
        id="cdoc_demo_bill",
        user_id="u_priya",
        document_name="Sample City Hospital Emergency Bill",
        document_type="hospital_bill",
        category="medical",
        file_name="sample_hospital_bill.pdf",
        stored_path=str(config.DEMO_ASSETS_DIR / "sample_hospital_bill.pdf"),
        mime_type="application/pdf",
        file_size=14600,
        document_number="BILL-2026-9901",
        issuing_authority="Sample City Hospital Billing Desk",
        issue_date=incident_utc,
        expiry_date=None,
        verification_status="verified",
        notes="PM-RAHAT cashless package intake bill",
        resource_type="ACCIDENT_CASE",
        resource_id="case_demo",
    )
    cdoc_med = CentralDocument(
        id="cdoc_demo_med",
        user_id="u_priya",
        document_name="Initial Medical Admission & Clinical Report",
        document_type="medical_report",
        category="medical",
        file_name="sample_medical_report.pdf",
        stored_path=str(config.DEMO_ASSETS_DIR / "sample_medical_report.pdf"),
        mime_type="application/pdf",
        file_size=15800,
        document_number="MED-2026-0812",
        issuing_authority="Sample City Hospital Trauma Centre",
        issue_date=incident_utc,
        expiry_date=None,
        verification_status="verified",
        notes="Trauma team admission assessment, fracture fixation note",
        resource_type="ACCIDENT_CASE",
        resource_id="case_demo",
    )
    db.add_all([cdoc_dl, cdoc_pan, cdoc_rc, cdoc_ins, cdoc_puc, cdoc_puc_exp, cdoc_bill, cdoc_med])

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
    db.add_all([
        CaseMember(
            case_id=case.id,
            user_id="u_priya",
            role="coordinator",
            relationship="Spouse",
            contact_number="+91 98450 12345",
            permissions_summary="Full Case Access, Financial Approvals",
        ),
        CaseMember(
            case_id=case.id,
            user_id="u_arjun",
            role="member",
            relationship="Brother",
            contact_number="+91 98450 67890",
            permissions_summary="View Case, Coordinate Tasks & Garage",
        ),
        # Seed case tasks
        Task(
            case_id=case.id,
            title="Confirm PM-RAHAT cashless package at hospital billing desk",
            description="Hospital billing desk confirmed initial stabilization cover up to ₹1.5 lakh under PM-RAHAT.",
            priority="high",
            status="open",
            due_at=incident_utc + timedelta(days=2),
            due_source="PM-RAHAT 7-Day Protocol",
            assignee_id="u_priya",
            created_by="u_priya",
        ),
        Task(
            case_id=case.id,
            title="Review and approve AI draft police intimation statement",
            description="Carefully review the statement prepared from vehicle and incident details before approving intimation.",
            priority="high",
            status="open",
            due_at=incident_utc + timedelta(days=1),
            due_source="Police Documentation Requirement",
            assignee_id="u_priya",
            created_by="u_priya",
        ),
        Task(
            case_id=case.id,
            title="Coordinate vehicle inspection with Tata AIG surveyor Anand Verma",
            description="Surveyor scheduled to inspect Honda City at authorized service workshop in Koramangala.",
            priority="medium",
            status="open",
            due_at=incident_utc + timedelta(days=3),
            due_source="Insurer Surveyor Appointment",
            assignee_id="u_arjun",
            created_by="u_priya",
        ),
        Task(
            case_id=case.id,
            title="Submit driving licence and vehicle RC copies to claims desk",
            description="Documents sourced directly from Second Hour Document Wallet.",
            priority="low",
            status="done",
            due_at=incident_utc + timedelta(days=1),
            due_source="Claim Intake Desk",
            assignee_id="u_priya",
            created_by="u_priya",
        ),
        # Seed chronological timeline events
        TimelineEvent(
            case_id=case.id,
            actor_id="u_priya",
            kind="incident_occurred",
            summary="Accident occurred on Outer Ring Road, Bengaluru. Emergency intimation logged.",
            at=incident_utc,
        ),
        TimelineEvent(
            case_id=case.id,
            actor_id="u_priya",
            kind="hospital_admission",
            summary="Ravi Kumar admitted to Sample City Hospital Trauma Unit. Stabilisation started.",
            at=incident_utc + timedelta(minutes=45),
        ),
        TimelineEvent(
            case_id=case.id,
            actor_id="u_priya",
            kind="pmrahat_activated",
            summary="PM-RAHAT cashless protocol activated (₹1,50,000 stabilization cover).",
            at=incident_utc + timedelta(hours=1, minutes=15),
        ),
        TimelineEvent(
            case_id=case.id,
            actor_id="u_priya",
            kind="case_created",
            summary="Accident Case SH-2026-0001 workspace created on Second Hour.",
            at=incident_utc + timedelta(hours=2),
        ),
        TimelineEvent(
            case_id=case.id,
            actor_id="u_priya",
            kind="insurance_claim_intimated",
            summary="Motor claim CLM-AIG-0001-2026 intimated with Tata AIG General Insurance.",
            at=incident_utc + timedelta(hours=3),
        ),
        TimelineEvent(
            case_id=case.id,
            actor_id=None,
            kind="police_draft_prepared",
            summary="AI Case Assistant prepared draft statement of incident for HSR Layout Traffic Police Station.",
            at=incident_utc + timedelta(hours=5),
        ),
    ])
    db.commit()
    db.close()
    make_demo_assets(incident_ist)
    return {"case_id": "case_demo", "incident_at_utc": incident_utc.isoformat()}


if __name__ == "__main__":
    out = seed()
    print("Seeded:", out)
    print("Demo assets:", config.DEMO_ASSETS_DIR)
