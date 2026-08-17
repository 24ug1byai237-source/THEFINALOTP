"""
Seed script to populate initial districts, demo users, farms, and assignments.
Run: python scripts/seed.py
"""

import sys
from datetime import date, timedelta
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import engine
from app.models.enums import UserRole, FarmType, RiskLevel, RegistrationStatus, ComplianceStatus, RiskTrend
from app.models.user import User, District, UserFarmAssignment
from app.models.farm import Farm, Zone
from app.models.passport import BiosecurityPassport
from app.core.security import get_password_hash


def seed():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        # Check if already seeded
        if db.query(User).filter(User.email == "farmer@bioshield.local").first():
            print("Database already contains demo user records. Skipping seed.")
            return

        print("Seeding database...")
        # Create Districts
        dist1 = District(id="district-ranchi", name="Ranchi", state="Jharkhand")
        dist2 = District(id="district-ramgarh", name="Ramgarh", state="Jharkhand")
        db.add_all([dist1, dist2])
        db.flush()

        # Create Demo Users
        farmer = User(
            email="farmer@bioshield.local",
            password_hash=get_password_hash("farmer123"),
            full_name="Rajesh Kumar",
            role=UserRole.FARMER,
            phone="+91 9876543210",
            district_id="district-ranchi",
        )
        vet = User(
            email="vet@bioshield.local",
            password_hash=get_password_hash("vet123"),
            full_name="Dr. Ananya Sharma",
            role=UserRole.VETERINARIAN,
            phone="+91 9876543211",
            district_id="district-ranchi",
        )
        officer = User(
            email="officer@bioshield.local",
            password_hash=get_password_hash("officer123"),
            full_name="Officer Suresh Verma",
            role=UserRole.OFFICER,
            phone="+91 9876543212",
            district_id="district-ranchi",
        )
        db.add_all([farmer, vet, officer])
        db.flush()

        # Create Demo Farms
        farm1 = Farm(
            id="FARM-JH-2026-0487",
            name="GreenValley Bio-Farm #04",
            owner_name="Rajesh Kumar",
            location="Kanke, Ranchi",
            farm_type=FarmType.POULTRY,
            capacity=3500,
            animal_count=2850,
            district_id="district-ranchi",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=78,
            previous_score=74,
            risk_level=RiskLevel.SAFE,
            latitude=23.3441,
            longitude=85.3096,
            owner_phone="+91 9876543210",
        )
        farm2 = Farm(
            id="FARM-JH-2026-0102",
            name="Apex Swine Breeding Center",
            owner_name="Suresh Mahato",
            location="Ramgarh, Jharkhand",
            farm_type=FarmType.PIG,
            capacity=1200,
            animal_count=940,
            district_id="district-ramgarh",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=42,
            previous_score=58,
            risk_level=RiskLevel.CRITICAL,
            latitude=23.6300,
            longitude=85.5100,
            owner_phone="+91 9876543219",
        )
        farm3 = Farm(
            id="FARM-JH-2026-0319",
            name="Highland Dairy & Livestock Hub",
            owner_name="Anand Verma",
            location="Ormanjhi, Ranchi",
            farm_type=FarmType.MIXED,
            capacity=850,
            animal_count=720,
            district_id="district-ranchi",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=85,
            previous_score=80,
            risk_level=RiskLevel.SAFE,
            latitude=23.4800,
            longitude=85.4200,
            owner_phone="+91 9876543222",
        )
        farm4 = Farm(
            id="FARM-JH-2026-0550",
            name="Chota Nagpur Agro-Livestock Farm",
            owner_name="Sunil Singh",
            location="Mandu, Ramgarh",
            farm_type=FarmType.POULTRY,
            capacity=600,
            animal_count=480,
            district_id="district-ramgarh",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=64,
            previous_score=60,
            risk_level=RiskLevel.SAFE,
            latitude=23.7100,
            longitude=85.4900,
            owner_phone="+91 9876543233",
        )
        db.add_all([farm1, farm2, farm3, farm4])
        db.flush()

        # Create Passports for farms
        today = date.today()
        p1 = BiosecurityPassport(
            id="PASS-FARM-JH-2026-0487",
            farm_id=farm1.id,
            passport_qr_code=f"BS-PASSPORT-{farm1.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT,
            risk_trend=RiskTrend.IMPROVING,
            issue_date=today,
            last_inspection_date=today - timedelta(days=30),
        )
        p2 = BiosecurityPassport(
            id="PASS-FARM-JH-2026-0102",
            farm_id=farm2.id,
            passport_qr_code=f"BS-PASSPORT-{farm2.id}-ATTENTION",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_trend=RiskTrend.DETERIORATING,
            issue_date=today,
            last_inspection_date=today - timedelta(days=45),
        )
        p3 = BiosecurityPassport(
            id="PASS-FARM-JH-2026-0319",
            farm_id=farm3.id,
            passport_qr_code=f"BS-PASSPORT-{farm3.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT,
            risk_trend=RiskTrend.STABLE,
            issue_date=today,
            last_inspection_date=today - timedelta(days=15),
        )
        p4 = BiosecurityPassport(
            id="PASS-FARM-JH-2026-0550",
            farm_id=farm4.id,
            passport_qr_code=f"BS-PASSPORT-{farm4.id}-REVIEW",
            compliance_status=ComplianceStatus.ATTENTION_REQUIRED,
            risk_trend=RiskTrend.STABLE,
            issue_date=today,
            last_inspection_date=today - timedelta(days=20),
        )
        db.add_all([p1, p2, p3, p4])

        # Assign all farms to demo users
        assignments = []
        for u in [farmer, vet, officer]:
            for f in [farm1, farm2, farm3, farm4]:
                assignments.append(UserFarmAssignment(user_id=u.id, farm_id=f.id, is_owner=(u.id == farmer.id and f.id == farm1.id)))
        db.add_all(assignments)

        db.commit()
        print("Database seeded successfully with demo users, farms, and assignments!")


if __name__ == "__main__":
    seed()
