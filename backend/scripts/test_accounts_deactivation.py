import sys
import os
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

test_db_path = os.path.join(os.path.dirname(__file__), "test_accounts.db")
if os.path.exists(test_db_path):
    try:
        os.remove(test_db_path)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

from fastapi.testclient import TestClient
from app.database.base import Base
from app.database.session import engine, SessionLocal
from app.main import app
from app.models.user import User, District
from app.models.farm import Farm
from app.models.incident import Incident
from app.core.security import get_password_hash

def seed_test_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        dist = District(id="district-ranchi", name="Ranchi", state="Jharkhand")
        db.add(dist)
        officer = User(
            email="officer@bioshield.local",
            password_hash=get_password_hash("officer123"),
            full_name="Officer Suresh Verma",
            role="officer",
            phone="+91 9876543212",
            district_id="district-ranchi",
            official_id="OFF-0001",
        )
        farm = Farm(
            id="FARM-TEST-001",
            name="Test Farm",
            owner_name="Test Owner",
            location="Ranchi",
            farm_type="poultry",
            capacity=1000,
            animal_count=500,
            district_id="district-ranchi",
            registration_status="registered",
        )
        db.add_all([officer, farm])
        db.commit()

client = TestClient(app)

def test_account_creation_and_deactivation():
    print("=== TESTING ACCOUNT CREATION, ROLES, VET SELECTION & DEACTIVATION ===")
    seed_test_db()

    # 1. Login as Officer to get admin token
    res = client.post("/api/v1/auth/login", json={"email": "officer@bioshield.local", "password": "officer123"})
    assert res.status_code == 200, f"Officer login failed: {res.text}"
    officer_token = res.json()["accessToken"]
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    # 2. Test Public Registration for Farmer
    farmer_reg = client.post("/api/v1/auth/register", json={
        "email": "testfarmer_persistent@bioshield.local",
        "password": "farmerpass123",
        "fullName": "Persistent Test Farmer",
        "role": "farmer",
        "phone": "+91 9998887771"
    })
    assert farmer_reg.status_code == 200, f"Farmer registration failed: {farmer_reg.text}"
    farmer_data = farmer_reg.json()["user"]
    print(f"[OK] Created Farmer Account: {farmer_data['fullName']} | ID: {farmer_data.get('officialId')} ({farmer_data['id']})")
    assert farmer_data["role"] == "farmer"

    # 3. Test Public Registration for Veterinarian
    vet_reg = client.post("/api/v1/auth/register", json={
        "email": "testvet_persistent@bioshield.local",
        "password": "vetpass123",
        "fullName": "Dr. Test Persistent Vet",
        "role": "veterinarian",
        "phone": "+91 9998887772"
    })
    assert vet_reg.status_code == 200, f"Vet registration failed: {vet_reg.text}"
    vet_data = vet_reg.json()["user"]
    print(f"[OK] Created Vet Account: {vet_data['fullName']} | ID: {vet_data.get('officialId')} ({vet_data['id']})")
    assert vet_data["role"] == "veterinarian"
    assert vet_data.get("officialId", "").startswith("VET-")

    # 4. Test Active Veterinarians listing
    vets_res = client.get("/api/v1/auth/veterinarians")
    assert vets_res.status_code == 200, f"List vets failed: {vets_res.text}"
    vet_list = vets_res.json()
    active_vet_ids = [v["id"] for v in vet_list]
    print(f"[OK] Fetched Active Veterinarians ({len(vet_list)} active vets in DB)")
    assert vet_data["id"] in active_vet_ids

    # 5. Test Officer Deactivating Vet Account ("Delete Account")
    delete_res = client.delete(f"/api/v1/users/{vet_data['id']}", headers=officer_headers)
    assert delete_res.status_code == 200, f"Deactivate failed: {delete_res.text}"
    deleted_user = delete_res.json()
    assert deleted_user["isActive"] == False
    print(f"[OK] Officer deactivated Vet account {vet_data['officialId']} (isActive = False)")

    # 6. Verify Deactivated Vet Cannot Sign In
    vet_login_retry = client.post("/api/v1/auth/login", json={"email": "testvet_persistent@bioshield.local", "password": "vetpass123"})
    assert vet_login_retry.status_code == 401, "Deactivated vet should be blocked from login"
    print("[OK] Deactivated user sign-in attempt successfully blocked with 401")

    # 7. Verify Deactivated Vet is Excluded from Active Vet Selection
    vets_res_after = client.get("/api/v1/auth/veterinarians")
    active_vet_ids_after = [v["id"] for v in vets_res_after.json()]
    assert vet_data["id"] not in active_vet_ids_after, "Deactivated vet must not appear in active vet selection"
    print("[OK] Deactivated user excluded from active Farmer -> Vet selection list")

    # 8. Verify Farm Data & Incidents Are NOT Deleted (Data Integrity Check)
    db = SessionLocal()
    farm_count = db.query(Farm).count()
    incident_count = db.query(Incident).count()
    db.close()
    assert farm_count > 0, "Farms must NOT be deleted upon user account deactivation!"
    print(f"[OK] DATA INTEGRITY CONFIRMED: {farm_count} Farms and {incident_count} Incidents intact in DB!")

    print("\nALL ACCOUNT CREATION & NON-DESTRUCTIVE DEACTIVATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_account_creation_and_deactivation()
