"""
Fix script: Stamps alembic_version to 003_otp_requests so that
'alembic upgrade head' on Render skips already-created tables.
Run once from local PC:
    python backend/scripts/fix_alembic_version.py
"""
from sqlalchemy import create_engine, text

DATABASE_URL = (
    "postgresql://agrisentinel:5bizilYDF15kKIsGy7vZ0LyRrzdStkHx"
    "@dpg-d9tj0oijobas73d4fm30-a.oregon-postgres.render.com/agrisentinel"
    "?sslmode=require"
)

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    current = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    print(f"Current alembic version: {current[0]}")
    conn.execute(text("UPDATE alembic_version SET version_num = '003_otp_requests'"))
    conn.commit()
    updated = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    print(f"Updated alembic version: {updated[0]}")
    print("Done! Now push to GitHub — Render deploy will succeed.")
