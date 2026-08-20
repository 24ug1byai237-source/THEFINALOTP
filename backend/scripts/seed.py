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

        # Additional districts for the multi-state farm expansion below.
        dist3 = District(id="district-bengaluru-rural", name="Bengaluru Rural", state="Karnataka")
        dist4 = District(id="district-mysuru", name="Mysuru", state="Karnataka")
        dist5 = District(id="district-belagavi", name="Belagavi", state="Karnataka")
        dist6 = District(id="district-guntur", name="Guntur", state="Andhra Pradesh")
        dist7 = District(id="district-krishna", name="Krishna", state="Andhra Pradesh")
        dist8 = District(id="district-chittoor", name="Chittoor", state="Andhra Pradesh")
        dist9 = District(id="district-namakkal", name="Namakkal", state="Tamil Nadu")
        dist10 = District(id="district-coimbatore", name="Coimbatore", state="Tamil Nadu")
        dist11 = District(id="district-thrissur", name="Thrissur", state="Kerala")
        dist12 = District(id="district-ernakulam", name="Ernakulam", state="Kerala")

        db.add_all([
            dist1, dist2, dist3, dist4, dist5, dist6,
            dist7, dist8, dist9, dist10, dist11, dist12,
        ])
        db.flush()

        # Create Demo Users
        farmer = User(
            email="farmer@bioshield.local",
            password_hash=get_password_hash("farmer123"),
            full_name="Rajesh Kumar",
            role=UserRole.FARMER,
            phone="+91 9876543210",
            district_id="district-ranchi",
            official_id="FAR-0001",
        )
        vet = User(
            email="vet@bioshield.local",
            password_hash=get_password_hash("vet123"),
            full_name="Dr. Ananya Sharma",
            role=UserRole.VETERINARIAN,
            phone="+91 9876543211",
            district_id="district-ranchi",
            official_id="VET-0001",
        )
        vet2 = User(
            email="vet2@bioshield.local",
            password_hash=get_password_hash("vet123"),
            full_name="Dr. Priya Sharma",
            role=UserRole.VETERINARIAN,
            phone="+91 9876543214",
            district_id="district-ranchi",
            official_id="VET-0002",
        )
        vet3 = User(
            email="vet3@bioshield.local",
            password_hash=get_password_hash("vet123"),
            full_name="Dr. Arun Kumar",
            role=UserRole.VETERINARIAN,
            phone="+91 9876543215",
            district_id="district-ranchi",
            official_id="VET-0003",
        )
        officer = User(
            email="officer@bioshield.local",
            password_hash=get_password_hash("officer123"),
            full_name="Officer Suresh Verma",
            role=UserRole.OFFICER,
            phone="+91 9876543212",
            district_id="district-ranchi",
            official_id="OFF-0001",
        )
        db.add_all([farmer, vet, vet2, vet3, officer])
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
        # --- Multi-state expansion: 3 Karnataka, 3 Andhra Pradesh, 2 Tamil
        # Nadu, 2 Kerala farms (pig/poultry only), matching the same field
        # structure as farm1-farm4 above. ---
        farm5 = Farm(
            id="FARM-KA-2026-0601",
            name="Nandi Hills Poultry Farm",
            owner_name="Manjunath Gowda",
            location="Devanahalli, Bengaluru Rural",
            farm_type=FarmType.POULTRY,
            capacity=4200,
            animal_count=3650,
            district_id="district-bengaluru-rural",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=81,
            previous_score=77,
            risk_level=RiskLevel.SAFE,
            latitude=13.2437,
            longitude=77.7081,
            owner_phone="+91 9900112201",
        )
        farm6 = Farm(
            id="FARM-KA-2026-0602",
            name="Mysuru Heritage Pig Farm",
            owner_name="Nagaraj K.M.",
            location="T. Narasipura, Mysuru",
            farm_type=FarmType.PIG,
            capacity=950,
            animal_count=610,
            district_id="district-mysuru",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=55,
            previous_score=61,
            risk_level=RiskLevel.CAUTION,
            latitude=12.2098,
            longitude=76.9006,
            owner_phone="+91 9900112202",
        )
        farm7 = Farm(
            id="FARM-KA-2026-0603",
            name="Belagavi Organic Poultry Cooperative",
            owner_name="Basavaraj Patil",
            location="Khanapur, Belagavi",
            farm_type=FarmType.POULTRY,
            capacity=2800,
            animal_count=2400,
            district_id="district-belagavi",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=72,
            previous_score=69,
            risk_level=RiskLevel.SAFE,
            latitude=15.6350,
            longitude=74.5240,
            owner_phone="+91 9900112203",
        )
        farm8 = Farm(
            id="FARM-AP-2026-0701",
            name="Guntur Broiler Excellence Farm",
            owner_name="Venkata Rao",
            location="Tenali, Guntur",
            farm_type=FarmType.POULTRY,
            capacity=5000,
            animal_count=4700,
            district_id="district-guntur",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=68,
            previous_score=70,
            risk_level=RiskLevel.CAUTION,
            latitude=16.2430,
            longitude=80.6400,
            owner_phone="+91 9848012201",
        )
        farm9 = Farm(
            id="FARM-AP-2026-0702",
            name="Krishna Delta Swine Farm",
            owner_name="Subba Reddy",
            location="Machilipatnam, Krishna",
            farm_type=FarmType.PIG,
            capacity=1100,
            animal_count=890,
            district_id="district-krishna",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=38,
            previous_score=50,
            risk_level=RiskLevel.CRITICAL,
            latitude=16.1875,
            longitude=81.1389,
            owner_phone="+91 9848012202",
        )
        farm10 = Farm(
            id="FARM-AP-2026-0703",
            name="Chittoor Hills Poultry Estate",
            owner_name="Ramesh Naidu",
            location="Madanapalle, Chittoor",
            farm_type=FarmType.POULTRY,
            capacity=3300,
            animal_count=2950,
            district_id="district-chittoor",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=76,
            previous_score=72,
            risk_level=RiskLevel.SAFE,
            latitude=13.5503,
            longitude=78.5030,
            owner_phone="+91 9848012203",
        )
        farm11 = Farm(
            id="FARM-TN-2026-0801",
            name="Namakkal Layer Poultry Complex",
            owner_name="Murugan S.",
            location="Namakkal, Tamil Nadu",
            farm_type=FarmType.POULTRY,
            capacity=6000,
            animal_count=5600,
            district_id="district-namakkal",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=83,
            previous_score=79,
            risk_level=RiskLevel.SAFE,
            latitude=11.2189,
            longitude=78.1677,
            owner_phone="+91 9843012201",
        )
        farm12 = Farm(
            id="FARM-TN-2026-0802",
            name="Coimbatore Hill Pig Farm",
            owner_name="Karthikeyan R.",
            location="Mettupalayam, Coimbatore",
            farm_type=FarmType.PIG,
            capacity=780,
            animal_count=540,
            district_id="district-coimbatore",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=60,
            previous_score=58,
            risk_level=RiskLevel.CAUTION,
            latitude=11.2994,
            longitude=76.9412,
            owner_phone="+91 9843012202",
        )
        farm13 = Farm(
            id="FARM-KL-2026-0901",
            name="Thrissur Backwater Pig Farm",
            owner_name="Thomas Varghese",
            location="Kodungallur, Thrissur",
            farm_type=FarmType.PIG,
            capacity=650,
            animal_count=420,
            district_id="district-thrissur",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=47,
            previous_score=52,
            risk_level=RiskLevel.CRITICAL,
            latitude=10.2278,
            longitude=76.1988,
            owner_phone="+91 9847012201",
        )
        farm14 = Farm(
            id="FARM-KL-2026-0902",
            name="Ernakulam Coastal Poultry Farm",
            owner_name="Anoop Nair",
            location="Perumbavoor, Ernakulam",
            farm_type=FarmType.POULTRY,
            capacity=2600,
            animal_count=2250,
            district_id="district-ernakulam",
            registration_status=RegistrationStatus.REGISTERED,
            biosecurity_score=74,
            previous_score=71,
            risk_level=RiskLevel.SAFE,
            latitude=10.1097,
            longitude=76.4756,
            owner_phone="+91 9847012202",
        )

        db.add_all([
            farm1, farm2, farm3, farm4,
            farm5, farm6, farm7, farm8, farm9,
            farm10, farm11, farm12, farm13, farm14,
        ])
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
        p5 = BiosecurityPassport(
            id="PASS-FARM-KA-2026-0601", farm_id=farm5.id,
            passport_qr_code=f"BS-PASSPORT-{farm5.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT, risk_trend=RiskTrend.IMPROVING,
            issue_date=today, last_inspection_date=today - timedelta(days=25),
        )
        p6 = BiosecurityPassport(
            id="PASS-FARM-KA-2026-0602", farm_id=farm6.id,
            passport_qr_code=f"BS-PASSPORT-{farm6.id}-ATTENTION",
            compliance_status=ComplianceStatus.ATTENTION_REQUIRED, risk_trend=RiskTrend.DETERIORATING,
            issue_date=today, last_inspection_date=today - timedelta(days=40),
        )
        p7 = BiosecurityPassport(
            id="PASS-FARM-KA-2026-0603", farm_id=farm7.id,
            passport_qr_code=f"BS-PASSPORT-{farm7.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT, risk_trend=RiskTrend.STABLE,
            issue_date=today, last_inspection_date=today - timedelta(days=18),
        )
        p8 = BiosecurityPassport(
            id="PASS-FARM-AP-2026-0701", farm_id=farm8.id,
            passport_qr_code=f"BS-PASSPORT-{farm8.id}-ATTENTION",
            compliance_status=ComplianceStatus.ATTENTION_REQUIRED, risk_trend=RiskTrend.DETERIORATING,
            issue_date=today, last_inspection_date=today - timedelta(days=35),
        )
        p9 = BiosecurityPassport(
            id="PASS-FARM-AP-2026-0702", farm_id=farm9.id,
            passport_qr_code=f"BS-PASSPORT-{farm9.id}-REVIEW",
            compliance_status=ComplianceStatus.NON_COMPLIANT, risk_trend=RiskTrend.DETERIORATING,
            issue_date=today, last_inspection_date=today - timedelta(days=50),
        )
        p10 = BiosecurityPassport(
            id="PASS-FARM-AP-2026-0703", farm_id=farm10.id,
            passport_qr_code=f"BS-PASSPORT-{farm10.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT, risk_trend=RiskTrend.IMPROVING,
            issue_date=today, last_inspection_date=today - timedelta(days=22),
        )
        p11 = BiosecurityPassport(
            id="PASS-FARM-TN-2026-0801", farm_id=farm11.id,
            passport_qr_code=f"BS-PASSPORT-{farm11.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT, risk_trend=RiskTrend.IMPROVING,
            issue_date=today, last_inspection_date=today - timedelta(days=12),
        )
        p12 = BiosecurityPassport(
            id="PASS-FARM-TN-2026-0802", farm_id=farm12.id,
            passport_qr_code=f"BS-PASSPORT-{farm12.id}-ATTENTION",
            compliance_status=ComplianceStatus.ATTENTION_REQUIRED, risk_trend=RiskTrend.STABLE,
            issue_date=today, last_inspection_date=today - timedelta(days=28),
        )
        p13 = BiosecurityPassport(
            id="PASS-FARM-KL-2026-0901", farm_id=farm13.id,
            passport_qr_code=f"BS-PASSPORT-{farm13.id}-REVIEW",
            compliance_status=ComplianceStatus.NON_COMPLIANT, risk_trend=RiskTrend.DETERIORATING,
            issue_date=today, last_inspection_date=today - timedelta(days=55),
        )
        p14 = BiosecurityPassport(
            id="PASS-FARM-KL-2026-0902", farm_id=farm14.id,
            passport_qr_code=f"BS-PASSPORT-{farm14.id}-VERIFIED",
            compliance_status=ComplianceStatus.COMPLIANT, risk_trend=RiskTrend.STABLE,
            issue_date=today, last_inspection_date=today - timedelta(days=20),
        )

        db.add_all([
            p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14,
        ])

        new_state_farms = [farm5, farm6, farm7, farm8, farm9, farm10, farm11, farm12, farm13, farm14]

        # Assign the original 4 Jharkhand farms to all demo users, as before.
        assignments = []
        for u in [farmer, vet, vet2, vet3, officer]:
            for f in [farm1, farm2, farm3, farm4]:
                assignments.append(UserFarmAssignment(user_id=u.id, farm_id=f.id, is_owner=(u.id == farmer.id and f.id == farm1.id)))

        # All three demo users get access to every farm across all states —
        # Farmer and Vet via explicit UserFarmAssignment rows (their role's
        # scoping in FarmService.list_farms is assignment-based), Officer
        # via district_id=None below (their scoping is district-based, not
        # assignment-based, so an explicit assignment alone wouldn't do it).
        for f in new_state_farms:
            assignments.append(UserFarmAssignment(user_id=farmer.id, farm_id=f.id, is_owner=False))
            assignments.append(UserFarmAssignment(user_id=vet.id, farm_id=f.id, is_owner=False))
            assignments.append(UserFarmAssignment(user_id=officer.id, farm_id=f.id, is_owner=False))
        db.add_all(assignments)

        # The Officer role is scoped by district_id, not by farm assignments
        # (see FarmService.list_farms) — Officer with district_id=None gets
        # NATIONAL scope, i.e. every registered farm. Clearing it here so the
        # demo officer can see the full multi-state dataset rather than only
        # Ranchi district.
        officer.district_id = None

        db.commit()
        print("Database seeded successfully with demo users, farms, and assignments!")


if __name__ == "__main__":
    seed()
