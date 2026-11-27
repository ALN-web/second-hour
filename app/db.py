"""SQLAlchemy models and database connectivity layer (PostgreSQL / SQLite)."""
from __future__ import annotations

import json
import logging
import urllib.parse
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event, select, text
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CaseMember(Base):
    __tablename__ = "case_members"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String, default="member")  # coordinator | editor | viewer
    relationship: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_number: Mapped[str | None] = mapped_column(String, nullable=True)
    permissions_summary: Mapped[str | None] = mapped_column(String, nullable=True)
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
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    due_source: Mapped[str | None] = mapped_column(String, nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rpt"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    path: Mapped[str] = mapped_column(String)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


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
    case_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tool: Mapped[str] = mapped_column(String)
    arguments_json: Mapped[str] = mapped_column(Text)
    result_summary: Mapped[str] = mapped_column(Text)
    approval_state: Mapped[str] = mapped_column(String)  # auto_read_only|proposed|approved|rejected|error
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


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
    mime_type: Mapped[str] = mapped_column(String)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CentralDocument(Base):
    __tablename__ = "central_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cdoc"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    document_name: Mapped[str] = mapped_column(String)
    document_type: Mapped[str] = mapped_column(String)  # driving_licence, rc, insurance, puc, medical_report, hospital_bill, aadhaar, pan, passport, fir, etc.
    category: Mapped[str] = mapped_column(String, index=True)  # personal, driving_licence, vehicle, insurance, medical, accident_case, other
    file_name: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String, nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String, default="verified")  # verified | expiring_soon | expired | pending | not_verified
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(String, default="USER")  # USER | VEHICLE | ACCIDENT_CASE
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # user_id, vehicle_id, or case_id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("conv"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, default="New Conversation")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    context_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cmsg"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String)  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_cards_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_followups_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


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
    accident_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    case_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    document_expiry_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_renewal_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    pending_task_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


def init_db() -> None:
    """Initialize database schema safely, reporting diagnostic details if unavailable."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database schema initialized successfully (dialect: %s)", engine.dialect.name)
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)
        raise
