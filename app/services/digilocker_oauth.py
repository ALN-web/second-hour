"""DigiLocker OAuth 2.0 PKCE Integration and Encrypted Token Management Service.

Implements:
1. Cryptographically secure OAuth state generation and validation (single-use, user-bound, expiring).
2. Proof Key for Code Exchange (PKCE) using RFC 7636 S256 challenge/verifier.
3. Authenticated encryption of PKCE verifiers and tokens at rest via Fernet.
4. Authorization code exchange with provider error and denial handling.
5. Concurrent-safe token lifecycle and refresh synchronization.
6. Central audit logging across all OAuth lifecycle events.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import (
    ConsentRecord,
    DigiLockerOAuthState,
    User,
    UserDigiLockerConnection,
    VerificationRecord,
    new_id,
    utcnow,
)
from app.encryption import decrypt_token, encrypt_token
from app.services.audit import record_audit
from app.services.common import PermissionDenied, ServiceError, iso
from app.services.verification import ProviderTrustMode, get_provider_mode

logger = logging.getLogger("secondhour.digilocker_oauth")

OAUTH_STATE_EXPIRY_MINUTES = 15
PROVIDER_TIMEOUT_SECONDS = 15


def _normalize_dt(dt: datetime | None) -> datetime:
    """Ensure datetime is offset-naive UTC for dialect-independent comparisons."""
    if dt is None:
        return datetime.min
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _mask_identifier(val: str | None) -> str:
    """Sanitize and mask provider IDs and account numbers for presentation."""
    if not val:
        return "Not available"
    clean = str(val).strip()
    if len(clean) <= 6:
        return f"****{clean[-2:]}" if len(clean) >= 2 else "****"
    return f"{clean[:3]}****{clean[-4:]}"


def generate_pkce_pair() -> tuple[str, str]:
    """Generate high-entropy PKCE code_verifier and corresponding S256 code_challenge.

    Returns:
        tuple[str, str]: (code_verifier, code_challenge)
    """
    # 64 random bytes -> 86 URL-safe characters (RFC 7636 Section 4.1 specifies 43-128 chars)
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def initiate_oauth_flow(
    db: Session,
    user_id: str,
    redirect_uri: str | None = None,
    doc_type: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Initiate DigiLocker OAuth 2.0 PKCE flow, persisting secure state and encrypted verifier.

    Returns:
        dict containing auth_url, state, expires_in, provider.
        NEVER returns code_verifier!
    """
    user = db.get(User, user_id)
    if not user:
        raise ServiceError("User not found")

    verifier, challenge = generate_pkce_pair()
    encrypted_verifier = encrypt_token(verifier)
    state = secrets.token_urlsafe(32)
    effective_redirect_uri = (redirect_uri or config.DIGILOCKER_REDIRECT_URI).strip()
    expires_at = utcnow() + timedelta(minutes=OAUTH_STATE_EXPIRY_MINUTES)

    state_rec = DigiLockerOAuthState(
        id=new_id("dstate"),
        user_id=user_id,
        state=state,
        encrypted_code_verifier=encrypted_verifier,
        code_challenge=challenge,
        code_challenge_method="S256",
        redirect_uri=effective_redirect_uri,
        doc_type=doc_type,
        is_consumed=False,
        expires_at=expires_at,
        created_at=utcnow(),
    )
    db.add(state_rec)

    # Central audit log
    record_audit(
        db=db,
        actor_id=user_id,
        action_type="digilocker_oauth_initiated",
        resource_type="oauth_session",
        resource_id=state_rec.id,
        action_outcome="success",
        result_summary=f"Initiated DigiLocker OAuth flow with S256 PKCE for {doc_type or 'all'}",
        payload={"doc_type": doc_type, "redirect_uri": effective_redirect_uri, "expires_in": OAUTH_STATE_EXPIRY_MINUTES * 60},
    )
    db.commit()

    # Construct authorization URL
    params = {
        "response_type": "code",
        "client_id": config.DIGILOCKER_CLIENT_ID or "secondhour_client",
        "redirect_uri": effective_redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": config.DIGILOCKER_SCOPES,
    }
    auth_base = config.DIGILOCKER_AUTH_URL
    query_string = urllib.parse.urlencode(params)
    auth_url = f"{auth_base}?{query_string}"

    return {
        "auth_url": auth_url,
        "state": state,
        "provider": "DIGILOCKER",
        "expires_in": OAUTH_STATE_EXPIRY_MINUTES * 60,
    }


def handle_oauth_callback(
    db: Session,
    authenticated_user_id: str,
    state: str,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Validate OAuth callback, enforce single-use state and user binding, and exchange code for tokens.

    Guarantees:
    - State is strictly bound to the authenticated user session.
    - Missing, mismatched, expired, or reused state is rejected.
    - PKCE code_verifier is decrypted server-side and exchanged.
    - Tokens are encrypted at rest with server-managed key.
    - Tokens are NEVER returned to frontend or logged.
    """
    if not state or not state.strip():
        raise ServiceError("Missing OAuth state parameter in callback.")

    # Concurrency-safe state lookup with row lock
    state_rec = db.scalars(
        select(DigiLockerOAuthState).where(DigiLockerOAuthState.state == state.strip()).with_for_update()
    ).first()

    if not state_rec:
        raise ServiceError("Invalid OAuth state: state token not recognized.")

    # Verify user binding
    if state_rec.user_id != authenticated_user_id:
        record_audit(
            db=db,
            actor_id=authenticated_user_id,
            action_type="digilocker_oauth_state_mismatch",
            resource_type="oauth_session",
            resource_id=state_rec.id,
            action_outcome="failure",
            result_summary="OAuth state rejected: state was generated by a different user session",
        )
        db.commit()
        raise PermissionDenied("OAuth state mismatch: state was generated by a different user session.")

    # Enforce single-use
    if state_rec.is_consumed:
        record_audit(
            db=db,
            actor_id=authenticated_user_id,
            action_type="digilocker_oauth_state_reused",
            resource_type="oauth_session",
            resource_id=state_rec.id,
            action_outcome="failure",
            result_summary="OAuth state rejected: single-use violation (state already consumed)",
        )
        db.commit()
        raise ServiceError("OAuth state has already been consumed. Please initiate a new authorization request.")

    # Check expiration
    if _normalize_dt(state_rec.expires_at) < _normalize_dt(utcnow()):
        state_rec.is_consumed = True
        state_rec.consumed_at = utcnow()
        db.commit()
        raise ServiceError("OAuth state has expired. Please initiate a new authorization request.")

    # Mark state as consumed immediately to prevent replay
    state_rec.is_consumed = True
    state_rec.consumed_at = utcnow()

    # Handle provider authorization denial
    if error:
        err_msg = error_description or error
        record_audit(
            db=db,
            actor_id=authenticated_user_id,
            action_type="digilocker_oauth_denied",
            resource_type="oauth_session",
            resource_id=state_rec.id,
            action_outcome="failure",
            result_summary=f"DigiLocker authorization denied: {err_msg}",
            payload={"error": error, "error_description": error_description},
        )
        db.commit()
        raise ServiceError(f"DigiLocker authorization denied by provider or user: {err_msg}")

    if not code or not code.strip():
        db.commit()
        raise ServiceError("Missing authorization code in DigiLocker callback.")

    # Retrieve and decrypt the original PKCE code_verifier
    try:
        code_verifier = decrypt_token(state_rec.encrypted_code_verifier)
    except Exception as exc:
        logger.error("Failed to decrypt PKCE code_verifier for state %s: %s", state_rec.id, exc)
        db.commit()
        raise ServiceError("Failed to decrypt PKCE code verifier for token exchange.") from exc

    # Perform token exchange
    mode = get_provider_mode()
    access_token = ""
    refresh_token = None
    digilocker_id = ""
    expires_in = 3600
    scope = config.DIGILOCKER_SCOPES

    if mode == ProviderTrustMode.PRODUCTION:
        if not config.DIGILOCKER_CLIENT_ID or not config.DIGILOCKER_CLIENT_SECRET:
            db.commit()
            raise ServiceError("Missing production DigiLocker credentials. Token exchange cannot proceed.")

        token_payload = {
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": config.DIGILOCKER_CLIENT_ID,
            "client_secret": config.DIGILOCKER_CLIENT_SECRET,
            "redirect_uri": state_rec.redirect_uri,
            "code_verifier": code_verifier,
        }

        try:
            resp = httpx.post(
                config.DIGILOCKER_TOKEN_URL,
                data=token_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=PROVIDER_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            db.commit()
            logger.error("DigiLocker token exchange timed out: %s", exc)
            raise ServiceError("DigiLocker token exchange timed out. Please retry.") from exc
        except Exception as exc:
            db.commit()
            logger.error("DigiLocker token exchange network failure: %s", exc)
            raise ServiceError("Failed to connect to DigiLocker token endpoint.") from exc

        if resp.status_code != 200:
            db.commit()
            logger.error("DigiLocker token exchange failed with HTTP %s: %s", resp.status_code, resp.text[:200])
            raise ServiceError(f"DigiLocker token exchange failed (HTTP {resp.status_code}).")

        try:
            token_data = resp.json()
        except Exception as exc:
            db.commit()
            raise ServiceError("DigiLocker returned a malformed non-JSON token response.") from exc

        access_token = token_data.get("access_token")
        if not access_token:
            db.commit()
            raise ServiceError("DigiLocker token response did not contain an access_token.")

        refresh_token = token_data.get("refresh_token")
        digilocker_id = str(token_data.get("digilockerid") or token_data.get("sub") or "")
        expires_in = int(token_data.get("expires_in") or 3600)
        scope = token_data.get("scope") or scope

    else:
        # MOCK or SANDBOX mode: simulated tokens for non-production environments
        access_token = f"sim_{mode.lower()}_access_{uuid4().hex}"
        refresh_token = f"sim_{mode.lower()}_refresh_{uuid4().hex}"
        digilocker_id = f"DL-{mode[:3]}-{authenticated_user_id[:8].upper()}"
        expires_in = 3600

    # Encrypt tokens before database persistence
    encrypted_at = encrypt_token(access_token)
    encrypted_rt = encrypt_token(refresh_token) if refresh_token else None
    token_expiry = utcnow() + timedelta(seconds=expires_in)

    # Persist or update user_digilocker_connections atomically
    conn = db.scalars(
        select(UserDigiLockerConnection)
        .where(UserDigiLockerConnection.user_id == authenticated_user_id)
        .with_for_update()
    ).first()

    if conn:
        conn.digilocker_id = digilocker_id
        conn.encrypted_access_token = encrypted_at
        conn.encrypted_refresh_token = encrypted_rt
        conn.token_scope = scope
        conn.token_type = "Bearer"
        conn.access_token_expires_at = token_expiry
        conn.connection_status = "connected"
        conn.connected_at = utcnow()
        conn.disconnected_at = None
        conn.updated_at = utcnow()
    else:
        conn = UserDigiLockerConnection(
            id=new_id("dconn"),
            user_id=authenticated_user_id,
            digilocker_id=digilocker_id,
            encrypted_access_token=encrypted_at,
            encrypted_refresh_token=encrypted_rt,
            token_scope=scope,
            token_type="Bearer",
            access_token_expires_at=token_expiry,
            connection_status="connected",
            connected_at=utcnow(),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(conn)

    # Audit log connection event
    record_audit(
        db=db,
        actor_id=authenticated_user_id,
        action_type="digilocker_oauth_connected",
        resource_type="digilocker_connection",
        resource_id=conn.id,
        action_outcome="success",
        result_summary=f"Successfully connected DigiLocker account (ID: {_mask_identifier(digilocker_id)})",
        payload={
            "trust_mode": mode,
            "digilocker_id_masked": _mask_identifier(digilocker_id),
            "expires_in_seconds": expires_in,
            "has_refresh_token": bool(refresh_token),
        },
    )
    db.commit()

    return {
        "status": "connected",
        "connection_status": "connected",
        "digilocker_id": _mask_identifier(digilocker_id),
        "connected_at": iso(conn.connected_at),
        "expires_at": iso(token_expiry),
        "trust_mode": mode,
        "message": "DigiLocker account connected successfully. You can now verify documents with official records.",
    }


def get_connection_status(db: Session, user_id: str) -> dict[str, Any]:
    """Retrieve connection status and masked metadata for the authenticated user.

    NEVER returns raw access or refresh tokens!
    """
    conn = db.scalars(
        select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_id)
    ).first()

    if not conn or conn.connection_status != "connected":
        return {
            "is_connected": False,
            "connection_status": conn.connection_status if conn else "not_connected",
            "digilocker_id_masked": None,
            "connected_at": None,
            "expires_at": None,
            "is_expired": False,
        }

    is_expired = False
    if conn.access_token_expires_at:
        is_expired = _normalize_dt(conn.access_token_expires_at) < _normalize_dt(utcnow())

    return {
        "is_connected": True and not is_expired,
        "connection_status": "expired" if is_expired else conn.connection_status,
        "digilocker_id_masked": _mask_identifier(conn.digilocker_id),
        "connected_at": iso(conn.connected_at),
        "expires_at": iso(conn.access_token_expires_at) if conn.access_token_expires_at else None,
        "is_expired": is_expired,
    }


def disconnect_connection(db: Session, user_id: str) -> dict[str, Any]:
    """Disconnect DigiLocker account, attempt token revocation if supported, and clear stored tokens."""
    conn = db.scalars(
        select(UserDigiLockerConnection)
        .where(UserDigiLockerConnection.user_id == user_id)
        .with_for_update()
    ).first()

    if not conn or conn.connection_status == "disconnected":
        return {
            "status": "disconnected",
            "connection_status": "disconnected",
            "message": "DigiLocker account is not connected.",
        }

    # Best-effort token revocation in PRODUCTION mode
    mode = get_provider_mode()
    if mode == ProviderTrustMode.PRODUCTION and conn.encrypted_access_token:
        try:
            token = decrypt_token(conn.encrypted_access_token)
            httpx.post(
                config.DIGILOCKER_REVOKE_URL,
                data={
                    "token": token,
                    "client_id": config.DIGILOCKER_CLIENT_ID,
                    "client_secret": config.DIGILOCKER_CLIENT_SECRET,
                },
                timeout=5,
            )
        except Exception as exc:
            logger.warning("DigiLocker token revocation call failed (ignored): %s", exc)

    # Invalidate connection and scrub tokens
    conn.connection_status = "disconnected"
    conn.disconnected_at = utcnow()
    conn.encrypted_access_token = ""
    conn.encrypted_refresh_token = None
    conn.updated_at = utcnow()

    record_audit(
        db=db,
        actor_id=user_id,
        action_type="digilocker_oauth_disconnected",
        resource_type="digilocker_connection",
        resource_id=conn.id,
        action_outcome="success",
        result_summary="User disconnected DigiLocker account and revoked local credentials",
    )
    db.commit()

    return {
        "status": "disconnected",
        "connection_status": "disconnected",
        "message": "DigiLocker account disconnected successfully.",
    }


def refresh_digilocker_token(db: Session, user_id: str) -> dict[str, Any]:
    """Concurrently safe token refresh routine using row-level locking.

    Prevents concurrent token refresh race conditions.
    """
    conn = db.scalars(
        select(UserDigiLockerConnection)
        .where(UserDigiLockerConnection.user_id == user_id)
        .with_for_update()
    ).first()

    if not conn or conn.connection_status != "connected":
        raise ServiceError("No active DigiLocker connection found to refresh.")

    if not conn.encrypted_refresh_token:
        raise ServiceError("No refresh token available for this DigiLocker connection.")

    try:
        raw_refresh_token = decrypt_token(conn.encrypted_refresh_token)
    except Exception as exc:
        raise ServiceError("Failed to decrypt stored refresh token.") from exc

    mode = get_provider_mode()
    new_access_token = ""
    new_refresh_token = raw_refresh_token
    expires_in = 3600

    if mode == ProviderTrustMode.PRODUCTION:
        if not config.DIGILOCKER_CLIENT_ID or not config.DIGILOCKER_CLIENT_SECRET:
            raise ServiceError("Missing production credentials for DigiLocker token refresh.")

        refresh_payload = {
            "grant_type": "refresh_token",
            "refresh_token": raw_refresh_token,
            "client_id": config.DIGILOCKER_CLIENT_ID,
            "client_secret": config.DIGILOCKER_CLIENT_SECRET,
        }

        try:
            resp = httpx.post(
                config.DIGILOCKER_TOKEN_URL,
                data=refresh_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=PROVIDER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise ServiceError("Failed to connect to DigiLocker token endpoint for refresh.") from exc

        if resp.status_code != 200:
            conn.connection_status = "expired"
            conn.updated_at = utcnow()
            db.commit()
            raise ServiceError(f"DigiLocker token refresh rejected by provider (HTTP {resp.status_code}).")

        try:
            data = resp.json()
        except Exception as exc:
            raise ServiceError("DigiLocker returned malformed JSON during token refresh.") from exc

        new_access_token = data.get("access_token")
        if not new_access_token:
            raise ServiceError("Token refresh response missing access_token.")
        if data.get("refresh_token"):
            new_refresh_token = data["refresh_token"]
        expires_in = int(data.get("expires_in") or 3600)
    else:
        new_access_token = f"sim_{mode.lower()}_refreshed_{uuid4().hex}"
        expires_in = 3600

    conn.encrypted_access_token = encrypt_token(new_access_token)
    if new_refresh_token:
        conn.encrypted_refresh_token = encrypt_token(new_refresh_token)
    conn.access_token_expires_at = utcnow() + timedelta(seconds=expires_in)
    conn.last_refreshed_at = utcnow()
    conn.connection_status = "connected"
    conn.updated_at = utcnow()

    record_audit(
        db=db,
        actor_id=user_id,
        action_type="digilocker_token_refreshed",
        resource_type="digilocker_connection",
        resource_id=conn.id,
        action_outcome="success",
        result_summary="Refreshed DigiLocker OAuth access token successfully",
    )
    db.commit()

    return {
        "status": "refreshed",
        "connection_status": "connected",
        "expires_at": iso(conn.access_token_expires_at),
    }
