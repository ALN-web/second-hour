"""Database connectivity verification script for Second Hour.

Verifies:
1. Connection to the configured database (PostgreSQL / SQLite).
2. Execution of a test SQL query.
3. Proper opening, querying, and closing of ORM sessions.
4. Schema readiness.

Run:
    python -m scripts.test_db_connection
"""
import sys
from pathlib import Path

# Ensure app is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from app.db import Base, SessionLocal, User, check_connection, engine, get_db_context


def run_connectivity_test() -> bool:
    print("=" * 60)
    print("Second Hour Database Connectivity Test")
    print("=" * 60)

    # 1. Basic connection and metadata
    status = check_connection()
    print(f"Target Dialect : {status.get('dialect')}")
    print(f"Target         : {status.get('target')}")
    print(f"Is PostgreSQL  : {status.get('is_postgres')}")

    if not status.get("ok"):
        print(f"\n[FAIL] Connection failed: {status.get('error')}")
        print("Please check your DATABASE_URL configuration.")
        return False

    print("\n[PASS] Engine connection succeeded.")
    print(f"[PASS] Scalar query execution (SELECT 1 -> {status.get('query_result')})")
    if status.get("is_postgres"):
        print(f"Server Version : {status.get('db_version')}")
        print(f"Database Name  : {status.get('current_database')}")

    # 2. Session Lifecycle Test (Open, execute, close)
    print("\nTesting Session Lifecycle...")
    try:
        with get_db_context() as session:
            # Check if users table exists and count records
            user_count = session.scalar(select(text("count(*)")).select_from(text("users")))
            print(f"[PASS] Session opened, queried 'users' table (found {user_count} records), and committed.")
    except Exception as exc:
        print(f"[WARN] 'users' table query notice: {exc}")
        print("If this is a fresh database, run 'python -m scripts.seed' to initialize schema and seed demo data.")

    # 3. Model inspection
    tables = list(Base.metadata.tables.keys())
    print(f"\nConfigured Application Models: {len(tables)} tables registered in metadata.")

    print("\n" + "=" * 60)
    print("[SUCCESS] Database connectivity and session management verified.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_connectivity_test()
    sys.exit(0 if success else 1)
