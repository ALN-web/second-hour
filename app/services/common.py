"""Shared helpers: errors, membership checks, timeline, serialisation."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db import Case, CaseMember, TimelineEvent, User, utcnow


class ServiceError(Exception):
    """A user-facing error (bad input, not found, forbidden)."""


class PermissionDenied(ServiceError):
    pass


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="minutes") if dt else None


def parse_dt(value: str | None, field: str) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ServiceError(f"{field} must be an ISO-8601 datetime, got {value!r}") from e
    if dt.tzinfo is not None:
        # Store naive UTC
        dt = (dt - dt.utcoffset()).replace(tzinfo=None)
    return dt


def require_user(db: Session, actor_id: str) -> User:
    user = db.get(User, actor_id)
    if not user:
        raise PermissionDenied(f"Unknown actor '{actor_id}'")
    return user


def require_member(db: Session, actor_id: str, case_id: str) -> Case:
    """Server-side authorisation: actor must be a member of the case."""
    require_user(db, actor_id)
    case = db.get(Case, case_id)
    if not case:
        raise ServiceError(f"Case '{case_id}' not found")
    if not db.get(CaseMember, (case_id, actor_id)):
        raise PermissionDenied(f"Actor '{actor_id}' is not a member of case '{case_id}'")
    return case


def is_member(db: Session, user_id: str, case_id: str) -> bool:
    return db.get(CaseMember, (case_id, user_id)) is not None


def add_event(db: Session, case_id: str, actor_id: str | None, kind: str, summary: str) -> None:
    db.add(TimelineEvent(case_id=case_id, actor_id=actor_id, kind=kind, summary=summary))


def case_now(case: Case, now: datetime | None = None) -> datetime:
    """The demo clock: real UTC now + per-case offset, unless an explicit `now` is given."""
    if now is not None:
        return now
    return utcnow() + timedelta(hours=case.demo_clock_offset_hours or 0)
