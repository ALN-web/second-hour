"""Unit & integration tests for Second Hour database connectivity and Neon PostgreSQL configuration."""
import os
from unittest.mock import patch

from sqlalchemy import select, text
from app.db import (
    Base,
    _build_database_url,
    check_connection,
    engine,
    get_db_context,
    init_db,
)


def test_default_database_url_fallback():
    with patch("app.db.DATABASE_URL", ""):
        url, connect_args = _build_database_url()
        assert url.startswith("sqlite:///")
        assert connect_args.get("check_same_thread") is False


def test_postgres_database_url_normalization():
    # Normalizes postgres:// to postgresql+psycopg2://
    with patch("app.db.DATABASE_URL", "postgres://user:pass@ep-test.neon.tech/neondb?sslmode=require"):
        url, _ = _build_database_url()
        assert url.startswith("postgresql+psycopg2://")
        assert "sslmode=require" in url

    # Keeps existing driver if explicitly set
    with patch("app.db.DATABASE_URL", "postgresql+psycopg://user:pass@ep-test.neon.tech/neondb"):
        url, _ = _build_database_url()
        assert url.startswith("postgresql+psycopg://")


def test_sqlite_connection_check():
    status = check_connection()
    assert status["ok"] is True
    assert status["dialect"] == "sqlite"
    assert status["query_result"] == 1
    assert "error" not in status


def test_session_context_manager_lifecycle():
    with get_db_context() as session:
        result = session.execute(select(text("1"))).scalar()
        assert result == 1


def test_database_models_metadata_intact():
    table_names = set(Base.metadata.tables.keys())
    # Verify core application tables exist in metadata
    expected_tables = {
        "users",
        "cases",
        "case_members",
        "documents",
        "vehicles",
        "vehicle_documents",
        "central_documents",
        "emergency_contacts",
        "emergency_contact_permissions",
        "medical_information",
        "user_addresses",
        "user_privacy_preferences",
        "user_notification_preferences",
    }
    assert expected_tables.issubset(table_names)
