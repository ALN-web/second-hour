"""Case, task, timeline, checklist and alert (watcher) services."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.db import Case, CaseMember, Document, ExtractedField, Task, TimelineEvent, User, utcnow
from app.services.common import (
    ServiceError,
    add_event,
    case_now,
    iso,
    parse_dt,
    require_member,
    require_user,
)

POLICE_STATUSES = ("not_started", "requested_by_hospital", "confirmed", "not_confirmed")
PRIORITIES = ("low", "medium", "high")

# Configurable document checklist (guidance, not a legal determination)
CHECKLIST = [
    {"key": "medical_report", "label": "Medical / discharge report", "reason": "Records diagnosis and treatment; usually asked for by insurers and in claims."},
    {"key": "hospital_bill", "label": "Hospital bill / estimate", "reason": "Lets the family track treatment cost against the ₹1.5 lakh PM-RAHAT cover."},
    {"key": "police_document", "label": "Police document (FIR / GD entry / MLC copy)", "reason": "Road accident cases typically involve a police record; useful for insurance and claims."},
    {"key": "vehicle_document", "label": "Vehicle documents (RC / licence)", "reason": "Often requested for motor insurance or accident claims."},
    {"key": "insurance_policy", "label": "Insurance policy copy", "reason": "Health or motor insurance may cover costs beyond the scheme."},
]


# ---------------------------------------------------------------- cases

def _next_case_number(db: Session) -> str:
    n = db.scalar(select(func.count()).select_from(Case)) or 0
    return f"SH-{utcnow():%Y}-{n + 1:04d}"


def create_case(db: Session, actor_id: str, incident_at: str, approximate_location: str,
                victim_display_name: str | None = None, hospital_name: str | None = None,
                life_threatening: bool = False) -> dict:
    require_user(db, actor_id)
    inc = parse_dt(incident_at, "incident_at")
    if not inc:
        raise ServiceError("incident_at is required")
    if inc > utcnow() + timedelta(minutes=5):
        raise ServiceError("incident_at cannot be in the future")
    if not approximate_location or not approximate_location.strip():
        raise ServiceError("approximate_location is required")
    case = Case(case_number=_next_case_number(db), incident_at=inc,
                approximate_location=approximate_location.strip()[:200],
                victim_display_name=(victim_display_name or "").strip()[:100] or None,
                hospital_name=(hospital_name or "").strip()[:200] or None,
                life_threatening=bool(life_threatening), created_by=actor_id)
    db.add(case)
    db.flush()
    db.add(CaseMember(case_id=case.id, user_id=actor_id, role="coordinator"))
    add_event(db, case.id, actor_id, "case_created", f"Case {case.case_number} created")
    db.commit()
    return {"case_id": case.id, "case_number": case.case_number, "status": case.status}


def list_cases_for(db: Session, user_id: str) -> list[dict]:
    rows = db.scalars(select(Case).join(CaseMember, CaseMember.case_id == Case.id)
                      .where(CaseMember.user_id == user_id).order_by(Case.created_at.desc())).all()
    return [{"case_id": c.id, "case_number": c.case_number, "victim_display_name": c.victim_display_name,
             "hospital_name": c.hospital_name, "status": c.status, "incident_at": iso(c.incident_at)} for c in rows]


def members(db: Session, case_id: str) -> list[dict]:
    rows = db.execute(select(User, CaseMember.role).join(CaseMember, CaseMember.user_id == User.id)
                      .where(CaseMember.case_id == case_id)).all()
    return [{"user_id": u.id, "name": u.name, "role": r} for u, r in rows]


def inr(amount: float) -> str:
    """Indian digit grouping: 124000 -> 1,24,000."""
    s = f"{int(round(amount))}"
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def day_of_cover(case: Case, now: datetime) -> int:
    hours = (now - case.incident_at).total_seconds() / 3600
    return max(1, math.floor(hours / 24) + 1)


def confirmed_bill_total(db: Session, case_id: str) -> float:
    rows = db.scalars(select(ExtractedField).join(Document, Document.id == ExtractedField.document_id)
                      .where(ExtractedField.case_id == case_id, ExtractedField.name == "total_amount",
                             ExtractedField.status == "confirmed", Document.category == "hospital_bill")).all()
    total = 0.0
    for f in rows:
        try:
            total += float(str(f.value).replace(",", "").replace("₹", "").strip())
        except ValueError:
            continue
    return total


def get_case_summary(db: Session, actor_id: str, case_id: str) -> dict:
    case = require_member(db, actor_id, case_id)
    now = case_now(case)
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    needs_review = db.scalar(select(func.count()).select_from(ExtractedField)
                             .where(ExtractedField.case_id == case_id, ExtractedField.status == "needs_review")) or 0
    open_tasks = db.scalars(select(Task).where(Task.case_id == case_id, Task.status == "open")).all()
    day = day_of_cover(case, now)
    spent = confirmed_bill_total(db, case_id)
    checklist = get_missing_documents(db, actor_id, case_id)
    alerts = get_case_alerts(db, actor_id, case_id)["alerts"]
    next_steps = [a["suggested_task"]["title"] for a in alerts if a.get("suggested_task")]
    if checklist["missing"]:
        next_steps.append(f"Collect: {checklist['missing'][0]['label']}")
    if needs_review:
        next_steps.append(f"Review {needs_review} extracted field(s) marked 'Needs review'")
    return {
        "case_id": case.id, "case_number": case.case_number, "status": case.status,
        "victim_display_name": case.victim_display_name, "hospital_name": case.hospital_name,
        "approximate_location": case.approximate_location, "incident_at": iso(case.incident_at),
        "life_threatening": case.life_threatening,
        "clock_now": iso(now), "demo_clock_offset_hours": case.demo_clock_offset_hours,
        "milestones": {
            "cover_window": {"day": day, "of": config.COVER_DAYS, "within_window": day <= config.COVER_DAYS,
                             "window_ends_at": iso(case.incident_at + timedelta(days=config.COVER_DAYS))},
            "cover_amount": {"confirmed_bills_inr": spent, "cover_limit_inr": config.COVER_LIMIT_INR,
                             "percent_used": round(100 * spent / config.COVER_LIMIT_INR, 1),
                             "note": "Sum of user-confirmed hospital bill totals only. Not a prediction of what the family will pay."},
            "police_authentication": {"status": case.police_auth_status, "updated_at": iso(case.police_auth_updated_at),
                                      "label": "user-provided, unverified"},
        },
        "document_counts": {"total": len(docs), "analyzed": sum(d.analysis_status == "analyzed" for d in docs),
                            "fields_needing_review": needs_review},
        "open_tasks": [_task_dict(t) for t in open_tasks],
        "members": members(db, case_id),
        "alerts": alerts,
        "next_steps": next_steps[:5],
        "disclaimer": "Second Hour is not an emergency service. In an emergency, call 112.",
    }


def set_police_status(db: Session, actor_id: str, case_id: str, status: str) -> dict:
    case = require_member(db, actor_id, case_id)
    if status not in POLICE_STATUSES:
        raise ServiceError(f"status must be one of {POLICE_STATUSES}")
    case.police_auth_status = status
    case.police_auth_updated_at = case_now(case)
    add_event(db, case_id, actor_id, "police_status", f"Family recorded police authentication status: {status} (user-provided, unverified)")
    db.commit()
    return {"status": status, "updated_at": iso(case.police_auth_updated_at)}


def advance_clock(db: Session, actor_id: str, case_id: str, hours: float) -> dict:
    case = require_member(db, actor_id, case_id)
    if hours == 0:
        case.demo_clock_offset_hours = 0
    else:
        case.demo_clock_offset_hours = (case.demo_clock_offset_hours or 0) + hours
    add_event(db, case_id, actor_id, "demo_clock", f"Demo clock offset set to +{case.demo_clock_offset_hours:g}h")
    db.commit()
    return {"demo_clock_offset_hours": case.demo_clock_offset_hours, "clock_now": iso(case_now(case))}


# ---------------------------------------------------------------- watchers

def get_case_alerts(db: Session, actor_id: str, case_id: str, now: str | None = None) -> dict:
    """Deterministic watchers. No LLM involved."""
    case = require_member(db, actor_id, case_id)
    t = case_now(case, parse_dt(now, "now"))
    alerts: list[dict] = []

    # Rule 1: cover window tracker
    day = day_of_cover(case, t)
    spent = confirmed_bill_total(db, case_id)
    pct = spent / config.COVER_LIMIT_INR
    if pct >= 0.8 or day >= 6:
        reasons = []
        if day >= 6:
            reasons.append(f"it is day {day} of the {config.COVER_DAYS}-day PM-RAHAT window" if day <= 7
                           else f"the {config.COVER_DAYS}-day PM-RAHAT window from the accident date has passed (day {day})")
        if pct >= 0.8:
            reasons.append(f"confirmed hospital bills total ₹{inr(spent)}, which is {pct:.0%} of the ₹1,50,000 cover")
        alerts.append({
            "id": "cover_window", "rule": "cover_window_tracker", "severity": "high" if (pct >= 1 or day > 7) else "medium",
            "title": "PM-RAHAT cover limit approaching" if pct >= 0.8 else "PM-RAHAT 7-day window closing",
            "message": "Heads-up: " + " and ".join(reasons) + ". Second Hour does not predict what the family will pay.",
            "facts": {"day": day, "of": config.COVER_DAYS, "confirmed_bills_inr": spent, "cover_limit_inr": config.COVER_LIMIT_INR},
            "source": {"title": "PIB, 11 March 2026: PM-RAHAT salient features", "url": config.PIB_MARCH_URL},
            "suggested_task": {"title": "Ask the hospital billing desk how treatment beyond the cover will be handled",
                               "priority": "high"},
        })

    # Rule 2: police authentication status watcher
    if case.police_auth_status == "requested_by_hospital" and case.police_auth_updated_at:
        window = config.POLICE_WINDOW_HOURS_LIFE_THREATENING if case.life_threatening else config.POLICE_WINDOW_HOURS
        elapsed = (t - case.police_auth_updated_at).total_seconds() / 3600
        if elapsed > window:
            alerts.append({
                "id": "police_auth", "rule": "police_authentication_watcher", "severity": "medium",
                "title": "Police authentication still pending",
                "message": (f"The family recorded 'requested by hospital' {elapsed:.0f} hours ago (user-provided, unverified). "
                            f"Under PM-RAHAT the hospital raises police authentication on the TMS platform via eDAR, and police "
                            f"respond to the hospital within {window} hours{' for life-threatening cases' if case.life_threatening else ''}. "
                            "This is the hospital's and police's process, not a family deadline. It may help to ask the hospital desk for an update."),
                "facts": {"hours_elapsed": round(elapsed, 1), "official_window_hours": window},
                "source": {"title": "PIB, 11 March 2026: PM-RAHAT salient features", "url": config.PIB_MARCH_URL},
                "suggested_task": {"title": "Ask the hospital desk for the police authentication status", "priority": "medium"},
            })
    return {"case_id": case_id, "evaluated_at": iso(t), "day_of_cover": day, "alerts": alerts}


# ---------------------------------------------------------------- checklist

def get_missing_documents(db: Session, actor_id: str, case_id: str) -> dict:
    require_member(db, actor_id, case_id)
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    pending_fields = {f.document_id for f in db.scalars(select(ExtractedField).where(
        ExtractedField.case_id == case_id, ExtractedField.status == "needs_review")).all()}
    present, missing, review = [], [], []
    for item in CHECKLIST:
        matching = [d for d in docs if d.category == item["key"]]
        if not matching:
            missing.append({**item, "status": "missing"})
        elif any(d.id in pending_fields for d in matching):
            review.append({**item, "status": "needs_review", "document_ids": [d.id for d in matching],
                           "reason": "Document uploaded; extracted fields still need family confirmation."})
        else:
            present.append({**item, "status": "present", "document_ids": [d.id for d in matching]})
    unclassified = [d.id for d in docs if d.analysis_status != "analyzed"]
    return {"present": present, "missing": missing, "needs_review": review, "unanalyzed_document_ids": unclassified,
            "label": "Guidance, not a legal determination. Requirements vary by hospital, insurer and state."}


# ---------------------------------------------------------------- tasks

def _task_dict(t: Task) -> dict:
    return {"task_id": t.id, "title": t.title, "description": t.description, "priority": t.priority,
            "status": t.status, "due_at": iso(t.due_at), "due_source": t.due_source, "assignee_id": t.assignee_id}


def create_task(db: Session, actor_id: str, case_id: str, title: str, description: str = "",
                priority: str = "medium", due_at: str | None = None, due_source: str | None = None) -> dict:
    require_member(db, actor_id, case_id)
    if not title or not title.strip():
        raise ServiceError("title is required")
    if priority not in PRIORITIES:
        raise ServiceError(f"priority must be one of {PRIORITIES}")
    due = parse_dt(due_at, "due_at")
    if due and not (due_source and due_source.strip()):
        raise ServiceError("A due date needs a due_source (user-confirmed or an official source). Leave due_at empty otherwise.")
    t = Task(case_id=case_id, title=title.strip()[:200], description=(description or "")[:2000], priority=priority,
             due_at=due, due_source=(due_source or None), created_by=actor_id)
    db.add(t)
    db.flush()
    add_event(db, case_id, actor_id, "task_created", f"Task created: {t.title}")
    db.commit()
    return _task_dict(t)


def assign_task(db: Session, actor_id: str, case_id: str, task_id: str, member_id: str) -> dict:
    require_member(db, actor_id, case_id)
    t = db.get(Task, task_id)
    if not t or t.case_id != case_id:
        raise ServiceError(f"Task '{task_id}' not found in this case")
    require_member(db, member_id, case_id)  # assignee must also be a member
    t.assignee_id = member_id
    name = db.get(User, member_id).name
    add_event(db, case_id, actor_id, "task_assigned", f"Task '{t.title}' assigned to {name}")
    db.commit()
    return _task_dict(t)


def list_tasks(db: Session, actor_id: str, case_id: str) -> list[dict]:
    require_member(db, actor_id, case_id)
    return [_task_dict(t) for t in db.scalars(select(Task).where(Task.case_id == case_id).order_by(Task.created_at)).all()]


def set_task_status(db: Session, actor_id: str, case_id: str, task_id: str, status: str) -> dict:
    require_member(db, actor_id, case_id)
    t = db.get(Task, task_id)
    if not t or t.case_id != case_id or status not in ("open", "done"):
        raise ServiceError("Invalid task or status")
    t.status = status
    add_event(db, case_id, actor_id, "task_status", f"Task '{t.title}' marked {status}")
    db.commit()
    return _task_dict(t)


def timeline(db: Session, actor_id: str, case_id: str) -> list[dict]:
    require_member(db, actor_id, case_id)
    rows = db.scalars(select(TimelineEvent).where(TimelineEvent.case_id == case_id).order_by(TimelineEvent.at.desc())).all()
    return [{"at": iso(e.at), "actor_id": e.actor_id, "kind": e.kind, "summary": e.summary} for e in rows]
