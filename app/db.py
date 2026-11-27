"""SQLAlchemy models and database connectivity layer (PostgreSQL / SQLite)."""
from __future__ import annotations

import json
import logging
import urllib.parse
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, create_engine, event, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship as orm_relationship, sessionmaker

from app.config import DATABASE_URL, DB_PATH

logger = logging.getLogger(__name__)


def _build_database_url() -> tuple[str, dict]:
    """Return database URL and engine connect args appropriate for target dialect."""
    raw_url = (DATABASE_URL or "").strip()
    if raw_url:
        # Normalize postgres:// to postgresql:// for SQLAlchemy 2.x
        if raw_url.startswith("postgres://"):
            raw_url = "postgresql://" + raw_url[len("postgres://"):]
        # Default to psycopg2 driver if not explicitly specified
        if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
            raw_url = "postgresql+psycopg2://" + raw_url[len("postgresql://"):]
        return raw_url, {}
    return f"sqlite:///{DB_PATH}", {"check_same_thread": False, "timeout": 30}


def create_app_engine():
    """Create and configure SQLAlchemy engine with connection pooling and serverless resilience."""
    url, connect_args = _build_database_url()
    if url.startswith("sqlite"):
        return create_engine(url, connect_args=connect_args)

    # Neon PostgreSQL serverless connection pooling & resilience:
    # - pool_pre_ping: tests connection before checkout, preventing stale socket errors on auto-resume
    # - pool_recycle: re-establishes connections older than 300s
    # - pool_size / max_overflow: handles concurrent requests within serverless connection budgets
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        connect_args={"connect_timeout": 15},
    )


engine = create_app_engine()


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    """Enforce WAL mode and foreign keys when using SQLite dialect."""
    if engine.dialect.name == "sqlite":
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Reusable transactional context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_connection() -> dict:
    """Test connection to the active database and return sanitized diagnostics without credentials."""
    url, _ = _build_database_url()
    is_postgres = not url.startswith("sqlite")
    masked_target = "sqlite local file"
    if is_postgres:
        parsed = urllib.parse.urlsplit(url)
        masked_target = f"PostgreSQL ({parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')})"

    try:
        with engine.connect() as conn:
            query_result = conn.execute(select(1)).scalar()
            db_version = "unknown"
            current_db = "unknown"
            if is_postgres:
                version_row = conn.execute(text("SELECT version(), current_database()")).first()
                if version_row:
                    db_version = version_row[0]
                    current_db = version_row[1]
            return {
                "ok": True,
                "is_postgres": is_postgres,
                "dialect": engine.dialect.name,
                "target": masked_target,
                "query_result": query_result,
                "db_version": db_version,
                "current_database": current_db,
            }
    except Exception as exc:
        return {
            "ok": False,
            "is_postgres": is_postgres,
            "dialect": engine.dialect.name,
            "target": masked_target,
            "error": str(exc),
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role_label: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    date_of_birth: Mapped[str | None] = mapped_column(String, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_photo: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String, default="English")
    account_status: Mapped[str] = mapped_column(String, default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("case"))
    case_number: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="active")  # active | under_review | resolved | closed
    incident_at: Mapped[datetime] = mapped_column(DateTime)
    approximate_location: Mapped[str] = mapped_column(String)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_landmark: Mapped[str | None] = mapped_column(String, nullable=True)
    accident_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    accident_type: Mapped[str | None] = mapped_column(String, default="Two-Vehicle Collision")
    weather_conditions: Mapped[str | None] = mapped_column(String, default="Clear & Dry")
    vehicles_involved: Mapped[str | None] = mapped_column(String, default="2 Vehicles")
    people_affected: Mapped[str | None] = mapped_column(String, default="1 Person Injured")
    victim_display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    victim_relationship: Mapped[str | None] = mapped_column(String, nullable=True)
    victim_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    injury_severity: Mapped[str | None] = mapped_column(String, default="Moderate")  # Minor | Moderate | Severe | Critical
    injury_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    damage_severity: Mapped[str | None] = mapped_column(String, default="Moderate Frontal Damage")
    damage_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String, nullable=True)
    hospital_address: Mapped[str | None] = mapped_column(String, nullable=True)
    hospital_contact: Mapped[str | None] = mapped_column(String, nullable=True)
    treating_doctor: Mapped[str | None] = mapped_column(String, nullable=True)
    admission_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hospital_treatment_status: Mapped[str] = mapped_column(String, default="Admitted - General Ward")
    life_threatening: Mapped[bool] = mapped_column(Boolean, default=False)
    pmrahat_status: Mapped[str] = mapped_column(String, default="eligible_active")
    pmrahat_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    pmrahat_stage: Mapped[str] = mapped_column(String, default="Eligible - Cashless Active")
    police_auth_status: Mapped[str] = mapped_column(String, default="not_started")
    police_auth_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    police_station: Mapped[str | None] = mapped_column(String, nullable=True)
    police_station_address: Mapped[str | None] = mapped_column(String, nullable=True)
    investigating_officer: Mapped[str | None] = mapped_column(String, nullable=True)
    officer_contact: Mapped[str | None] = mapped_column(String, nullable=True)
    fir_number: Mapped[str | None] = mapped_column(String, nullable=True)
    fir_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fir_sections: Mapped[str | None] = mapped_column(String, nullable=True)
    police_stage: Mapped[str] = mapped_column(String, default="Draft Prepared")
    police_report_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    police_draft_status: Mapped[str] = mapped_column(String, default="draft_pending_review")  # draft_pending_review | approved_by_user | submitted_to_station | fir_recorded
    police_draft_approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    police_draft_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    insurance_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_policy_number: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_claim_number: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_stage: Mapped[str] = mapped_column(String, default="Claim Intimated")
    insurance_surveyor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_surveyor_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_settlement_status: Mapped[str | None] = mapped_column(String, default="In Progress - Cashless Assessment")
    demo_clock_offset_hours: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    primary_vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CaseStatusTransition(Base):
    __tablename__ = "case_status_transitions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cst"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    from_status: Mapped[str] = mapped_column(String)
    to_status: Mapped[str] = mapped_column(String)
    changed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    transition_trigger: Mapped[str] = mapped_column(String, default="manual_user_action")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CaseMember(Base):
    __tablename__ = "case_members"
    id: Mapped[str | None] = mapped_column(String, default=lambda: new_id("cm"), nullable=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    member_name: Mapped[str | None] = mapped_column(String, nullable=True)
    member_email: Mapped[str | None] = mapped_column(String, nullable=True)
    member_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="member")  # coordinator | editor | viewer
    relationship: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_number: Mapped[str | None] = mapped_column(String, nullable=True)
    permissions_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    invitation_status: Mapped[str] = mapped_column(String, default="active")
    can_view_case: Mapped[bool] = mapped_column(Boolean, default=True)
    can_upload_evidence: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_documents: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_tasks: Mapped[bool] = mapped_column(Boolean, default=True)
    can_approve_reports: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_medical: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CaseVehicle(Base):
    __tablename__ = "case_vehicles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cv"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    registration_number: Mapped[str] = mapped_column(String)
    vehicle_involvement_type: Mapped[str] = mapped_column(String, default="primary_subject")
    damage_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    damage_severity: Mapped[str] = mapped_column(String, default="Moderate")
    make_model: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    driver_name: Mapped[str | None] = mapped_column(String, nullable=True)
    driver_contact: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_company: Mapped[str | None] = mapped_column(String, nullable=True)
    insurance_policy_no: Mapped[str | None] = mapped_column(String, nullable=True)
    is_third_party: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CaseInvolvedPerson(Base):
    __tablename__ = "case_involved_people"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cip"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    case_vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("case_vehicles.id"), nullable=True)
    associated_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String)
    involvement_type: Mapped[str] = mapped_column(String, default="driver")
    relationship_to_coordinator: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_number: Mapped[str | None] = mapped_column(String, nullable=True)
    reported_injury_status: Mapped[str] = mapped_column(String, default="uninjured")
    injury_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String, nullable=True)
    treatment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CaseEvidence(Base):
    __tablename__ = "case_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ce"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    evidence_category: Mapped[str] = mapped_column(String, default="scene_photo")
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_source: Mapped[str] = mapped_column(String, default="user_upload")
    associated_case_vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("case_vehicles.id"), nullable=True)
    associated_person_id: Mapped[str | None] = mapped_column(ForeignKey("case_involved_people.id"), nullable=True)
    verification_status: Mapped[str] = mapped_column(String, default="pending")
    capture_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    geo_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("doc"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String, default="pending")  # pending|analyzed|failed
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("fld"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    name: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String, default="needs_review")  # needs_review|confirmed
    confirmed_by: Mapped[str | None] = mapped_column(String, nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("task"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String, default="general")
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    due_source: Mapped[str | None] = mapped_column(String, nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    related_entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, default=dict, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rpt"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    path: Mapped[str] = mapped_column(String)
    created_by: Mapped[str] = mapped_column(String)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String, default="Accident Case Summary Report")
    report_type: Mapped[str] = mapped_column(String, default="accident_summary")
    status: Mapped[str] = mapped_column(String, default="draft", index=True)  # draft | ready_for_review | approved | rejected | archived
    current_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("report_versions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    generation_source: Mapped[str] = mapped_column(String, default="ai_generated")  # ai_generated | user_created | system_generated
    path: Mapped[str | None] = mapped_column(String, nullable=True)  # Legacy file path / compatibility
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    versions: Mapped[list[ReportVersion]] = orm_relationship(
        "ReportVersion", back_populates="report", cascade="all, delete-orphan", foreign_keys="[ReportVersion.report_id]"
    )
    current_version: Mapped[ReportVersion | None] = orm_relationship(
        "ReportVersion", foreign_keys=[current_version_id], post_update=True
    )


class ReportVersion(Base):
    __tablename__ = "report_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rptv"))
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    content_json: Mapped[dict | list] = mapped_column(JSON, default=dict)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    generated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    generation_method: Mapped[str] = mapped_column(String, default="ai_assisted")  # ai_assisted | user_drafted | template_compiled
    ai_model: Mapped[str | None] = mapped_column(String, nullable=True)
    source_references_json: Mapped[dict | list] = mapped_column(JSON, default=list)
    version_status: Mapped[str] = mapped_column(String, default="draft")  # draft | ready_for_review | approved | superseded | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    report: Mapped[Report] = orm_relationship("Report", back_populates="versions", foreign_keys=[report_id])


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("claim"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("vehicle_insurance_policies.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    insurer_name: Mapped[str] = mapped_column(String)
    policy_number: Mapped[str] = mapped_column(String)
    claim_reference_number: Mapped[str | None] = mapped_column(String, nullable=True)
    claim_type: Mapped[str] = mapped_column(String, default="own_damage")  # own_damage | third_party_liability | comprehensive | personal_accident
    incident_date: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Text, default="")
    estimated_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    claim_status: Mapped[str] = mapped_column(String, default="draft", index=True)
    # draft | preparing | ready_for_review | approved_by_user | submitted | under_review | additional_info_required | approved_by_insurer | rejected | settled | withdrawn
    filed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    surveyor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    surveyor_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    cashless_garage: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    submissions: Mapped[list[ExternalSubmission]] = orm_relationship("ExternalSubmission", back_populates="claim", cascade="all, delete-orphan")


class ExternalSubmission(Base):
    __tablename__ = "external_submissions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("exsub"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[str | None] = mapped_column(ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("insurance_claims.id", ondelete="SET NULL"), nullable=True)
    submitted_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    external_org_name: Mapped[str] = mapped_column(String)  # e.g. "Tata AIG General Insurance", "HSR Layout Police Station", "PM-RAHAT Portal"
    external_org_type: Mapped[str] = mapped_column(String, default="insurer")  # insurer | police | hospital | government | court | legal
    external_reference_number: Mapped[str | None] = mapped_column(String, nullable=True)
    submission_method: Mapped[str] = mapped_column(String, default="manual_user_submission")  # manual_user_submission | email | portal_upload | physical_handover | api
    submission_status: Mapped[str] = mapped_column(String, default="draft", index=True)  # draft | queued | submitted | acknowledged | rejected | failed
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, default=dict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    claim: Mapped[InsuranceClaim | None] = orm_relationship("InsuranceClaim", back_populates="submissions")


class PendingAction(Base):
    __tablename__ = "pending_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("act"))
    case_id: Mapped[str] = mapped_column(String)
    actor_id: Mapped[str] = mapped_column(String)
    tool: Mapped[str] = mapped_column(String)
    arguments_json: Mapped[str] = mapped_column(Text)
    preview: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="proposed")  # proposed|approved|rejected|failed
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def arguments(self) -> dict:
        return json.loads(self.arguments_json)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String, default="user")  # user, system, ai, api
    action_type: Mapped[str] = mapped_column(String, default="action")
    resource_type: Mapped[str] = mapped_column(String, default="general")
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tool: Mapped[str | None] = mapped_column(String, nullable=True)
    arguments_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str] = mapped_column(Text, default="")
    action_outcome: Mapped[str] = mapped_column(String, default="success")  # success, failure, denied
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    approval_state: Mapped[str] = mapped_column(String, default="standard")  # auto_read_only|proposed|approved|rejected|error
    sanitized_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AIActionLog(Base):
    __tablename__ = "ai_action_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("aiact"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String, index=True)
    action_description: Mapped[str] = mapped_column(Text)
    input_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    output_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    action_status: Mapped[str] = mapped_column(String, default="proposed", index=True)  # proposed | awaiting_approval | approved | rejected | executing | completed | failed | cancelled
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    execution_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("veh"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    registration_number: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String, default="Four Wheeler")  # Two Wheeler | Four Wheeler | Commercial | Other
    manufacturer: Mapped[str] = mapped_column(String)  # e.g. Honda
    model: Mapped[str] = mapped_column(String)         # e.g. City
    variant: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. ZX CVT
    manufacturing_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_type: Mapped[str] = mapped_column(String, default="Petrol")
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    chassis_number: Mapped[str | None] = mapped_column(String, nullable=True)
    engine_number: Mapped[str | None] = mapped_column(String, nullable=True)
    vin: Mapped[str | None] = mapped_column(String, nullable=True)
    engine_capacity: Mapped[str | None] = mapped_column(String, nullable=True)
    transmission: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String, nullable=True)
    ownership_type: Mapped[str] = mapped_column(String, default="Individual")
    relationship_to_user: Mapped[str | None] = mapped_column(String, nullable=True)
    main_image: Mapped[str | None] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registration_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String, default="unverified")  # unverified | pending | verified | failed
    verification_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class VehicleDocument(Base):
    __tablename__ = "vehicle_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("vdoc"))
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    document_type: Mapped[str] = mapped_column(String)  # rc | insurance | puc | purchase_invoice | service_record | other
    document_name: Mapped[str] = mapped_column(String)
    file_name: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String, default="verified")  # verified | expiring_soon | expired | pending
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VehiclePhoto(Base):
    __tablename__ = "vehicle_photos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("vpho"))
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    photo_category: Mapped[str] = mapped_column(String, default="main")  # main | front | rear | left | right | additional
    file_name: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    storage_key: Mapped[str] = mapped_column(String, default="")
    mime_type: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VehicleInsurancePolicy(Base):
    __tablename__ = "vehicle_insurance_policies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("vpol"))
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    policy_number: Mapped[str] = mapped_column(String)
    policy_type: Mapped[str] = mapped_column(String, default="Comprehensive")
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    document_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_current_policy: Mapped[bool] = mapped_column(Boolean, default=True)
    policy_status: Mapped[str] = mapped_column(String, default="active")  # active | expired | renewed | cancelled
    superseded_by_policy_id: Mapped[str | None] = mapped_column(ForeignKey("vehicle_insurance_policies.id", ondelete="SET NULL"), nullable=True)
    coverage_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CentralDocument(Base):
    __tablename__ = "central_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cdoc"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    document_name: Mapped[str] = mapped_column(String)
    document_type: Mapped[str] = mapped_column(String)  # driving_licence, rc, insurance, puc, medical_report, hospital_bill, aadhaar, pan, passport, fir, etc.
    category: Mapped[str] = mapped_column(String, index=True)  # personal, driving_licence, vehicle, insurance, medical, accident_case, other
    file_name: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    storage_key: Mapped[str] = mapped_column(String, default="")
    mime_type: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String, nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String, default="unverified")  # unverified | pending | verified | failed
    verification_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(String, default="USER")  # USER | VEHICLE | ACCIDENT_CASE
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # user_id, vehicle_id, or case_id
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    versions: Mapped[list[DocumentVersion]] = orm_relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="desc(DocumentVersion.version_number)")
    access_logs: Mapped[list[DocumentAccessLog]] = orm_relationship("DocumentAccessLog", back_populates="document", cascade="all, delete-orphan", order_by="desc(DocumentAccessLog.accessed_at)")


class DocumentVersion(Base):
    """Historical revision archive for re-uploaded or renewed central documents."""
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number", name="uq_document_version"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("dver"))
    document_id: Mapped[str] = mapped_column(ForeignKey("central_documents.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str] = mapped_column(String)
    file_name: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    change_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[CentralDocument] = orm_relationship("CentralDocument", back_populates="versions")


class DocumentAccessLog(Base):
    """Append-only audit trail for viewing, downloading, exporting, or sharing sensitive documents."""
    __tablename__ = "document_access_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("central_documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String)  # 'view', 'download', 'upload', 'replace', 'delete'
    access_channel: Mapped[str] = mapped_column(String, default="web_dashboard")
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    case_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[CentralDocument] = orm_relationship("CentralDocument", back_populates="access_logs")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("conv"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, default="New Conversation")
    status: Mapped[str] = mapped_column(String, default="active", index=True)  # active | archived
    ai_provider: Mapped[str] = mapped_column(String, default="gemini")
    model_identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    context_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    messages: Mapped[list[ConversationMessage]] = orm_relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.sequence_number")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cmsg"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String)  # user | assistant
    sender_type: Mapped[str] = mapped_column(String, default="user")  # user | assistant | system | tool
    content: Mapped[str] = mapped_column(Text)
    content_format: Mapped[str] = mapped_column(String, default="text")  # text | markdown | json
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)
    tool_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_references_json: Mapped[list | dict | None] = mapped_column(JSON, default=list)
    ai_model_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)
    token_usage_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)
    citations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_cards_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_followups_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = orm_relationship("Conversation", back_populates="messages")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("econtact"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String)
    relationship: Mapped[str] = mapped_column(String)  # Parent, Spouse, Sibling, Child, Relative, Friend, Other
    mobile_number: Mapped[str] = mapped_column(String)
    alternate_number: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_contact_method: Mapped[str] = mapped_column(String, default="phone")  # phone, whatsapp, sms
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    permission: Mapped[EmergencyContactPermission | None] = orm_relationship(
        "EmergencyContactPermission", back_populates="contact", uselist=False, cascade="all, delete-orphan"
    )


class EmergencyContactPermission(Base):
    __tablename__ = "emergency_contact_permissions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ecperm"))
    contact_id: Mapped[str] = mapped_column(ForeignKey("emergency_contacts.id", ondelete="CASCADE"), unique=True, index=True)

    # Outbound Notification Dispatch Permissions (SMS / WhatsApp / SOS)
    can_notify_accident_sos: Mapped[bool] = mapped_column(Boolean, default=True)
    can_receive_case_sms: Mapped[bool] = mapped_column(Boolean, default=True)
    can_receive_whatsapp_updates: Mapped[bool] = mapped_column(Boolean, default=False)

    # Interactive Account & Case Workspace Permissions
    has_workspace_access: Mapped[bool] = mapped_column(Boolean, default=False)
    permitted_case_ids: Mapped[str] = mapped_column(String, default="[]")  # JSON list of case IDs
    workspace_role: Mapped[str] = mapped_column(String, default="viewer")
    can_view_limited_summary_only: Mapped[bool] = mapped_column(Boolean, default=True)

    # Sensitive Resource Overrides (Strictly False by default)
    can_view_medical: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_documents: Mapped[bool] = mapped_column(Boolean, default=False)

    granted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    contact: Mapped[EmergencyContact | None] = orm_relationship("EmergencyContact", back_populates="permission")

    # Backward compatibility accessors
    @property
    def can_notify_accident(self) -> bool:
        return self.can_notify_accident_sos

    @can_notify_accident.setter
    def can_notify_accident(self, val: bool) -> None:
        self.can_notify_accident_sos = val

    @property
    def can_receive_case_updates(self) -> bool:
        return self.can_receive_case_sms

    @can_receive_case_updates.setter
    def can_receive_case_updates(self, val: bool) -> None:
        self.can_receive_case_sms = val

    @property
    def can_access_case(self) -> bool:
        return self.has_workspace_access

    @can_access_case.setter
    def can_access_case(self, val: bool) -> None:
        self.has_workspace_access = val

    @property
    def can_view_limited_case_info(self) -> bool:
        return self.can_view_limited_summary_only

    @can_view_limited_case_info.setter
    def can_view_limited_case_info(self, val: bool) -> None:
        self.can_view_limited_summary_only = val


class MedicalInformation(Base):
    __tablename__ = "medical_information"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("medinfo"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    blood_group: Mapped[str | None] = mapped_column(String, nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_with_ems: Mapped[bool] = mapped_column(Boolean, default=False)
    share_with_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class MedicalAccessLog(Base):
    """Append-only audit trail for viewing or sharing quarantined medical information."""
    __tablename__ = "medical_access_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    access_purpose: Mapped[str] = mapped_column(String)  # 'emergency_ems_triage' | 'hospital_intake' | 'user_self_view' | 'ai_assistant_query'
    authorization_type: Mapped[str] = mapped_column(String)  # 'explicit_user_consent' | 'ems_emergency_protocol' | 'self_authorized'
    fields_accessed: Mapped[str] = mapped_column(Text, default="[]")
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserAddress(Base):
    __tablename__ = "user_addresses"
    __table_args__ = (UniqueConstraint("user_id", "address_type", name="uq_user_address_type"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("uaddr"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    address_type: Mapped[str] = mapped_column(String)  # current | permanent
    address_line_1: Mapped[str] = mapped_column(String)
    address_line_2: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    pin_code: Mapped[str] = mapped_column(String)
    country: Mapped[str] = mapped_column(String, default="India")
    is_same_as_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class UserPrivacyPreference(Base):
    __tablename__ = "user_privacy_preferences"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("privpref"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    ai_data_access_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_include_medical: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_include_documents: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_include_vehicles: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_include_cases: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_emergency_broadcast: Mapped[bool] = mapped_column(Boolean, default=True)
    conversation_retention_days: Mapped[int] = mapped_column(Integer, default=365)
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    data_sharing_preferences: Mapped[dict] = mapped_column(JSON, default=lambda: {"anonymized_research": False, "insurer_direct_share": False})
    medical_info_sharing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("notifpref"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    in_app_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    accident_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    case_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    document_expiry_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_renewal_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    pending_task_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_action_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[str] = mapped_column(String, default="22:00")
    quiet_hours_end: Mapped[str] = mapped_column(String, default="07:00")
    quiet_hours_timezone: Mapped[str] = mapped_column(String, default="Asia/Kolkata")
    preferred_language: Mapped[str] = mapped_column(String, default="English")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("consent"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    consent_type: Mapped[str] = mapped_column(String, index=True)  # terms_of_service | privacy_policy | ai_data_processing | medical_information_sharing | emergency_contact_data_sharing | external_document_sharing | notifications | pm_rahat_claim_intake
    consent_status: Mapped[str] = mapped_column(String, default="granted", index=True)  # granted | revoked | expired
    policy_version: Mapped[str] = mapped_column(String, default="1.0")
    consent_source: Mapped[str] = mapped_column(String, default="web_application")
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VerificationRecord(Base):
    """Immutable log of verification transactions across users, vehicles, and documents."""
    __tablename__ = "verification_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("vrec"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)  # USER_EMAIL | USER_PHONE | IDENTITY_DOCUMENT | VEHICLE_RC | VEHICLE_INSURANCE
    entity_id: Mapped[str] = mapped_column(String, index=True)    # user_id, document_id, vehicle_id, policy_id
    provider: Mapped[str] = mapped_column(String)                 # DIGILOCKER | VAHAN_PARIVAHAN | IIB_INSURANCE | SMS_OTP | EMAIL_OTP
    status: Mapped[str] = mapped_column(String, default="PENDING")# PENDING | VERIFIED | FAILED | REVOKED
    verification_type: Mapped[str] = mapped_column(String)       # OTP | API_MATCH | OAUTH_DIGILOCKER
    verification_reference_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_record_id: Mapped[str | None] = mapped_column(ForeignKey("consent_records.id"), nullable=True)
    raw_response_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class OtpVerification(Base):
    """Manages ephemeral, cryptographically salted and hashed OTP codes for mobile and email."""
    __tablename__ = "otp_verifications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("otp"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String)                  # email | phone
    target: Mapped[str] = mapped_column(String)                   # email or phone
    otp_hash: Mapped[str] = mapped_column(String)                 # Salted SHA-256 hash
    salt: Mapped[str] = mapped_column(String)                     # Hex salt
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


def init_db() -> None:
    """Initialize database schema safely, reporting diagnostic details if unavailable."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database schema initialized successfully (dialect: %s)", engine.dialect.name)
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)
        raise
