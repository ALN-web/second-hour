"""Test suite for Ask Second Hour AI Assistant module.

Tests:
1. Conversation creation, listing, retrieval, pinning, and deletion.
2. User isolation (preventing other users from reading/modifying conversations).
3. Context-aware AI queries:
   - Vehicles and insurance policy grounding.
   - Central document wallet retrieval and citations.
   - Accident case status, hospital, police report, and tasks.
   - PM-RAHAT official government scheme guidance (MoRTH citation).
   - Emergency 112 guidance trigger.
4. Action card proposal and action execution endpoint.
"""
from __future__ import annotations

import os
import tempfile
import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="sh_asst_test_")
os.environ["ANTHROPIC_API_KEY"] = ""

from app.db import Conversation, SessionLocal, User, init_db
from app.services import assistant as asst_svc
from app.services.common import PermissionDenied, ServiceError
from scripts.seed import seed


@pytest.fixture(autouse=True)
def setup_db():
    seed()
    yield


def test_conversation_lifecycle():
    db = SessionLocal()
    try:
        # 1. Create conversation
        conv = asst_svc.create_conversation(db, "u_priya", "Test Chat")
        assert conv["id"].startswith("conv_")
        assert conv["title"] == "Test Chat"
        assert conv["is_pinned"] is False

        # 2. List conversations
        convs = asst_svc.list_conversations(db, "u_priya")
        assert len(convs) >= 1
        assert any(c["id"] == conv["id"] for c in convs)

        # 3. Pin conversation
        pinned = asst_svc.pin_conversation(db, "u_priya", conv["id"], True)
        assert pinned["is_pinned"] is True

        # 4. Get conversation
        details = asst_svc.get_conversation(db, "u_priya", conv["id"])
        assert details["id"] == conv["id"]
        assert details["is_pinned"] is True
        assert len(details["messages"]) == 0

        # 5. Delete conversation
        res = asst_svc.delete_conversation(db, "u_priya", conv["id"])
        assert res is True

        with pytest.raises(ServiceError):
            asst_svc.get_conversation(db, "u_priya", conv["id"])
    finally:
        db.close()


def test_user_data_isolation():
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya", "Priya Confidential Chat")

        # Outsider cannot get Priya's conversation
        with pytest.raises(PermissionDenied):
            asst_svc.get_conversation(db, "u_outsider", conv["id"])

        # Outsider cannot post to Priya's conversation
        with pytest.raises(PermissionDenied):
            asst_svc.post_user_message(db, "u_outsider", conv["id"], "Hello")

        # Outsider cannot delete Priya's conversation
        with pytest.raises(PermissionDenied):
            asst_svc.delete_conversation(db, "u_outsider", conv["id"])
    finally:
        db.close()


def test_ai_query_vehicles_grounding():
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya")
        res = asst_svc.post_user_message(db, "u_priya", conv["id"], "What is the insurance status of my car?")

        assert res["sender"] == "assistant"
        assert "KA-01-MJ-2024" in res["content"] or "Honda" in res["content"]
        assert len(res["citations"]) >= 1
        assert any("KA-01-MJ-2024" in c["title"] for c in res["citations"])
        assert any(a["action_type"] in ("NAVIGATE", "OPEN_DOCUMENT") for a in res["action_cards"])
        assert len(res["suggested_followups"]) > 0
    finally:
        db.close()


def test_ai_query_documents_grounding():
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya")
        res = asst_svc.post_user_message(db, "u_priya", conv["id"], "Show me what documents I have in my wallet")

        assert res["sender"] == "assistant"
        assert len(res["citations"]) >= 1
        # Action card to open document wallet
        assert any(a["action_type"] == "NAVIGATE" for a in res["action_cards"])
    finally:
        db.close()


def test_ai_query_accident_case_grounding():
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya")
        res = asst_svc.post_user_message(db, "u_priya", conv["id"], "Give me an update on my accident case and hospital status")

        assert res["sender"] == "assistant"
        assert "SH-2026-0001" in res["content"] or "Hospital" in res["content"]
        assert len(res["citations"]) >= 1
        assert any("SH-2026-0001" in c["title"] for c in res["citations"])
        assert any(a["action_type"] == "OPEN_CASE" for a in res["action_cards"])
    finally:
        db.close()


def test_ai_query_pmrahat_scheme():
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya")
        res = asst_svc.post_user_message(db, "u_priya", conv["id"], "How does PM-RAHAT cashless assistance work and what is the limit?")

        assert res["sender"] == "assistant"
        assert "1,50,000" in res["content"] or "1.5" in res["content"]
        assert any(c["type"] == "OFFICIAL_GOVERNMENT" for c in res["citations"])
    finally:
        db.close()


def test_ai_query_emergency_warning():
    db = SessionLocal()
    try:
        conv = asst_svc.create_conversation(db, "u_priya")
        res = asst_svc.post_user_message(db, "u_priya", conv["id"], "There is an emergency accident! Someone is bleeding!")

        assert res["sender"] == "assistant"
        assert "112" in res["content"]
        assert "EMERGENCY" in res["content"]
    finally:
        db.close()


def test_execute_assistant_action():
    db = SessionLocal()
    try:
        # Navigate action
        nav = asst_svc.execute_assistant_action(db, "u_priya", "NAVIGATE", {"path": "/vehicles"})
        assert nav["status"] == "success"
        assert nav["path"] == "/vehicles"

        # Create task action
        task = asst_svc.execute_assistant_action(db, "u_priya", "CREATE_TASK", {
            "title": "Follow up with hospital billing desk",
            "priority": "high",
        })
        assert task["status"] == "success"
        assert "task_id" in task
    finally:
        db.close()
