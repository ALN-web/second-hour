"""SQLAlchemy models (SQLite, one file)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False, "timeout": 30})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


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


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("case"))
    case_number: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="open")
    incident_at: Mapped[datetime] = mapped_column(DateTime)
    approximate_location: Mapped[str] = mapped_column(String)
    victim_display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String, nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    life_threatening: Mapped[bool] = mapped_column(Boolean, default=False)
    police_auth_status: Mapped[str] = mapped_column(String, default="not_started")
    police_auth_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    demo_clock_offset_hours: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CaseMember(Base):
    __tablename__ = "case_members"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String, default="member")


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


def init_db() -> None:
    Base.metadata.create_all(engine)
