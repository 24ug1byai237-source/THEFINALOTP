"""
Diagnostic script: checks what farms the farmer user is assigned to in production DB.
"""
from sqlalchemy import create_engine, text

DATABASE_URL = (
    "postgresql://agrisentinel:5bizilYDF15kKIsGy7vZ0LyRrzdStkHx"
    "@dpg-d9tj0oijobas73d4fm30-a.oregon-postgres.render.com/agrisentinel"
    "?sslmode=require"
)

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    email = "farmer@bioshield.local"
    rows = conn.execute(
        text("""
            SELECT u.email, f.id, f.name
            FROM user_farm_assignments ufa
            JOIN users u ON u.id = ufa.user_id
            JOIN farms f ON f.id = ufa.farm_id
            WHERE u.email = :email
        """),
        {"email": email}
    ).fetchall()

    if rows:
        print(f"Farmer '{email}' is assigned to these farms:")
        for r in rows:
            print(f"  - {r[1]} | {r[2]}")
    else:
        print(f"WARNING: No farm assignments found for '{email}'!")
        print("This is why 'Unable to load farm data' shows — farmer has no farms assigned.")

    # Also check checklist
    farms = conn.execute(text("SELECT id FROM farms LIMIT 3")).fetchall()
    for farm in farms:
        checklist_count = conn.execute(
            text("SELECT count(*) FROM checklist_items WHERE farm_id = :fid"),
            {"fid": farm[0]}
        ).scalar()
        print(f"Farm {farm[0]}: {checklist_count} checklist items")
