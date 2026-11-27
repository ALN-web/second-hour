"""Context-Aware AI Assistant Service for Second Hour.

Provides full-screen intelligent assistance grounded in:
1. User Profile & Emergency Contacts
2. Registered Vehicles & Insurance Policies
3. Centralized Documents Wallet & Extracted Data
4. Accident Cases, Hospitalization, Police & Insurance Aftermath
5. Official PM-RAHAT Scheme Knowledge & MoRTH Guidance

Includes source citations, interactive action cards, and user data isolation.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.orm import Session

from app import config
from app.db import (
    AIActionLog,
    Case,
    CaseMember,
    CentralDocument,
    Conversation,
    ConversationMessage,
    Document,
    ExtractedField,
    Task,
    TimelineEvent,
    User,
    Vehicle,
    VehicleDocument,
    VehicleInsurancePolicy,
    VehiclePhoto,
    new_id,
    utcnow,
)
from app.services import audit, guidance, privacy
from app.services.common import PermissionDenied, ServiceError, iso


# ==============================================================================
# Helper functions & Citations
# ==============================================================================

def _make_citation(
    cite_id: str,
    cite_type: str,
    title: str,
    snippet: str,
    url_or_path: str = "",
    verification: str = "verified",
) -> dict[str, str]:
    return {
        "id": cite_id,
        "type": cite_type,  # APPLICATION_RECORD | DOCUMENT_WALLET | OFFICIAL_GOVERNMENT | GENERAL_GUIDANCE
        "title": title,
        "snippet": snippet,
        "url_or_path": url_or_path,
        "verification": verification,
    }


def _make_action_card(
    action_id: str,
    action_type: str,
    title: str,
    description: str,
    payload: dict[str, Any],
    button_label: str,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "action_type": action_type,  # NAVIGATE | OPEN_DOCUMENT | OPEN_CASE | CREATE_TASK | PREPARE_REPORT | INITIATE_UPLOAD
        "title": title,
        "description": description,
        "payload": payload,
        "button_label": button_label,
        "status": "proposed",
    }


# ==============================================================================
# Conversation CRUD
# ==============================================================================

def list_conversations(
    db: Session,
    user_id: str,
    status: str | None = None,
    case_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all conversations for a user with privacy boundary isolation."""
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    if status:
        stmt = stmt.where(Conversation.status == status)
    else:
        # Default active conversations
        stmt = stmt.where(Conversation.status != "deleted")
    if case_id:
        stmt = stmt.where(Conversation.case_id == case_id)

    stmt = stmt.order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at))
    convs = db.scalars(stmt).all()

    results = []
    for c in convs:
        last_msg = db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == c.id)
            .order_by(desc(ConversationMessage.sequence_number), desc(ConversationMessage.created_at))
            .limit(1)
        ).first()

        results.append({
            "id": c.id,
            "title": c.title,
            "status": c.status or "active",
            "is_pinned": c.is_pinned,
            "case_id": c.case_id,
            "ai_provider": c.ai_provider,
            "model_identifier": c.model_identifier,
            "last_message": last_msg.content[:120] if last_msg else None,
            "last_message_at": iso(c.last_message_at) or (iso(last_msg.created_at) if last_msg else iso(c.updated_at)),
            "created_at": iso(c.created_at),
            "updated_at": iso(c.updated_at),
            "archived_at": iso(c.archived_at) if c.archived_at else None,
        })
    return results


def create_conversation(
    db: Session,
    user_id: str,
    title: str | None = None,
    case_id: str | None = None,
    ai_provider: str = "gemini",
    model_identifier: str | None = None,
) -> dict[str, Any]:
    """Create a new conversation session."""
    user = db.get(User, user_id)
    if not user:
        raise ServiceError("User not found")

    cid = new_id("conv")
    now = utcnow()
    conv = Conversation(
        id=cid,
        user_id=user_id,
        case_id=case_id,
        title=(title or "New Conversation").strip()[:80],
        status="active",
        ai_provider=ai_provider,
        model_identifier=model_identifier,
        last_message_at=now,
    )
    db.add(conv)

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="create_conversation",
        resource_type="conversation",
        resource_id=cid,
        case_id=case_id,
        result_summary=f"Created conversation '{conv.title}'",
    )
    db.commit()
    db.refresh(conv)

    return {
        "id": conv.id,
        "title": conv.title,
        "status": conv.status,
        "case_id": conv.case_id,
        "ai_provider": conv.ai_provider,
        "model_identifier": conv.model_identifier,
        "is_pinned": conv.is_pinned,
        "last_message_at": iso(conv.last_message_at),
        "created_at": iso(conv.created_at),
        "updated_at": iso(conv.updated_at),
        "messages": [],
    }


def get_conversation(db: Session, user_id: str, conversation_id: str) -> dict[str, Any]:
    """Get conversation details and full ordered message history."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    messages = db.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.sequence_number.asc(), ConversationMessage.created_at.asc())
    ).all()

    msg_list = []
    for m in messages:
        cites = m.source_references_json if isinstance(m.source_references_json, list) else json.loads(m.citations_json or "[]")
        cards = json.loads(m.action_cards_json or "[]")
        followups = json.loads(m.suggested_followups_json or "[]")

        msg_list.append({
            "id": m.id,
            "sender": m.sender,
            "sender_type": m.sender_type or m.sender,
            "content": m.content,
            "content_format": m.content_format or "text",
            "sequence_number": m.sequence_number,
            "citations": cites,
            "action_cards": cards,
            "suggested_followups": followups,
            "created_at": iso(m.created_at),
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "status": conv.status or "active",
        "case_id": conv.case_id,
        "ai_provider": conv.ai_provider,
        "model_identifier": conv.model_identifier,
        "is_pinned": conv.is_pinned,
        "last_message_at": iso(conv.last_message_at),
        "created_at": iso(conv.created_at),
        "updated_at": iso(conv.updated_at),
        "archived_at": iso(conv.archived_at) if conv.archived_at else None,
        "messages": msg_list,
    }


def rename_conversation(db: Session, user_id: str, conversation_id: str, new_title: str) -> dict[str, Any]:
    """Rename a conversation."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    clean = (new_title or "").strip()[:80]
    if not clean:
        raise ServiceError("Conversation title cannot be empty")

    conv.title = clean
    conv.updated_at = utcnow()

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="rename_conversation",
        resource_type="conversation",
        resource_id=conv.id,
        result_summary=f"Renamed conversation to '{conv.title}'",
    )
    db.commit()
    return {"id": conv.id, "title": conv.title, "updated_at": iso(conv.updated_at)}


def archive_conversation(db: Session, user_id: str, conversation_id: str) -> dict[str, Any]:
    """Archive a conversation session."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    now = utcnow()
    conv.status = "archived"
    conv.archived_at = now
    conv.updated_at = now

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="archive_conversation",
        resource_type="conversation",
        resource_id=conv.id,
        result_summary=f"Archived conversation '{conv.title}'",
    )
    db.commit()
    return {"id": conv.id, "status": "archived", "archived_at": iso(now)}


def unarchive_conversation(db: Session, user_id: str, conversation_id: str) -> dict[str, Any]:
    """Restore an archived conversation to active status."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    conv.status = "active"
    conv.archived_at = None
    conv.updated_at = utcnow()
    db.commit()
    return {"id": conv.id, "status": "active", "archived_at": None}


def delete_conversation(db: Session, user_id: str, conversation_id: str) -> bool:
    """Delete a conversation and its messages."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="delete_conversation",
        resource_type="conversation",
        resource_id=conversation_id,
        result_summary=f"Deleted conversation '{conv.title}'",
    )
    db.execute(delete(ConversationMessage).where(ConversationMessage.conversation_id == conversation_id))
    db.delete(conv)
    db.commit()
    return True


def clear_conversations(db: Session, user_id: str) -> int:
    """Clear all conversations for a user."""
    conv_ids = db.scalars(select(Conversation.id).where(Conversation.user_id == user_id)).all()
    if not conv_ids:
        return 0

    db.execute(delete(ConversationMessage).where(ConversationMessage.conversation_id.in_(conv_ids)))
    count = db.execute(delete(Conversation).where(Conversation.user_id == user_id)).rowcount
    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="clear_conversations",
        resource_type="conversation",
        result_summary=f"Cleared {count} conversations",
    )
    db.commit()
    return count


def pin_conversation(db: Session, user_id: str, conversation_id: str, pinned: bool) -> dict[str, Any]:
    """Toggle pin status of conversation."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    conv.is_pinned = pinned
    conv.updated_at = utcnow()
    db.commit()
    return {"id": conv.id, "is_pinned": conv.is_pinned}


# ==============================================================================
# AI Action Logs & Supervised Approval
# ==============================================================================

def _action_log_dict(a: AIActionLog) -> dict[str, Any]:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "conversation_id": a.conversation_id,
        "case_id": a.case_id,
        "action_type": a.action_type,
        "action_description": a.action_description,
        "input_metadata": a.input_metadata or {},
        "output_metadata": a.output_metadata or {},
        "action_status": a.action_status,
        "approval_required": a.approval_required,
        "approved_by": a.approved_by,
        "approval_timestamp": iso(a.approval_timestamp) if a.approval_timestamp else None,
        "execution_timestamp": iso(a.execution_timestamp) if a.execution_timestamp else None,
        "failure_reason": a.failure_reason,
        "created_at": iso(a.created_at),
    }


def propose_action(
    db: Session,
    user_id: str,
    action_type: str,
    description: str,
    input_payload: dict[str, Any],
    conversation_id: str | None = None,
    case_id: str | None = None,
    requires_approval: bool = True,
) -> dict[str, Any]:
    """Register a proposed AI action awaiting user inspection."""
    aid = new_id("aiact")
    action = AIActionLog(
        id=aid,
        user_id=user_id,
        conversation_id=conversation_id,
        case_id=case_id,
        action_type=action_type,
        action_description=description,
        input_metadata=input_payload,
        output_metadata={},
        action_status="awaiting_approval" if requires_approval else "proposed",
        approval_required=requires_approval,
        created_at=utcnow(),
    )
    db.add(action)
    db.flush()

    audit.record_audit(
        db=db,
        actor_id=user_id,
        actor_type="ai",
        action_type="propose_ai_action",
        resource_type="ai_action",
        resource_id=aid,
        case_id=case_id,
        payload={"action_type": action_type, "requires_approval": requires_approval},
        result_summary=f"AI proposed action: {description}",
    )
    db.commit()
    return _action_log_dict(action)


def list_ai_actions(
    db: Session,
    user_id: str,
    status: str | None = None,
    case_id: str | None = None,
    conversation_id: str | None = None,
) -> list[dict[str, Any]]:
    """List AI actions proposed or executed for a user."""
    stmt = select(AIActionLog).where(AIActionLog.user_id == user_id)
    if status:
        stmt = stmt.where(AIActionLog.action_status == status)
    if case_id:
        stmt = stmt.where(AIActionLog.case_id == case_id)
    if conversation_id:
        stmt = stmt.where(AIActionLog.conversation_id == conversation_id)

    stmt = stmt.order_by(desc(AIActionLog.created_at))
    actions = db.scalars(stmt).all()
    return [_action_log_dict(a) for a in actions]


def get_action_details(db: Session, user_id: str, action_id: str) -> dict[str, Any]:
    """Retrieve details of a specific AI action."""
    action = db.get(AIActionLog, action_id)
    if not action or action.user_id != user_id:
        raise ServiceError("Action not found")
    return _action_log_dict(action)


def approve_action(
    db: Session,
    user_id: str,
    action_id: str,
    approval_notes: str = "",
) -> dict[str, Any]:
    """Human-in-the-loop approval and execution of a proposed AI action.

    Strict rules:
    - AI cannot approve its own actions.
    - Approval is bound to the exact proposed action.
    - Underlying operation must confirm success.
    """
    if user_id in ("ai", "system", "assistant", "ai_assistant_agent") or "ai" in str(user_id).lower():
        raise PermissionDenied("AI agents and automated systems are strictly forbidden from approving actions")

    action = db.get(AIActionLog, action_id)
    if not action or action.user_id != user_id:
        raise ServiceError("Action not found or unauthorized")

    if action.action_status not in ("proposed", "awaiting_approval"):
        raise ServiceError(f"Action cannot be approved from status '{action.action_status}'")

    now = utcnow()
    action.approved_by = user_id
    action.approval_timestamp = now
    action.action_status = "executing"
    db.flush()

    # Execute underlying business action
    try:
        result = execute_assistant_action(
            db=db,
            user_id=user_id,
            action_type=action.action_type,
            payload=action.input_metadata or {},
        )

        if result.get("status") == "error":
            action.action_status = "failed"
            action.failure_reason = result.get("message", "Action execution error")
        else:
            action.action_status = "completed"
            action.output_metadata = result
            action.execution_timestamp = utcnow()
            action.failure_reason = None
    except Exception as exc:
        action.action_status = "failed"
        action.failure_reason = str(exc)
        result = {"status": "error", "error": str(exc)}

    # Audit log
    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="approve_ai_action",
        resource_type="ai_action",
        resource_id=action.id,
        case_id=action.case_id,
        action_outcome="success" if action.action_status == "completed" else "failure",
        payload={"action_type": action.action_type, "result": result, "notes": approval_notes},
        result_summary=f"User approved AI action '{action.action_type}': {action.action_status}",
    )
    db.commit()
    return _action_log_dict(action)


def reject_action(
    db: Session,
    user_id: str,
    action_id: str,
    reason: str = "User dismissed proposed action",
) -> dict[str, Any]:
    """Explicitly reject a proposed action without executing it."""
    action = db.get(AIActionLog, action_id)
    if not action or action.user_id != user_id:
        raise ServiceError("Action not found")

    if action.action_status not in ("proposed", "awaiting_approval"):
        raise ServiceError(f"Action cannot be rejected from status '{action.action_status}'")

    action.action_status = "rejected"
    action.failure_reason = reason or "Rejected by user"

    audit.record_audit(
        db=db,
        actor_id=user_id,
        action_type="reject_ai_action",
        resource_type="ai_action",
        resource_id=action.id,
        case_id=action.case_id,
        action_outcome="denied",
        payload={"reason": reason},
        result_summary=f"User rejected AI action '{action.action_type}'",
    )
    db.commit()
    return _action_log_dict(action)



# ==============================================================================
# Controlled Application Tools
# ==============================================================================

def tool_get_profile(db: Session, user_id: str) -> dict[str, Any]:
    """Retrieve authenticated user's profile and readiness state."""
    user = db.get(User, user_id)
    if not user:
        return {"error": "User not found"}

    from app.services import profile as prof_svc
    prof = prof_svc.get_profile(db, user_id)
    return {
        "user_id": user.id,
        "name": user.name,
        "role_label": user.role_label,
        "email": user.email,
        "phone": user.phone,
        "preferred_language": user.preferred_language,
        "completion_percentage": prof["stats"]["completion_percentage"],
        "missing_items": prof["stats"]["missing_items"],
        "registered_vehicles_count": prof["stats"]["registered_vehicles_count"],
        "emergency_contacts_count": prof["stats"]["emergency_contacts_count"],
        "readiness_status": "Complete" if prof["stats"]["completion_percentage"] >= 75 else "Partially Prepared",
    }


def tool_get_vehicles(db: Session, user_id: str) -> list[dict[str, Any]]:
    """Retrieve user's registered vehicles and insurance statuses."""
    vehicles = db.scalars(select(Vehicle).where(Vehicle.user_id == user_id)).all()
    results = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for v in vehicles:
        ins = db.scalars(
            select(VehicleInsurancePolicy)
            .where(VehicleInsurancePolicy.vehicle_id == v.id)
            .order_by(desc(VehicleInsurancePolicy.expiry_date))
        ).first()

        days_left = None
        status = "not_provided"
        if ins and ins.expiry_date:
            days_left = (ins.expiry_date.date() - now.date()).days
            if days_left < 0:
                status = "expired"
            elif days_left <= 30:
                status = "expiring_soon"
            else:
                status = "active"

        results.append({
            "id": v.id,
            "registration_number": v.registration_number,
            "category": v.category,
            "manufacturer": v.manufacturer,
            "model": v.model,
            "variant": v.variant,
            "manufacturing_year": v.manufacturing_year,
            "fuel_type": v.fuel_type,
            "color": v.color,
            "insurance_provider": ins.provider if ins else None,
            "policy_number": ins.policy_number if ins else None,
            "insurance_expiry": iso(ins.expiry_date) if ins and ins.expiry_date else None,
            "insurance_status": status,
            "days_until_expiry": days_left,
        })
    return results


def tool_get_vehicle_detail(db: Session, user_id: str, vehicle_id_or_reg: str) -> dict[str, Any]:
    """Retrieve detailed vehicle data, documents, and policies for a specific vehicle."""
    v = db.scalars(
        select(Vehicle).where(
            Vehicle.user_id == user_id,
            or_(Vehicle.id == vehicle_id_or_reg, Vehicle.registration_number == vehicle_id_or_reg.upper().strip())
        )
    ).first()
    if not v:
        return {"error": f"No vehicle found matching '{vehicle_id_or_reg}' belonging to you."}

    ins = db.scalars(select(VehicleInsurancePolicy).where(VehicleInsurancePolicy.vehicle_id == v.id)).first()
    docs = db.scalars(select(VehicleDocument).where(VehicleDocument.vehicle_id == v.id)).all()

    return {
        "id": v.id,
        "registration_number": v.registration_number,
        "manufacturer": v.manufacturer,
        "model": v.model,
        "variant": v.variant,
        "manufacturing_year": v.manufacturing_year,
        "fuel_type": v.fuel_type,
        "chassis_number": v.chassis_number,
        "engine_number": v.engine_number,
        "insurance": {
            "provider": ins.provider if ins else None,
            "policy_number": ins.policy_number if ins else None,
            "expiry_date": iso(ins.expiry_date) if ins and ins.expiry_date else None,
        } if ins else None,
        "documents": [
            {"id": d.id, "type": d.document_type, "name": d.document_name, "expiry": iso(d.expiry_date) if d.expiry_date else None}
            for d in docs
        ],
    }


def tool_search_documents(db: Session, user_id: str, query: str = "", category: str = "") -> list[dict[str, Any]]:
    """Search user's central documents wallet."""
    stmt = select(CentralDocument).where(
        CentralDocument.user_id == user_id,
        CentralDocument.deleted_at.is_(None)
    )
    if category and category.strip():
        stmt = stmt.where(CentralDocument.category == category.strip().lower())

    docs = db.scalars(stmt).all()
    results = []
    q = query.lower().strip() if query else ""

    for d in docs:
        if q and q not in d.document_name.lower() and q not in (d.category or "").lower() and q not in (d.document_type or "").lower():
            continue
        results.append({
            "id": d.id,
            "document_name": d.document_name,
            "category": d.category,
            "document_type": d.document_type,
            "verification_status": d.verification_status,
            "document_number": d.document_number,
            "expiry_date": iso(d.expiry_date) if d.expiry_date else None,
            "resource_type": d.resource_type,
            "resource_id": d.resource_id,
        })
    return results


def tool_get_document_content(db: Session, user_id: str, document_id: str) -> dict[str, Any]:
    """Retrieve document details and extracted metadata."""
    doc = db.get(CentralDocument, document_id)
    if not doc or doc.user_id != user_id or doc.deleted_at:
        return {"error": f"Document '{document_id}' not found or access denied."}

    # Also check case documents / extracted fields if resource_id is a case
    extracted = []
    if doc.resource_type == "ACCIDENT_CASE" and doc.resource_id:
        flds = db.scalars(select(ExtractedField).where(ExtractedField.case_id == doc.resource_id)).all()
        for f in flds:
            extracted.append({"name": f.name, "value": f.value, "confidence": f.confidence, "status": f.status})

    return {
        "id": doc.id,
        "name": doc.document_name,
        "category": doc.category,
        "type": doc.document_type,
        "document_number": doc.document_number,
        "issuing_authority": doc.issuing_authority,
        "verification_status": doc.verification_status,
        "expiry_date": iso(doc.expiry_date) if doc.expiry_date else None,
        "extracted_fields": extracted,
        "file_name": doc.file_name,
    }


def tool_get_cases(db: Session, user_id: str) -> list[dict[str, Any]]:
    """Retrieve accident cases where user is creator or member."""
    # Member of case
    member_case_ids = db.scalars(select(CaseMember.case_id).where(CaseMember.user_id == user_id)).all()
    created_cases = db.scalars(select(Case.id).where(Case.created_by == user_id)).all()
    all_case_ids = list(set(member_case_ids + created_cases))

    if not all_case_ids:
        return []

    cases = db.scalars(select(Case).where(Case.id.in_(all_case_ids))).all()
    results = []
    for c in cases:
        pending_tasks = db.scalar(
            select(Task.id).where(Task.case_id == c.id, Task.status == "open")
        ) is not None

        results.append({
            "id": c.id,
            "case_number": c.case_number,
            "status": c.status,
            "incident_at": iso(c.incident_at),
            "location": c.approximate_location,
            "hospital_name": c.hospital_name,
            "hospital_treatment_status": c.hospital_treatment_status,
            "pmrahat_stage": c.pmrahat_stage,
            "police_stage": c.police_stage,
            "insurance_stage": c.insurance_stage,
            "victim_name": c.victim_display_name,
            "has_pending_tasks": pending_tasks,
        })
    return results


def tool_get_case_detail(db: Session, user_id: str, case_id: str) -> dict[str, Any]:
    """Retrieve comprehensive details of a specific accident case."""
    is_member = db.scalar(
        select(CaseMember.case_id).where(CaseMember.case_id == case_id, CaseMember.user_id == user_id)
    )
    case = db.get(Case, case_id)
    if not case:
        return {"error": "Case not found."}
    if not is_member and case.created_by != user_id:
        raise PermissionDenied("You do not have access to this case.")

    tasks = db.scalars(select(Task).where(Task.case_id == case.id, Task.status == "open")).all()

    return {
        "id": case.id,
        "case_number": case.case_number,
        "status": case.status,
        "incident_at": iso(case.incident_at),
        "location": case.approximate_location,
        "accident_type": case.accident_type,
        "victim_name": case.victim_display_name,
        "victim_relationship": case.victim_relationship,
        "injury_severity": case.injury_severity,
        "injury_description": case.injury_description,
        "hospital_name": case.hospital_name,
        "treating_doctor": case.treating_doctor,
        "hospital_treatment_status": case.hospital_treatment_status,
        "pmrahat_status": case.pmrahat_status,
        "pmrahat_stage": case.pmrahat_stage,
        "police_station": case.police_station,
        "police_stage": case.police_stage,
        "police_draft_status": case.police_draft_status,
        "fir_number": case.fir_number,
        "insurance_provider": case.insurance_provider,
        "insurance_policy_number": case.insurance_policy_number,
        "insurance_claim_number": case.insurance_claim_number,
        "insurance_stage": case.insurance_stage,
        "open_tasks": [{"id": t.id, "title": t.title, "priority": t.priority} for t in tasks],
    }


def tool_search_pmrahat_guidance(question: str) -> dict[str, Any]:
    """Search official PM-RAHAT knowledge base using BM25."""
    return guidance.search(question, k=3)


# ==============================================================================
# Action Execution Handler
# ==============================================================================

def execute_assistant_action(db: Session, user_id: str, action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute confirmed action requested by the user from an action card."""
    if action_type == "NAVIGATE":
        path = payload.get("path", "/ai-assistant")
        return {"status": "success", "message": f"Navigating to {path}", "path": path}

    elif action_type == "OPEN_DOCUMENT":
        doc_id = payload.get("document_id")
        doc = db.get(CentralDocument, doc_id)
        if not doc or doc.user_id != user_id:
            raise ServiceError("Document not accessible")
        return {"status": "success", "message": f"Opened {doc.document_name}", "path": f"/documents"}

    elif action_type == "OPEN_CASE":
        case_id = payload.get("case_id")
        case = db.get(Case, case_id)
        if not case:
            raise ServiceError("Case not found")
        return {"status": "success", "message": f"Opening case {case.case_number}", "path": f"/cases/{case.id}"}

    elif action_type == "CREATE_TASK":
        case_id = payload.get("case_id")
        title = payload.get("title", "Follow-up task")
        description = payload.get("description", "")
        priority = payload.get("priority", "medium")

        if not case_id:
            # Pick user's latest case if any
            c = db.scalars(select(Case).where(Case.created_by == user_id).limit(1)).first()
            if c:
                case_id = c.id
            else:
                return {"status": "error", "message": "No active case to attach task to."}

        new_t = Task(
            case_id=case_id,
            title=title,
            description=description,
            priority=priority,
            status="open",
            created_by=user_id,
        )
        db.add(new_t)
        db.commit()
        return {"status": "success", "message": f"Created task: {title}", "task_id": new_t.id}

    elif action_type == "PREPARE_REPORT":
        case_id = payload.get("case_id")
        return {
            "status": "success",
            "message": "Case summary package ready for review.",
            "path": f"/cases/{case_id}" if case_id else "/cases"
        }

    elif action_type == "INITIATE_UPLOAD":
        target = payload.get("target", "documents")
        return {
            "status": "success",
            "message": "Ready to upload document.",
            "path": "/documents" if target == "documents" else f"/cases/{payload.get('case_id')}"
        }

    return {"status": "error", "message": f"Unknown action type {action_type}"}


# ==============================================================================
# Grounded Context-Aware AI Engine
# ==============================================================================

def _generate_grounded_response(db: Session, user_id: str, query: str) -> dict[str, Any]:
    """Analyze user intent, call real application tools, synthesize answer with citations & action cards."""
    # 0. Check global AI data access privacy boundary
    if not privacy.check_ai_data_access(db, user_id, "general"):
        return {
            "content": (
                "> [!NOTE] **Privacy Setting Notice**\n"
                "> AI data access is currently disabled in your Profile Privacy Preferences. "
                "To receive personalized answers based on your records, please enable AI Data Access under **Profile > Privacy & Consent**."
            ),
            "citations": [],
            "action_cards": [],
            "suggested_followups": ["How do I update my privacy preferences?"],
        }

    q_lower = query.lower().strip()
    citations: list[dict[str, str]] = []
    action_cards: list[dict[str, Any]] = []
    followups: list[str] = []

    # Check category privacy permissions
    can_vehicles = privacy.check_ai_data_access(db, user_id, "vehicles")
    can_docs = privacy.check_ai_data_access(db, user_id, "documents")
    can_cases = privacy.check_ai_data_access(db, user_id, "cases")
    can_medical = privacy.check_ai_data_access(db, user_id, "medical")

    # 1. Emergency intent check
    is_emergency = any(w in q_lower for w in ["emergency", "112", "bleeding", "unconscious", "just had an accident", "ambulance", "help now", "critical"])
    emergency_callout = ""
    if is_emergency:
        emergency_callout = (
            "> [!CAUTION] **EMERGENCY NOTICE: Call 112 Immediately**\n"
            "> If you or someone at the scene is injured or in immediate danger, dial **112** for Police and Emergency Medical Services right away. "
            "Ensure the victim is moved safely off active traffic lanes if safe to do so.\n\n"
        )

    # 2. Check for vehicle queries
    vehicle_intent = any(w in q_lower for w in ["vehicle", "car", "bike", "honda", "registration", "rc", "insurance", "puc", "expiry", "expire", "policy"])
    # 3. Check for document queries
    doc_intent = any(w in q_lower for w in ["document", "wallet", "licence", "license", "dl", "bill", "medical report", "aadhaar", "pan", "rc book", "files"])
    # 4. Check for accident case queries
    case_intent = any(w in q_lower for w in ["case", "accident", "hospital", "police", "fir", "claim", "surveyor", "status", "timeline", "injury", "treatment", "doctor", "ward"])
    # 5. Check for PM-RAHAT scheme queries
    scheme_intent = any(w in q_lower for w in ["rahat", "pm-rahat", "pmrahat", "scheme", "golden hour", "cashless", "1.5 lakh", "150000", "empanelled", "eligibility", "government cover"])
    # 6. Check for medical queries
    medical_intent = any(w in q_lower for w in ["medical", "blood group", "allergy", "allergies", "chronic", "health"])

    # Handle Medical info
    medical_text = ""
    if medical_intent:
        if can_medical:
            from app.db import MedicalInformation
            med = db.scalars(select(MedicalInformation).where(MedicalInformation.user_id == user_id)).first()
            if med:
                medical_text = (
                    f"### Medical Profile\n"
                    f"- **Blood Group:** {med.blood_group or 'Not recorded'}\n"
                    f"- **Allergies:** {med.allergies or 'None reported'}\n"
                    f"- **Chronic Conditions:** {med.chronic_conditions or 'None reported'}\n\n"
                )
                citations.append(_make_citation(
                    cite_id=f"cite_med_{med.id}",
                    cite_type="APPLICATION_RECORD",
                    title="User Medical Information",
                    snippet=f"Blood group: {med.blood_group}. Allergies: {med.allergies}.",
                    url_or_path="/profile",
                    verification="verified",
                ))
            else:
                medical_text = "### Medical Profile\nNo medical details currently recorded on your profile.\n\n"
        else:
            medical_text = (
                "### Medical Profile\n"
                "*[Privacy Boundary] Medical information access is strictly disabled by default in your profile privacy preferences. "
                "Enable 'Include Medical Records' in privacy settings to allow AI assistance with medical data.*\n\n"
            )

    # If nothing specific matched, provide an intelligent overview
    if not (vehicle_intent or doc_intent or case_intent or scheme_intent or is_emergency or medical_intent):
        profile = tool_get_profile(db, user_id)
        vehicles = tool_get_vehicles(db, user_id) if can_vehicles else []
        cases = tool_get_cases(db, user_id) if can_cases else []
        docs = tool_search_documents(db, user_id) if can_docs else []

        v_summary = f"{len(vehicles)} vehicle(s)" if can_vehicles else "Hidden by privacy setting"
        c_summary = f"{len(cases)} case(s)" if can_cases else "Hidden by privacy setting"
        d_summary = f"{len(docs)} document(s)" if can_docs else "Hidden by privacy setting"

        text = (
            f"Hello **{profile.get('name', 'there')}**! I am your Second Hour assistant, connected to your preparedness records, documents, and cases.\n\n"
            f"### Quick Overview of Your Profile\n"
            f"- **Readiness Status:** {profile.get('readiness_status', 'Partially Prepared')}\n"
            f"- **Vehicles:** {v_summary}\n"
            f"- **Accident Cases:** {c_summary}\n"
            f"- **Document Wallet:** {d_summary}\n\n"
            f"You can ask me to check your insurance expiry, review documents, guide you through PM-RAHAT cashless assistance, or track case progress.\n\n"
            f"*(In case of a life-threatening emergency on the road, always dial **112** immediately.)*"
        )

        followups = [
            "Check my vehicle insurance status",
            "What documents are in my wallet?",
            "How does PM-RAHAT cashless cover work?",
            "What is the status of my accident case?",
        ]
        return {
            "content": text,
            "citations": citations,
            "action_cards": action_cards,
            "suggested_followups": followups,
        }

    # Handle Scheme queries
    scheme_text = ""
    if scheme_intent:
        rag_res = tool_search_pmrahat_guidance(query)
        if rag_res.get("found") and rag_res.get("results"):
            top = rag_res["results"][0]
            src = top.get("source", {})
            citations.append(_make_citation(
                cite_id=f"cite_pmrahat_{len(citations)+1}",
                cite_type="OFFICIAL_GOVERNMENT",
                title=f"{src.get('title', 'PM-RAHAT Official Guidance')} ({src.get('publisher', 'MoRTH')})",
                snippet=top.get("snippet", "")[:280] + "...",
                url_or_path=src.get("url", "https://morth.nic.in"),
                verification=src.get("verification", "verified"),
            ))
            scheme_text += (
                f"### PM-RAHAT Scheme Guidance\n"
                f"Under the **PM-RAHAT Scheme** notified by the Ministry of Road Transport & Highways (MoRTH):\n"
                f"- **Cashless Treatment Limit:** Up to **₹1,50,000** per victim per accident.\n"
                f"- **Golden Hour Coverage:** Eligible for the first **7 days** from the time of the road accident.\n"
                f"- **No Pre-payment:** Empanelled trauma care hospitals are mandated by central guidelines to provide immediate stabilization without demanding upfront cash deposit.\n"
                f"- **Police Authentication:** The treating hospital intimates local police to issue a verification report for clearing scheme settlement.\n\n"
                f"> **Official Source:** [{src.get('title', 'MoRTH Scheme Guidelines')}]({src.get('url', '#')}) · PIB & MoRTH verified.\n\n"
            )
        else:
            scheme_text += (
                f"### PM-RAHAT Cashless Assistance\n"
                f"The **PM-RAHAT Scheme** provides cashless trauma stabilization up to **₹1,50,000** for road accident victims for up to **7 days**.\n\n"
            )

    # Handle Vehicles queries
    vehicle_text = ""
    if vehicle_intent:
        if not can_vehicles:
            vehicle_text += "### Registered Vehicles & Insurance\n*[Privacy Boundary] Vehicle data access is disabled in your privacy settings.*\n\n"
        else:
            vehicles = tool_get_vehicles(db, user_id)
            if vehicles:
                vehicle_text += "### Your Registered Vehicles & Insurance\n"
                for v in vehicles:
                    ins_badge = v['insurance_status'].replace('_', ' ').title()
                    days_txt = f"({v['days_until_expiry']} days remaining)" if v['days_until_expiry'] is not None and v['days_until_expiry'] >= 0 else "(Expired)"
                    vehicle_text += (
                        f"- **{v['manufacturer']} {v['model']} ({v['registration_number']})**\n"
                        f"  - Insurance Provider: **{v['insurance_provider'] or 'Not Provided'}**\n"
                        f"  - Policy Number: `{v['policy_number'] or 'N/A'}`\n"
                        f"  - Policy Expiry: **{v['insurance_expiry'] or 'N/A'}** {days_txt} · Status: `{ins_badge}`\n"
                        f"  - Fuel & Year: {v['fuel_type']} · {v['manufacturing_year']}\n\n"
                    )
                    citations.append(_make_citation(
                        cite_id=f"cite_veh_{v['id']}",
                        cite_type="APPLICATION_RECORD",
                        title=f"Vehicle Record: {v['registration_number']} ({v['manufacturer']} {v['model']})",
                        snippet=f"Policy {v['policy_number']} with {v['insurance_provider']}, valid until {v['insurance_expiry']}.",
                        url_or_path=f"/vehicles/{v['id']}",
                        verification="verified",
                    ))
                    action_cards.append(_make_action_card(
                        action_id=f"act_veh_{v['id']}",
                        action_type="NAVIGATE",
                        title=f"Manage {v['registration_number']}",
                        description=f"View full vehicle specifications, policy details, and attached RC & PUC files.",
                        payload={"path": f"/vehicles/{v['id']}"},
                        button_label="View Vehicle Details",
                    ))
            else:
                vehicle_text += (
                    "### Registered Vehicles\n"
                    "You have no registered vehicles in your account currently. You can add your car or two-wheeler to keep its RC, PUC, and Insurance policy organized.\n\n"
                )
                action_cards.append(_make_action_card(
                    action_id="act_add_veh",
                    action_type="NAVIGATE",
                    title="Add a Vehicle",
                    description="Register your vehicle to track insurance expiry reminders and centralize documents.",
                    payload={"path": "/vehicles"},
                    button_label="Go to My Vehicles",
                ))

    # Handle Documents queries
    doc_text = ""
    if doc_intent:
        if not can_docs:
            doc_text += "### Document Wallet\n*[Privacy Boundary] Document wallet access is disabled in your privacy settings.*\n\n"
        else:
            docs = tool_search_documents(db, user_id)
            if not can_medical:
                docs = [d for d in docs if (d.get("category") or "").lower() != "medical"]
            if docs:
                doc_text += f"### Your Document Wallet ({len(docs)} documents found)\n"
                for d in docs[:5]:
                    cat = (d['category'] or 'general').title()
                    exp = f"· Expiry: {d['expiry_date']}" if d.get('expiry_date') else ""
                    doc_text += f"- **{d['document_name']}** (`{cat}`) — Status: `{d['verification_status']}` {exp}\n"
                    citations.append(_make_citation(
                        cite_id=f"cite_doc_{d['id']}",
                        cite_type="DOCUMENT_WALLET",
                        title=f"Document: {d['document_name']} ({cat})",
                        snippet=f"Document #{d.get('document_number') or 'N/A'} · Verified in Document Wallet.",
                        url_or_path="/documents",
                        verification="user_record",
                    ))
                doc_text += "\n"
                action_cards.append(_make_action_card(
                    action_id="act_open_docs",
                    action_type="NAVIGATE",
                    title="Open Document Wallet",
                    description="Browse, filter, preview and download all personal, vehicle, and accident records.",
                    payload={"path": "/documents"},
                    button_label="Open Document Wallet",
                ))
            else:
                doc_text += (
                    "### Document Wallet\n"
                    "You currently have no documents uploaded in your Document Wallet. You can upload Driving Licences, Medical Bills, RC, and Insurance cards.\n\n"
                )
                action_cards.append(_make_action_card(
                    action_id="act_upload_doc",
                    action_type="INITIATE_UPLOAD",
                    title="Upload Document",
                    description="Add an important document (PDF, PNG, JPG) to your secure wallet.",
                    payload={"target": "documents"},
                    button_label="Upload New Document",
                ))

    # Handle Case queries
    case_text = ""
    if case_intent:
        if not can_cases:
            case_text += "### Accident Cases\n*[Privacy Boundary] Case records access is disabled in your privacy settings.*\n\n"
        else:
            cases = tool_get_cases(db, user_id)
            if cases:
                case_text += "### Active Accident Cases\n"
                for c in cases:
                    case_detail = tool_get_case_detail(db, user_id, c['id'])
                    case_text += (
                        f"- **Case #{c['case_number']}** at **{c['location']}**\n"
                        f"  - **Hospitalization:** {c['hospital_name'] or 'N/A'} · Treatment: `{c['hospital_treatment_status']}`\n"
                        f"  - **PM-RAHAT Status:** `{c['pmrahat_stage']}`\n"
                        f"  - **Police Documentation:** `{c['police_stage']}` (Draft: `{case_detail.get('police_draft_status')}`)\n"
                        f"  - **Insurance Claim:** `{c['insurance_stage']}`\n"
                    )
                    if case_detail.get('open_tasks'):
                        t_titles = [f"`{t['title']}`" for t in case_detail['open_tasks'][:2]]
                        case_text += f"  - **Pending Actions:** {', '.join(t_titles)}\n"

                    case_text += "\n"

                    citations.append(_make_citation(
                        cite_id=f"cite_case_{c['id']}",
                        cite_type="APPLICATION_RECORD",
                        title=f"Accident Case Record: {c['case_number']}",
                        snippet=f"Incident at {c['location']} on {c['incident_at']}. Hospital: {c['hospital_name']}.",
                        url_or_path=f"/cases/{c['id']}",
                        verification="verified",
                    ))
                    action_cards.append(_make_action_card(
                        action_id=f"act_case_{c['id']}",
                        action_type="OPEN_CASE",
                        title=f"Open Workspace for {c['case_number']}",
                        description=f"Manage timeline, hospital liaison, police draft approval, and evidence package.",
                        payload={"case_id": c['id']},
                        button_label="Open Case Workspace",
                    ))
            else:
                case_text += (
                    "### Accident Case Tracking\n"
                    "You do not have any open accident cases recorded under your account. If an accident recently occurred, you can report it from the homepage.\n\n"
                )

    # Assemble response content
    content_blocks = [emergency_callout, scheme_text, medical_text, case_text, vehicle_text, doc_text]
    full_content = "\n".join(b for b in content_blocks if b.strip()).strip()

    # Generate smart follow-up suggestions
    if case_intent:
        followups = [
            "What is the next step for police draft verification?",
            "How do I submit hospital bills to the insurance surveyor?",
            "Can I generate a consolidated PDF case report?",
        ]
    elif vehicle_intent:
        followups = [
            "Show me the policy details for my car",
            "What documents are required to renew vehicle insurance?",
            "How do I upload a renewed PUC certificate?",
        ]
    elif scheme_intent:
        followups = [
            "Does PM-RAHAT cover private empanelled hospitals?",
            "What happens if treatment exceeds ₹1.5 lakh?",
            "What documents are needed for PM-RAHAT hospital clearance?",
        ]
    else:
        followups = [
            "What should I do immediately after an accident?",
            "Check my vehicle documents",
            "Show me PM-RAHAT scheme benefits",
        ]

    return {
        "content": full_content,
        "citations": citations,
        "action_cards": action_cards,
        "suggested_followups": followups,
    }


def post_user_message(db: Session, user_id: str, conversation_id: str, user_text: str) -> dict[str, Any]:
    """Record user message, execute reasoning & application tools, and return response."""
    user = db.get(User, user_id)
    if not user:
        raise ServiceError("User not found")

    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ServiceError("Conversation not found")
    if conv.user_id != user_id:
        raise PermissionDenied("You do not have access to this conversation")

    clean_text = user_text.strip()
    if not clean_text:
        raise ServiceError("Message cannot be empty")

    now = utcnow()
    # Compute sequence numbers
    max_seq = db.scalar(
        select(func.coalesce(func.max(ConversationMessage.sequence_number), 0))
        .where(ConversationMessage.conversation_id == conversation_id)
    ) or 0
    user_seq = max_seq + 1
    asst_seq = max_seq + 2

    # 1. Save user message
    user_msg = ConversationMessage(
        id=new_id("cmsg"),
        conversation_id=conversation_id,
        sender="user",
        sender_type="user",
        content=clean_text,
        content_format="text",
        sequence_number=user_seq,
        created_at=now,
    )
    db.add(user_msg)

    # 2. Update conversation title if default
    if conv.title in ("New Conversation", "New Chat", ""):
        conv.title = clean_text[:40].replace("\n", " ").strip()
    conv.last_message_at = now
    conv.updated_at = now
    db.flush()

    # 3. Generate grounded context-aware response
    response_data = _generate_grounded_response(db, user_id, clean_text)

    # 4. Register action cards in AIActionLog for supervised execution
    registered_cards = []
    for card in response_data.get("action_cards", []):
        act_id = new_id("aiact")
        action_log = AIActionLog(
            id=act_id,
            user_id=user_id,
            conversation_id=conversation_id,
            case_id=conv.case_id or card.get("payload", {}).get("case_id"),
            action_type=card.get("action_type", "NAVIGATE"),
            action_description=card.get("description", card.get("title", "")),
            input_metadata=card.get("payload", {}),
            output_metadata={},
            action_status="awaiting_approval",
            approval_required=True,
            created_at=utcnow(),
        )
        db.add(action_log)
        c_dict = dict(card)
        c_dict["action_log_id"] = act_id
        registered_cards.append(c_dict)

    # 5. Save assistant message
    asst_msg = ConversationMessage(
        id=new_id("cmsg"),
        conversation_id=conversation_id,
        sender="assistant",
        sender_type="assistant",
        content=response_data["content"],
        content_format="markdown",
        sequence_number=asst_seq,
        source_references_json=response_data.get("citations", []),
        citations_json=json.dumps(response_data.get("citations", [])),
        action_cards_json=json.dumps(registered_cards),
        suggested_followups_json=json.dumps(response_data.get("suggested_followups", [])),
        ai_model_metadata={
            "provider": conv.ai_provider or "gemini",
            "model": conv.model_identifier or "gemini-1.5-flash",
        },
        token_usage_metadata={
            "prompt_tokens": max(1, len(clean_text) // 4),
            "completion_tokens": max(1, len(response_data["content"]) // 4),
            "total_tokens": max(2, (len(clean_text) + len(response_data["content"])) // 4),
        },
        created_at=utcnow(),
    )
    db.add(asst_msg)
    conv.last_message_at = utcnow()
    conv.updated_at = utcnow()

    # 6. Audit log entry
    audit.record_audit(
        db=db,
        actor_id=user_id,
        actor_type="user",
        action_type="send_ai_message",
        resource_type="conversation",
        resource_id=conversation_id,
        case_id=conv.case_id,
        result_summary=f"Sent message in conversation '{conv.title}'",
    )

    db.commit()

    return {
        "id": asst_msg.id,
        "conversation_id": conversation_id,
        "sender": "assistant",
        "sender_type": "assistant",
        "content": asst_msg.content,
        "sequence_number": asst_msg.sequence_number,
        "citations": response_data.get("citations", []),
        "action_cards": registered_cards,
        "suggested_followups": response_data.get("suggested_followups", []),
        "created_at": iso(asst_msg.created_at),
        "conversation_title": conv.title,
    }
