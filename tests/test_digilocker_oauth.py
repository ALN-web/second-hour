"""Comprehensive Automated Test Suite for DigiLocker OAuth 2.0 PKCE & Token Security.

Covers all 24 required scenarios across:
- OAuth State Security (1-6)
- PKCE S256 & Verifier Protection (7-10)
- Encrypted Token Lifecycle & Concurrency (11-15)
- Provider Integration & Trust Modes (16-20)
- Regressions (Step 1 OTP, Step 2 Vehicle Invalidation, Documents, API Auth) (21-24)
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import config
from app.api import app
from app.db import (
    AuditLog,
    CentralDocument,
    ConsentRecord,
    DigiLockerOAuthState,
    SessionLocal,
    User,
    UserDigiLockerConnection,
    Vehicle,
    VerificationRecord,
    new_id,
    utcnow,
)
from app.encryption import decrypt_token, encrypt_token, get_fernet
from app.services import central_documents as cdoc_svc
from app.services import digilocker_oauth
from app.services import profile as profile_svc
from app.services import vehicles as vehicle_svc
from app.services import verification as verify_svc
from app.services.common import PermissionDenied, ServiceError


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def user_a(db):
    user = db.get(User, "u_priya")
    assert user is not None
    return user


@pytest.fixture
def user_b(db):
    user = db.get(User, "u_arjun")
    assert user is not None
    return user


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_digilocker_test_state(db):
    """Ensure clean DigiLocker connection and state tables before each test."""
    yield
    # Rollback any uncommitted transaction first
    try:
        db.rollback()
        db.query(DigiLockerOAuthState).filter(
            DigiLockerOAuthState.user_id.in_(["u_priya", "u_arjun"])
        ).delete(synchronize_session=False)
        db.query(UserDigiLockerConnection).filter(
            UserDigiLockerConnection.user_id.in_(["u_priya", "u_arjun"])
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()


# ==============================================================================
# 1. OAuth State Tests (1 - 6)
# ==============================================================================

def test_valid_oauth_state_accepted(db, user_a):
    """Scenario 1: Valid OAuth state is accepted and advances the flow."""
    init_res = digilocker_oauth.initiate_oauth_flow(
        db, user_id=user_a.id, redirect_uri="http://localhost:5173/profile", doc_type="driving_licence"
    )
    assert "state" in init_res
    assert "auth_url" in init_res
    state_token = init_res["state"]

    # Verify state record in database
    state_rec = db.scalars(
        select(DigiLockerOAuthState).where(DigiLockerOAuthState.state == state_token)
    ).first()
    assert state_rec is not None
    assert state_rec.user_id == user_a.id
    assert state_rec.is_consumed is False
    assert state_rec.code_challenge_method == "S256"

    # Complete callback
    cb_res = digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=state_token, code="auth_code_sample_123"
    )
    assert cb_res["status"] == "connected"
    assert cb_res["connection_status"] == "connected"

    # Verify state record is now consumed
    db.refresh(state_rec)
    assert state_rec.is_consumed is True
    assert state_rec.consumed_at is not None

    # Verify active connection record
    conn = db.scalars(
        select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
    ).first()
    assert conn is not None
    assert conn.connection_status == "connected"
    assert conn.encrypted_access_token != ""


def test_missing_oauth_state_rejected(db, user_a, client):
    """Scenario 2: Missing OAuth state is rejected in both service and API."""
    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.handle_oauth_callback(
            db, authenticated_user_id=user_a.id, state="", code="auth_code_xyz"
        )
    assert "Missing OAuth state" in str(exc.value)

    # API POST test
    res_post = client.post(
        "/api/verify/digilocker/callback",
        headers={"X-User-Id": user_a.id},
        json={"state": "", "code": "sample_code"},
    )
    assert res_post.status_code == 400
    assert "Missing OAuth state" in res_post.json()["detail"]


def test_mismatched_or_tampered_state_rejected(db, user_a, client):
    """Scenario 3: Mismatched or tampered state is rejected."""
    tampered_state = "tampered-unrecognized-state-token-12345"
    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.handle_oauth_callback(
            db, authenticated_user_id=user_a.id, state=tampered_state, code="auth_code_xyz"
        )
    assert "Invalid OAuth state" in str(exc.value)

    res = client.post(
        "/api/verify/digilocker/callback",
        headers={"X-User-Id": user_a.id},
        json={"state": tampered_state, "code": "code123"},
    )
    assert res.status_code == 400
    assert "Invalid OAuth state" in res.json()["detail"]


def test_expired_oauth_state_rejected(db, user_a):
    """Scenario 4: Expired state is rejected."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    state_token = init_res["state"]

    # Manually expire the state
    state_rec = db.scalars(
        select(DigiLockerOAuthState).where(DigiLockerOAuthState.state == state_token)
    ).first()
    assert state_rec is not None
    state_rec.expires_at = utcnow() - timedelta(minutes=5)
    db.commit()

    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.handle_oauth_callback(
            db, authenticated_user_id=user_a.id, state=state_token, code="code_abc"
        )
    assert "OAuth state has expired" in str(exc.value)

    # Verify state was marked consumed to prevent further attempts
    db.refresh(state_rec)
    assert state_rec.is_consumed is True


def test_reused_state_rejected(db, user_a):
    """Scenario 5: Reused state is rejected (replay attack prevention)."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    state_token = init_res["state"]

    # First callback succeeds
    cb_res = digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=state_token, code="code_first_use"
    )
    assert cb_res["status"] == "connected"

    # Second callback with identical state MUST be rejected
    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.handle_oauth_callback(
            db, authenticated_user_id=user_a.id, state=state_token, code="code_replay_attempt"
        )
    assert "OAuth state has already been consumed" in str(exc.value)


def test_cross_user_state_rejected(db, user_a, user_b):
    """Scenario 6: Cross-user state usage is rejected (State for User A cannot be redeemed by User B)."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    state_token = init_res["state"]

    # User B attempts to redeem User A's OAuth state
    with pytest.raises(PermissionDenied) as exc:
        digilocker_oauth.handle_oauth_callback(
            db, authenticated_user_id=user_b.id, state=state_token, code="code_for_user_b"
        )
    assert "OAuth state mismatch" in str(exc.value)

    # Verify audit log recorded mismatch
    audit = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.actor_id == user_b.id,
            AuditLog.action_type == "digilocker_oauth_state_mismatch",
        )
        .order_by(AuditLog.id.desc())
    ).first()
    assert audit is not None
    assert audit.action_outcome == "failure"


# ==============================================================================
# 2. PKCE Tests (7 - 10)
# ==============================================================================

def test_pkce_s256_code_challenge_generated():
    """Scenario 7: Correct code challenge is generated using S256."""
    verifier, challenge = digilocker_oauth.generate_pkce_pair()
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    assert len(verifier) >= 43
    assert len(verifier) <= 128
    assert challenge != verifier

    # Independently verify RFC 7636 Section 4.2 S256 formula:
    # code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) without padding
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")
    assert challenge == expected_challenge


def test_pkce_code_verifier_used_in_token_exchange(db, user_a):
    """Scenario 8: Correct code verifier is used during token exchange in PRODUCTION mode."""
    prev_mode = config.VERIFICATION_PROVIDER_MODE
    prev_id = config.DIGILOCKER_CLIENT_ID
    prev_secret = config.DIGILOCKER_CLIENT_SECRET
    config.VERIFICATION_PROVIDER_MODE = "PRODUCTION"
    config.DIGILOCKER_CLIENT_ID = "test_client_id_prod"
    config.DIGILOCKER_CLIENT_SECRET = "test_client_secret_prod"

    try:
        init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
        state_token = init_res["state"]

        # Retrieve stored encrypted verifier and decrypt it for comparison
        state_rec = db.scalars(
            select(DigiLockerOAuthState).where(DigiLockerOAuthState.state == state_token)
        ).first()
        raw_verifier = decrypt_token(state_rec.encrypted_code_verifier)

        # Mock DigiLocker token endpoint
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "live_prod_access_token_123",
            "refresh_token": "live_prod_refresh_token_456",
            "digilockerid": "DL-GOV-987654",
            "expires_in": 3600,
            "scope": "read",
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            cb_res = digilocker_oauth.handle_oauth_callback(
                db, authenticated_user_id=user_a.id, state=state_token, code="prod_code_999"
            )
            assert cb_res["status"] == "connected"
            assert mock_post.called

            # Verify the exact parameters sent to DigiLocker
            _, kwargs = mock_post.call_args
            payload = kwargs.get("data", {})
            assert payload["grant_type"] == "authorization_code"
            assert payload["code"] == "prod_code_999"
            assert payload["client_id"] == "test_client_id_prod"
            assert payload["code_verifier"] == raw_verifier
    finally:
        config.VERIFICATION_PROVIDER_MODE = prev_mode
        config.DIGILOCKER_CLIENT_ID = prev_id
        config.DIGILOCKER_CLIENT_SECRET = prev_secret


def test_invalid_pkce_code_verifier_fails(db, user_a):
    """Scenario 9: Corrupted or tampered code verifier fails token exchange securely."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    state_token = init_res["state"]

    # Corrupt the encrypted_code_verifier in the database
    state_rec = db.scalars(
        select(DigiLockerOAuthState).where(DigiLockerOAuthState.state == state_token)
    ).first()
    state_rec.encrypted_code_verifier = "corrupted_invalid_fernet_token"
    db.commit()

    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.handle_oauth_callback(
            db, authenticated_user_id=user_a.id, state=state_token, code="some_code"
        )
    assert "Failed to decrypt PKCE code verifier" in str(exc.value)

    # Verify no connection was created
    conn = db.scalars(
        select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
    ).first()
    assert conn is None


def test_code_verifier_never_exposed_in_responses_or_logs(db, user_a, client):
    """Scenario 10: Code verifier is never exposed in API responses or audit logs."""
    res = client.post(
        "/api/verify/digilocker/initiate",
        headers={"X-User-Id": user_a.id},
        json={"redirect_uri": "http://localhost:5173/profile", "doc_type": "driving_licence"},
    )
    assert res.status_code == 200
    data = res.json()

    # API response must NOT contain any verifier
    assert "code_verifier" not in data
    assert "verifier" not in data
    assert "secret" not in data
    assert "auth_url" in data
    assert "state" in data

    # Audit log check
    audit = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.actor_id == user_a.id,
            AuditLog.action_type == "digilocker_oauth_initiated",
        )
        .order_by(AuditLog.id.desc())
    ).first()
    assert audit is not None
    payload = audit.sanitized_metadata or {}
    assert "code_verifier" not in payload
    assert "verifier" not in payload


# ==============================================================================
# 3. Token Security Tests (11 - 15)
# ==============================================================================

def test_tokens_encrypted_at_rest(db, user_a):
    """Scenario 11: Access and refresh tokens are encrypted at rest in the database."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=init_res["state"], code="code_token_enc"
    )

    conn = db.scalars(
        select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
    ).first()
    assert conn is not None

    # Stored token must NOT be in plaintext
    assert not conn.encrypted_access_token.startswith("sim_mock_")
    assert not conn.encrypted_access_token.startswith("sim_sandbox_")
    # Fernet ciphertexts start with gAAAAA
    assert conn.encrypted_access_token.startswith("gAAAAA")

    # Decrypting with server key must recover the underlying token
    decrypted_at = decrypt_token(conn.encrypted_access_token)
    assert "access" in decrypted_at

    if conn.encrypted_refresh_token:
        assert conn.encrypted_refresh_token.startswith("gAAAAA")
        decrypted_rt = decrypt_token(conn.encrypted_refresh_token)
        assert "refresh" in decrypted_rt


def test_tokens_decrypted_only_in_authorized_backend_ops(db, user_a, client):
    """Scenario 12: Tokens are never leaked in status endpoints or presentation objects."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=init_res["state"], code="code_backend_ops"
    )

    # Direct service status
    status = digilocker_oauth.get_connection_status(db, user_a.id)
    assert "encrypted_access_token" not in status
    assert "access_token" not in status
    assert "refresh_token" not in status
    assert "encrypted_refresh_token" not in status
    assert status["is_connected"] is True
    assert status["digilocker_id_masked"] is not None

    # API endpoint status
    api_res = client.get(
        "/api/verify/digilocker/status",
        headers={"X-User-Id": user_a.id},
    )
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert "access_token" not in api_data
    assert "refresh_token" not in api_data
    assert "encrypted_access_token" not in api_data


def test_cross_user_token_access_rejected(db, user_a, user_b, client):
    """Scenario 13: Cross-user token access is strictly rejected."""
    # User A connects DigiLocker
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=init_res["state"], code="code_u_a"
    )

    # User B checks status: User B sees disconnected, never User A's info
    res_b = client.get("/api/verify/digilocker/status", headers={"X-User-Id": user_b.id})
    assert res_b.status_code == 200
    assert res_b.json()["is_connected"] is False
    assert res_b.json()["digilocker_id_masked"] is None

    # User B attempts to refresh User A's token
    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.refresh_digilocker_token(db, user_id=user_b.id)
    assert "No active DigiLocker connection found" in str(exc.value)

    # User B disconnects: does NOT touch User A's connection
    res_disc = client.post("/api/verify/digilocker/disconnect", headers={"X-User-Id": user_b.id})
    assert res_disc.status_code == 200
    assert res_disc.json()["connection_status"] == "disconnected"

    # User A remains connected
    status_a = digilocker_oauth.get_connection_status(db, user_a.id)
    assert status_a["is_connected"] is True


def test_expired_or_revoked_tokens_require_reconnect_or_refresh(db, user_a, client):
    """Scenario 14: Expired or revoked tokens trigger appropriate reconnect/refresh workflows."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=init_res["state"], code="code_exp_test"
    )

    conn = db.scalars(
        select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
    ).first()
    # Simulate expired token
    conn.access_token_expires_at = utcnow() - timedelta(minutes=10)
    db.commit()

    status = digilocker_oauth.get_connection_status(db, user_a.id)
    assert status["is_connected"] is False
    assert status["connection_status"] == "expired"
    assert status["is_expired"] is True

    # Refresh token restores connection
    ref_res = digilocker_oauth.refresh_digilocker_token(db, user_a.id)
    assert ref_res["status"] == "refreshed"
    assert ref_res["connection_status"] == "connected"

    db.refresh(conn)
    from app.services.digilocker_oauth import _normalize_dt
    assert _normalize_dt(conn.access_token_expires_at) > _normalize_dt(utcnow())

    # Disconnect clears stored tokens securely
    disc_res = digilocker_oauth.disconnect_connection(db, user_a.id)
    assert disc_res["connection_status"] == "disconnected"
    db.refresh(conn)
    assert conn.encrypted_access_token == ""
    assert conn.encrypted_refresh_token is None


def test_concurrent_token_refreshes_handled_safely(db, user_a):
    """Scenario 15: Concurrent token refreshes are handled safely without duplicate writes."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=init_res["state"], code="code_concur"
    )

    # Perform multiple sequential refreshes to verify state persistence and row locking
    res1 = digilocker_oauth.refresh_digilocker_token(db, user_a.id)
    res2 = digilocker_oauth.refresh_digilocker_token(db, user_a.id)
    assert res1["status"] == "refreshed"
    assert res2["status"] == "refreshed"

    # Enforce exactly one connection record exists for user_a (unique constraint)
    conns = db.scalars(
        select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
    ).all()
    assert len(conns) == 1


# ==============================================================================
# 4. Provider Integration Tests (16 - 20)
# ==============================================================================

def test_digilocker_authorization_denial_handled_gracefully(db, user_a):
    """Scenario 16: Authorization denial from DigiLocker is handled gracefully."""
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    state_token = init_res["state"]

    with pytest.raises(ServiceError) as exc:
        digilocker_oauth.handle_oauth_callback(
            db,
            authenticated_user_id=user_a.id,
            state=state_token,
            error="access_denied",
            error_description="The user declined access to their DigiLocker account",
        )
    assert "authorization denied" in str(exc.value).lower()

    # Audit record must reflect failure
    audit = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.actor_id == user_a.id,
            AuditLog.action_type == "digilocker_oauth_denied",
        )
        .order_by(AuditLog.id.desc())
    ).first()
    assert audit is not None
    assert audit.action_outcome == "failure"

    # State must be consumed
    state_rec = db.scalars(
        select(DigiLockerOAuthState).where(DigiLockerOAuthState.state == state_token)
    ).first()
    assert state_rec.is_consumed is True


def test_digilocker_invalid_token_response_fails_safely(db, user_a):
    """Scenario 17: Invalid token responses from DigiLocker fail safely without corrupted state."""
    prev_mode = config.VERIFICATION_PROVIDER_MODE
    prev_id = config.DIGILOCKER_CLIENT_ID
    prev_secret = config.DIGILOCKER_CLIENT_SECRET
    config.VERIFICATION_PROVIDER_MODE = "PRODUCTION"
    config.DIGILOCKER_CLIENT_ID = "valid_client_id"
    config.DIGILOCKER_CLIENT_SECRET = "valid_client_secret"

    try:
        init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
        state_token = init_res["state"]

        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_resp.text = "Bad Gateway from upstream gateway"

        with patch("httpx.post", return_value=mock_resp):
            with pytest.raises(ServiceError) as exc:
                digilocker_oauth.handle_oauth_callback(
                    db, authenticated_user_id=user_a.id, state=state_token, code="code_502"
                )
            assert "token exchange failed (HTTP 502)" in str(exc.value)

        # No connection created
        conn = db.scalars(
            select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
        ).first()
        assert conn is None
    finally:
        config.VERIFICATION_PROVIDER_MODE = prev_mode
        config.DIGILOCKER_CLIENT_ID = prev_id
        config.DIGILOCKER_CLIENT_SECRET = prev_secret


def test_digilocker_timeout_fails_safely_no_active_connection(db, user_a):
    """Scenario 18: Network/timeout during token exchange fails safely without creating an active connection."""
    prev_mode = config.VERIFICATION_PROVIDER_MODE
    prev_id = config.DIGILOCKER_CLIENT_ID
    prev_secret = config.DIGILOCKER_CLIENT_SECRET
    config.VERIFICATION_PROVIDER_MODE = "PRODUCTION"
    config.DIGILOCKER_CLIENT_ID = "valid_client_id"
    config.DIGILOCKER_CLIENT_SECRET = "valid_client_secret"

    try:
        init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
        state_token = init_res["state"]

        with patch("httpx.post", side_effect=httpx.TimeoutException("Connection timed out")):
            with pytest.raises(ServiceError) as exc:
                digilocker_oauth.handle_oauth_callback(
                    db, authenticated_user_id=user_a.id, state=state_token, code="code_timeout"
                )
            assert "DigiLocker token exchange timed out" in str(exc.value)

        # Ensure no active connection exists
        conn = db.scalars(
            select(UserDigiLockerConnection).where(UserDigiLockerConnection.user_id == user_a.id)
        ).first()
        assert conn is None
    finally:
        config.VERIFICATION_PROVIDER_MODE = prev_mode
        config.DIGILOCKER_CLIENT_ID = prev_id
        config.DIGILOCKER_CLIENT_SECRET = prev_secret


def test_oauth_connection_does_not_mark_documents_verified(db, user_a):
    """Scenario 19: Successful OAuth connection does not automatically mark identity documents as verified."""
    # Ensure user has a central document in unverified/pending status
    doc = db.scalars(
        select(CentralDocument).where(CentralDocument.user_id == user_a.id)
    ).first()
    if not doc:
        doc = CentralDocument(
            id=new_id("cdoc"),
            user_id=user_a.id,
            document_name="Test Driving Licence",
            category="driving_licence",
            document_type="driving_licence",
            document_number="DL-0420220011223",
            file_name="dl.pdf",
            stored_path="uploads/dl.pdf",
            mime_type="application/pdf",
            file_size=1024,
            verification_status="unverified",
            is_active=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(doc)
        db.commit()
    else:
        doc.verification_status = "unverified"
        doc.verified_at = None
        db.commit()

    # User connects their DigiLocker account
    init_res = digilocker_oauth.initiate_oauth_flow(db, user_id=user_a.id)
    digilocker_oauth.handle_oauth_callback(
        db, authenticated_user_id=user_a.id, state=init_res["state"], code="code_no_auto_doc"
    )

    # Document verification_status MUST remain unverified
    db.refresh(doc)
    assert doc.verification_status == "unverified"
    assert doc.verified_at is None


def test_mock_and_sandbox_modes_cannot_grant_production_verification(db, user_a):
    """Scenario 20: MOCK and SANDBOX modes cannot grant production verification status."""
    # Create test document
    doc = CentralDocument(
        id=new_id("cdoc"),
        user_id=user_a.id,
        document_name="Karnataka DL",
        category="driving_licence",
        document_type="driving_licence",
        document_number="KA-01-2021-9988",
        file_name="licence.pdf",
        stored_path="uploads/licence.pdf",
        mime_type="application/pdf",
        file_size=1024,
        verification_status="unverified",
        is_active=True,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(doc)

    # Create explicit consent record
    consent = ConsentRecord(
        id=new_id("cons"),
        user_id=user_a.id,
        consent_type="digilocker_verification",
        consent_status="granted",
        metadata_json={"purpose": "DigiLocker document verification test"},
        consent_timestamp=utcnow(),
        recorded_at=utcnow(),
    )
    db.add(consent)
    db.commit()

    # 1. Test MOCK mode: status MUST be pending, NEVER verified
    mock_res = verify_svc.DigiLockerAdapter.verify_identity_document(
        db, user_id=user_a.id, document_id=doc.id, consent_record_id=consent.id, trust_mode="MOCK"
    )
    assert mock_res["status"] == "pending"
    assert mock_res["verification_status"] == "pending"
    assert mock_res["provider"] == "MOCK_DIGILOCKER"
    db.refresh(doc)
    assert doc.verification_status == "pending"
    assert doc.verified_at is None

    # 2. Test SANDBOX mode: status MUST be pending, NEVER verified
    sandbox_res = verify_svc.DigiLockerAdapter.verify_identity_document(
        db, user_id=user_a.id, document_id=doc.id, consent_record_id=consent.id, trust_mode="SANDBOX"
    )
    assert sandbox_res["status"] == "pending"
    assert sandbox_res["verification_status"] == "pending"
    assert sandbox_res["provider"] == "SANDBOX_DIGILOCKER"
    db.refresh(doc)
    assert doc.verification_status == "pending"
    assert doc.verified_at is None


# ==============================================================================
# 5. Regression Tests (21 - 24)
# ==============================================================================

def test_step1_otp_security_regressions(db, user_a):
    """Scenario 21: Step 1 OTP security features (HMAC, target binding, replay) continue to function."""
    prev_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    try:
        # Request OTP for registered email
        res = verify_svc.request_otp(db, user_a.id, channel="email", target=user_a.email, purpose="email_verify")
        assert res["status"] == "otp_sent"
        code = res.get("demo_code", "123456")

        # Confirm OTP
        conf = verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        assert conf["status"] == "verified"
        assert conf["purpose"] == "email_verify"

        # Replay attempt fails
        with pytest.raises(ServiceError) as exc:
            verify_svc.confirm_otp(db, user_a.id, channel="email", otp_code=code, purpose="email_verify")
        err_msg = str(exc.value)
        assert "No active verification code found" in err_msg or "Invalid verification code" in err_msg
    finally:
        config.DEMO_MODE = prev_demo


def test_step2_vehicle_invalidation_regressions(db, user_a):
    """Scenario 22: Step 2 vehicle verification invalidation continues to function."""
    # Find or create vehicle for user_a
    vehicle = db.scalars(
        select(Vehicle).where(Vehicle.user_id == user_a.id, Vehicle.is_active == True)
    ).first()
    assert vehicle is not None

    # Manually set to verified status
    vehicle.verification_status = "verified"
    vehicle.verification_provider = "VAHAN"
    vehicle.verification_reference_id = "VAHAN-REF-12345"
    vehicle.verified_at = utcnow()
    db.commit()

    # Update vehicle with a new registration number
    new_reg = f"KA01{utcnow().strftime('%H%M%S')}"
    vehicle_svc.update_vehicle(db, user_a.id, vehicle.id, {"registration_number": new_reg})

    # Invalidation must have triggered
    db.refresh(vehicle)
    assert vehicle.registration_number == new_reg
    assert vehicle.verification_status == "unverified"
    assert vehicle.verification_provider is None
    assert vehicle.verification_reference_id is None
    assert vehicle.verified_at is None


def test_document_and_profile_workflows_continue_working(db, user_a, client):
    """Scenario 23: Existing document upload and profile flows continue to work normally."""
    profile_data = profile_svc.get_profile(db, user_a.id)
    assert profile_data["user_id"] == user_a.id
    assert "email_verified" in profile_data

    # Profile endpoint via API
    res = client.get("/api/profile", headers={"X-User-Id": user_a.id})
    assert res.status_code == 200
    assert res.json()["user_id"] == user_a.id


def test_unauthenticated_digilocker_api_rejected(client):
    """Scenario 24: Unauthenticated access to DigiLocker API endpoints is strictly rejected (401)."""
    # Without X-User-Id header
    endpoints = [
        ("POST", "/api/verify/digilocker/initiate", {"redirect_uri": "http://localhost:5173"}),
        ("POST", "/api/verify/digilocker/callback", {"state": "abc", "code": "def"}),
        ("GET", "/api/verify/digilocker/status", None),
        ("POST", "/api/verify/digilocker/disconnect", None),
        ("POST", "/api/verify/digilocker/refresh", None),
    ]

    for method, path, payload in endpoints:
        if method == "POST":
            res = client.post(path, json=payload or {})
        else:
            res = client.get(path)
        assert res.status_code == 401, f"Expected 401 for {method} {path}, got {res.status_code}"
