"""Phase 5: Centralized Append-Only Audit Logging Service.

Provides immutable security and operational audit logging across Second Hour domains:
- Authentication & Profile mutations
- Medical record access & privacy modifications
- Vehicle and Document uploads, downloads, and verifications
- Accident Case creation, evidence uploads, and status transitions
- Report generation, versioning, and formal coordinator approvals
- Motor Insurance claim lodgement and status transitions
- External statutory submissions and receipts
- AI conversation messages and supervised tool/action approvals
- Consent grants, renewals, and revocations

Strictly redacts sensitive authentication credentials, passwords, raw tokens, and API keys.
Audit records cannot be modified or deleted through ordinary application APIs.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import AuditLog, User, utcnow
from app.services.common import iso

REDACTED_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "cookies",
    "jwt",
    "bearer",
    "session",
    "credit_card",
    "cvv",
}


def _sanitize_dict(data: Any, depth: int = 0) -> Any:
    """Recursively redact sensitive credentials and scrub sensitive tokens."""
    if depth > 5:
        return "<depth_limit_exceeded>"

    if isinstance(data, dict):
        clean = {}
        for k, v in data.items():
            if str(k).lower() in REDACTED_KEYS:
                clean[k] = "[REDACTED]"
            elif any(s in str(k).lower() for s in ("password", "secret", "auth_token")):
                clean[k] = "[REDACTED]"
            else:
                clean[k] = _sanitize_dict(v, depth + 1)
        return clean
    elif isinstance(data, (list, tuple, set)):
        return [_sanitize_dict(item, depth + 1) for item in data]
    return data


def _audit_dict(a: AuditLog) -> dict[str, Any]:
    return {
        "id": a.id,
        "case_id": a.case_id,
        "actor_id": a.actor_id,
        "actor_type": a.actor_type or "user",
        "action_type": a.action_type or (a.tool or "action"),
        "resource_type": a.resource_type or "general",
        "resource_id": a.resource_id,
        "action_outcome": a.action_outcome or "success",
        "result_summary": a.result_summary or "",
        "approval_state": a.approval_state or "standard",
        "request_id": a.request_id,
        "metadata": a.sanitized_metadata or {},
        "timestamp": iso(a.at),
    }


def record_audit(
    db: Session,
    actor_id: str | None,
    action_type: str,
    resource_type: str,
    resource_id: str | None = None,
    case_id: str | None = None,
    actor_type: str = "user",
    action_outcome: str = "success",
    payload: dict[str, Any] | None = None,
    result_summary: str = "",
    approval_state: str = "standard",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create an append-only audit log entry with automatic credential sanitization."""
    sanitized_meta = _sanitize_dict(payload or {})

    summary = (result_summary or f"{action_type} on {resource_type}").strip()[:500]

    log_entry = AuditLog(
        case_id=case_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        tool=action_type,
        arguments_json=json.dumps(sanitized_meta) if sanitized_meta else "{}",
        result_summary=summary,
        action_outcome=action_outcome,
        approval_state=approval_state,
        request_id=request_id,
        sanitized_metadata=sanitized_meta,
        at=utcnow(),
    )
    db.add(log_entry)
    db.flush()

    return _audit_dict(log_entry)


def list_audit_logs(
    db: Session,
    actor_id: str | None = None,
    case_id: str | None = None,
    resource_type: str | None = None,
    action_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Retrieve audit logs with optional filtering. Append-only, read-only."""
    stmt = select(AuditLog)

    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if case_id:
        stmt = stmt.where(AuditLog.case_id == case_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if action_type:
        stmt = stmt.where(AuditLog.action_type == action_type)

    stmt = stmt.order_by(desc(AuditLog.id)).limit(min(limit, 200)).offset(offset)
    logs = db.scalars(stmt).all()
    return [_audit_dict(l) for l in logs]
