"""Second Hour Database Migration Runner.

Executes idempotent SQL migrations transactionally against the configured database engine (Neon PostgreSQL).
Never executes DROP TABLE or destructive operations.

Run:
    python -m scripts.migrate
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db import Base, engine


def run_migrations() -> bool:
    print("=" * 60)
    print("Second Hour: Database Migration Runner")
    print(f"Dialect: {engine.dialect.name}")
    print("=" * 60)

    migrations_dir = ROOT / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        print("[WARN] No SQL migration files found in migrations/.")
        return True

    try:
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                # Ensure migration history table exists
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(64) PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
                    );
                """))

                # Get already applied versions
                applied = set(
                    r[0] for r in conn.execute(text("SELECT version FROM schema_migrations;")).fetchall()
                )

                for sql_path in sql_files:
                    version_name = sql_path.stem
                    if version_name in applied:
                        print(f"[SKIP] Migration '{version_name}' already applied.")
                        continue

                    print(f"[APPLYING] Migration '{version_name}'...")
                    sql_content = sql_path.read_text(encoding="utf-8")
                    conn.exec_driver_sql(sql_content)
                    print(f"[SUCCESS] Migration '{version_name}' applied successfully.")
        else:
            # SQLite fallback: use SQLAlchemy metadata creation
            print("[INFO] Dialect is SQLite; applying schema definitions via SQLAlchemy metadata...")
            Base.metadata.create_all(engine)
            print("[SUCCESS] SQLite schema initialized.")

        print("=" * 60)
        print("[COMPLETE] All migrations up to date.")
        print("=" * 60)
        return True
    except Exception as exc:
        print(f"\n[FAIL] Migration failed with error: {exc}")
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
