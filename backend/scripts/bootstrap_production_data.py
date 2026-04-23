#!/usr/bin/env python
"""One-time production bootstrap for baseline users and starter requests.

This script is idempotent:
- existing users/profiles/roles are updated to expected defaults
- starter requests are upserted by marker note to avoid duplicates
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models import (
    BloodGroup,
    Donor,
    Gender,
    Profile,
    Recipient,
    Request,
    RequestStatus,
    RequestType,
    UrgencyLevel,
    User,
    UserRole,
)
from app.core.security import SecurityManager


@dataclass
class BootstrapUser:
    email: str
    phone: str
    username: str
    role: UserRole
    first_name: str
    last_name: str
    blood_group: BloodGroup
    latitude: Decimal
    longitude: Decimal
    gender: Gender = Gender.OTHER
    address: str = "Bootstrap Hospital District"
    city: str = "Mumbai"
    state: str = "Maharashtra"
    postal_code: str = "400001"
    country: str = "India"
    emergency_contact_name: str = "Emergency Desk"
    emergency_contact_phone: str = "+910000000000"


def _upsert_user(db, item: BootstrapUser, password: str) -> User:
    user = db.query(User).filter(User.email == item.email).first()
    if user is None:
        user = User(
            email=item.email,
            phone=item.phone,
            username=item.username,
            password_hash=SecurityManager.hash_password(password),
            role=item.role,
            is_active=True,
            is_blocked=False,
            email_verified=True,
            phone_verified=True,
            id_verified=True,
        )
        db.add(user)
        db.flush()
        return user

    user.phone = item.phone
    user.username = item.username
    user.password_hash = SecurityManager.hash_password(password)
    user.role = item.role
    user.is_active = True
    user.is_blocked = False
    user.email_verified = True
    user.phone_verified = True
    user.id_verified = True
    user.updated_at = datetime.utcnow()
    db.flush()
    return user


def _upsert_profile(db, user: User, item: BootstrapUser) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(
            user_id=user.id,
            first_name=item.first_name,
            last_name=item.last_name,
            date_of_birth="1990-01-01",
            gender=item.gender,
            address=item.address,
            city=item.city,
            state=item.state,
            postal_code=item.postal_code,
            country=item.country,
            latitude=item.latitude,
            longitude=item.longitude,
            blood_group=item.blood_group,
            emergency_contact_name=item.emergency_contact_name,
            emergency_contact_phone=item.emergency_contact_phone,
        )
        db.add(profile)
        db.flush()
        return profile

    profile.first_name = item.first_name
    profile.last_name = item.last_name
    profile.gender = item.gender
    profile.address = item.address
    profile.city = item.city
    profile.state = item.state
    profile.postal_code = item.postal_code
    profile.country = item.country
    profile.latitude = item.latitude
    profile.longitude = item.longitude
    profile.blood_group = item.blood_group
    profile.emergency_contact_name = item.emergency_contact_name
    profile.emergency_contact_phone = item.emergency_contact_phone
    profile.updated_at = datetime.utcnow()
    db.flush()
    return profile


def _upsert_donor(db, user: User, profile: Profile) -> Donor:
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if donor is None:
        donor = Donor(
            user_id=user.id,
            profile_id=profile.id,
            is_available=True,
            can_donate_blood=True,
            organ_types=["KIDNEY", "LIVER"],
            organ_donation_registered=True,
            preferred_donation_time="ANYTIME",
            medical_clearance=True,
        )
        db.add(donor)
        db.flush()
        return donor

    donor.profile_id = profile.id
    donor.is_available = True
    donor.can_donate_blood = True
    donor.organ_types = ["KIDNEY", "LIVER"]
    donor.organ_donation_registered = True
    donor.preferred_donation_time = donor.preferred_donation_time or "ANYTIME"
    donor.medical_clearance = True
    donor.updated_at = datetime.utcnow()
    db.flush()
    return donor


def _upsert_recipient(db, user: User, profile: Profile) -> Recipient:
    recipient = db.query(Recipient).filter(Recipient.user_id == user.id).first()
    if recipient is None:
        recipient = Recipient(
            user_id=user.id,
            profile_id=profile.id,
            is_active=True,
            primary_disease="Trauma support",
            diagnosis_date="2026-04-01",
            surgery_needed_date="2026-05-20",
            hospital_name="Metro Care Hospital",
            hospital_contact_phone="+912240000111",
            doctor_name="Dr. Mehta",
            doctor_phone="+919811112222",
            doctor_registration_number="MH-DOC-0091",
            is_verified_by_hospital=True,
            matching_criteria={"urgency": "CRITICAL"},
            urgency_level=UrgencyLevel.CRITICAL,
        )
        db.add(recipient)
        db.flush()
        return recipient

    recipient.profile_id = profile.id
    recipient.is_active = True
    recipient.hospital_name = recipient.hospital_name or "Metro Care Hospital"
    recipient.hospital_contact_phone = recipient.hospital_contact_phone or "+912240000111"
    recipient.doctor_name = recipient.doctor_name or "Dr. Mehta"
    recipient.doctor_phone = recipient.doctor_phone or "+919811112222"
    recipient.doctor_registration_number = recipient.doctor_registration_number or "MH-DOC-0091"
    recipient.is_verified_by_hospital = True
    recipient.matching_criteria = recipient.matching_criteria or {"urgency": "CRITICAL"}
    recipient.urgency_level = recipient.urgency_level or UrgencyLevel.CRITICAL
    recipient.updated_at = datetime.utcnow()
    db.flush()
    return recipient


def _upsert_bootstrap_requests(db, recipient: Recipient) -> tuple[int, int]:
    base_time = datetime.utcnow()
    definitions = [
        {
            "marker": "PROD_BOOTSTRAP::BLOOD_O_POS",
            "request_type": RequestType.BLOOD,
            "blood_group_needed": "O+",
            "organ_type_needed": None,
            "urgency_level": UrgencyLevel.CRITICAL,
            "needed_by": base_time + timedelta(days=1),
            "hospital_name": "Metro Care Hospital",
            "hospital_location": {"latitude": 19.1196, "longitude": 72.8697, "address": "Andheri East"},
            "doctor_name": "Dr. Mehta",
            "doctor_phone": "+919811112222",
            "required_tests": ["CBC"],
        },
        {
            "marker": "PROD_BOOTSTRAP::BLOOD_A_NEG",
            "request_type": RequestType.BLOOD,
            "blood_group_needed": "A-",
            "organ_type_needed": None,
            "urgency_level": UrgencyLevel.MEDIUM,
            "needed_by": base_time + timedelta(days=2),
            "hospital_name": "City Health Hospital",
            "hospital_location": {"latitude": 19.0896, "longitude": 72.8656, "address": "Bandra East"},
            "doctor_name": "Dr. Singh",
            "doctor_phone": "+919811113333",
            "required_tests": ["CBC"],
        },
        {
            "marker": "PROD_BOOTSTRAP::ORGAN_KIDNEY_O_POS",
            "request_type": RequestType.ORGAN,
            "blood_group_needed": "O+",
            "organ_type_needed": "KIDNEY",
            "urgency_level": UrgencyLevel.CRITICAL,
            "needed_by": base_time + timedelta(days=5),
            "hospital_name": "Lifeline Transplant Center",
            "hospital_location": {"latitude": 19.0760, "longitude": 72.8777, "address": "Dadar"},
            "doctor_name": "Dr. Rao",
            "doctor_phone": "+919811114444",
            "required_tests": ["CBC", "Crossmatch"],
        },
    ]

    created = 0
    updated = 0
    for item in definitions:
        existing = (
            db.query(Request)
            .filter(
                Request.recipient_id == recipient.id,
                Request.clinical_notes == item["marker"],
            )
            .first()
        )
        if existing is None:
            request_obj = Request(
                recipient_id=recipient.id,
                request_type=item["request_type"],
                blood_group_needed=item["blood_group_needed"],
                organ_type_needed=item["organ_type_needed"],
                quantity_needed=1,
                urgency_level=item["urgency_level"],
                needed_by=item["needed_by"],
                status=RequestStatus.OPEN,
                hospital_location=item["hospital_location"],
                hospital_name=item["hospital_name"],
                receiving_doctor_name=item["doctor_name"],
                receiving_doctor_phone=item["doctor_phone"],
                clinical_notes=item["marker"],
                required_tests=item["required_tests"],
                is_public=True,
            )
            db.add(request_obj)
            created += 1
            continue

        existing.request_type = item["request_type"]
        existing.blood_group_needed = item["blood_group_needed"]
        existing.organ_type_needed = item["organ_type_needed"]
        existing.quantity_needed = 1
        existing.urgency_level = item["urgency_level"]
        existing.needed_by = item["needed_by"]
        existing.status = RequestStatus.OPEN
        existing.hospital_location = item["hospital_location"]
        existing.hospital_name = item["hospital_name"]
        existing.receiving_doctor_name = item["doctor_name"]
        existing.receiving_doctor_phone = item["doctor_phone"]
        existing.required_tests = item["required_tests"]
        existing.is_public = True
        existing.updated_at = datetime.utcnow()
        updated += 1

    # Repair older organ records missing blood group so compatibility filtering can see them.
    legacy_repaired = (
        db.query(Request)
        .filter(
            Request.recipient_id == recipient.id,
            Request.request_type == RequestType.ORGAN,
            (Request.blood_group_needed.is_(None) | (Request.blood_group_needed == "")),
        )
        .update(
            {
                Request.blood_group_needed: "O+",
                Request.status: RequestStatus.OPEN,
                Request.is_public: True,
                Request.updated_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
    )
    updated += int(legacy_repaired or 0)

    return created, updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap users and optional starter requests.")
    parser.add_argument(
        "--password",
        default=os.getenv("BOOTSTRAP_USER_PASSWORD", "SecurePass@123"),
        help="Password to set for all bootstrap users (default: BOOTSTRAP_USER_PASSWORD or SecurePass@123).",
    )
    parser.add_argument(
        "--without-requests",
        action="store_true",
        help="Create/update users and roles only, skip starter request data.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag to run writes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.yes:
        print("Refusing to run without --yes confirmation flag.")
        raise SystemExit(2)

    admin_data = BootstrapUser(
        email="admin@blooddonation.com",
        phone="+919999999999",
        username="admin_demo",
        role=UserRole.ADMIN,
        first_name="Admin",
        last_name="Operator",
        blood_group=BloodGroup.A_POS,
        latitude=Decimal("19.0760"),
        longitude=Decimal("72.8777"),
    )
    donor_data = BootstrapUser(
        email="donor@blooddonation.com",
        phone="+918888888888",
        username="donor_demo",
        role=UserRole.DONOR,
        first_name="Arjun",
        last_name="Patel",
        blood_group=BloodGroup.O_POS,
        latitude=Decimal("19.1328"),
        longitude=Decimal("72.8264"),
        gender=Gender.MALE,
    )
    recipient_data = BootstrapUser(
        email="recipient@blooddonation.com",
        phone="+917777777777",
        username="recipient_demo",
        role=UserRole.RECIPIENT,
        first_name="Riya",
        last_name="Sharma",
        blood_group=BloodGroup.O_POS,
        latitude=Decimal("19.1196"),
        longitude=Decimal("72.8697"),
        gender=Gender.FEMALE,
    )

    db = SessionLocal()
    try:
        admin_user = _upsert_user(db, admin_data, args.password)
        donor_user = _upsert_user(db, donor_data, args.password)
        recipient_user = _upsert_user(db, recipient_data, args.password)

        _upsert_profile(db, admin_user, admin_data)
        donor_profile = _upsert_profile(db, donor_user, donor_data)
        recipient_profile = _upsert_profile(db, recipient_user, recipient_data)

        _upsert_donor(db, donor_user, donor_profile)
        recipient = _upsert_recipient(db, recipient_user, recipient_profile)

        req_created = 0
        req_updated = 0
        if not args.without_requests:
            req_created, req_updated = _upsert_bootstrap_requests(db, recipient)

        db.commit()
        print("Bootstrap completed successfully.")
        print(f"Users ensured: admin={admin_user.email}, donor={donor_user.email}, recipient={recipient_user.email}")
        print(f"Password set for all bootstrap users: {args.password}")
        if args.without_requests:
            print("Starter requests: skipped (--without-requests)")
        else:
            print(f"Starter requests created: {req_created}, updated/repaired: {req_updated}")
    except Exception as exc:
        db.rollback()
        print(f"Bootstrap failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
