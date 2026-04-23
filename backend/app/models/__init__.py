# Database Models - All Tables
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, DECIMAL, Index, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import INET, ENUM as PG_ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum

Base = declarative_base()

# Define Enums as Python enums
class UserRole(str, enum.Enum):
    DONOR = "DONOR"
    RECIPIENT = "RECIPIENT"
    ADMIN = "ADMIN"

class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class BloodGroup(str, enum.Enum):
    O_POS = "O+"
    O_NEG = "O-"
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"

class UrgencyLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"

class RequestType(str, enum.Enum):
    BLOOD = "BLOOD"
    ORGAN = "ORGAN"
    PLASMA = "PLASMA"

class RequestStatus(str, enum.Enum):
    OPEN = "OPEN"
    MATCHED = "MATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class MatchStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    NOTIFIED = "NOTIFIED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DonorResponse(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"

class RecipientResponse(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class NotificationType(str, enum.Enum):
    REQUEST_MATCHED = "REQUEST_MATCHED"
    NEW_REQUEST_NEARBY = "NEW_REQUEST_NEARBY"
    DONATION_REMINDER = "DONATION_REMINDER"
    VERIFICATION_NEEDED = "VERIFICATION_NEEDED"
    SYSTEM_ALERT = "SYSTEM_ALERT"

class AdminActionType(str, enum.Enum):
    APPROVE_USER = "APPROVE_USER"
    BLOCK_USER = "BLOCK_USER"
    REJECT_REQUEST = "REJECT_REQUEST"
    VERIFY_ID = "VERIFY_ID"
    REMOVE_SPAM = "REMOVE_SPAM"
    SUSPEND_ACCOUNT = "SUSPEND_ACCOUNT"

class ActionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class User(Base):
    """User - Login & Authentication"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Verification
    email_verified = Column(Boolean, default=False, index=True)
    email_verified_at = Column(DateTime)
    phone_verified = Column(Boolean, default=False, index=True)
    phone_verified_at = Column(DateTime)
    id_verified = Column(Boolean, default=False, index=True)
    id_document_path = Column(String(500))
    id_verified_at = Column(DateTime)
    
    # Account Status
    role = Column(PG_ENUM(UserRole, name="user_role"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(String(500))
    
    # JWT
    refresh_token_hash = Column(String(255))
    last_login = Column(DateTime)
    last_ip_address = Column(INET)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
    donor = relationship("Donor", back_populates="user", uselist=False)
    recipient = relationship("Recipient", back_populates="user", uselist=False)
    admin_actions = relationship("AdminAction", back_populates="admin", foreign_keys="AdminAction.admin_id")
    notifications = relationship("Notification", back_populates="user")
    
    __table_args__ = (
        Index("idx_email_active", "email", "is_active"),
        Index("idx_role_active", "role", "is_active"),
    )


class Profile(Base):
    """User Profile - Personal Information"""
    __tablename__ = "profiles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Basic Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(String(10), nullable=False)
    gender = Column(PG_ENUM(Gender, name="gender"))
    
    # Location
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20))
    country = Column(String(100), default="India")
    
    # Geolocation
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False, index=True)
    
    # Medical
    blood_group = Column(PG_ENUM(BloodGroup, name="blood_group"), index=True)
    allergies = Column(Text)
    chronic_diseases = Column(Text)
    current_medications = Column(Text)
    
    # Emergency Contact
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    emergency_contact_relation = Column(String(50))
    
    # Media
    profile_photo_url = Column(String(500))
    id_photo_url = Column(String(500))
    medical_report_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    __table_args__ = (
        Index("idx_location", "latitude", "longitude"),
        Index("idx_city", "city"),
    )


class Donor(Base):
    """Donor Profile"""
    __tablename__ = "donors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=False)
    
    # Status
    is_available = Column(Boolean, default=True, index=True)
    availability_updated_at = Column(DateTime)
    
    # Blood Donation
    can_donate_blood = Column(Boolean, default=False)
    blood_donation_last_date = Column(String(10))
    blood_donation_eligible_date = Column(String(10))
    
    # Organ Donation
    organ_types = Column(JSON, default=[])
    organ_donation_registered = Column(Boolean, default=False)
    organ_registration_certificate_url = Column(String(500))
    
    # History
    blood_donations_count = Column(Integer, default=0)
    organ_donations_count = Column(Integer, default=0)
    lives_saved = Column(Integer, default=0)
    
    # Preferences
    preferred_donation_time = Column(String(50))
    willing_hospital_list = Column(JSON, default=[])
    
    # Verification
    medical_clearance = Column(Boolean, default=False)
    medical_clearance_date = Column(String(10))
    medical_report_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="donor")
    matches = relationship("Match", back_populates="donor", foreign_keys="Match.donor_id")
    
    __table_args__ = (
        Index("idx_available", "is_available"),
        Index("idx_blood_eligible", "blood_donation_eligible_date"),
    )


class Recipient(Base):
    """Recipient Profile"""
    __tablename__ = "recipients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Medical
    primary_disease = Column(String(255))
    diagnosis_date = Column(String(10))
    surgery_needed_date = Column(String(10))
    
    # Hospital & Doctor
    hospital_name = Column(String(255))
    hospital_contact_phone = Column(String(20))
    doctor_name = Column(String(100))
    doctor_phone = Column(String(20))
    doctor_registration_number = Column(String(50))
    
    # Verification
    is_verified_by_hospital = Column(Boolean, default=False, index=True)
    hospital_verification_date = Column(String(10))
    hospital_verification_document_url = Column(String(500))
    
    # Matching Criteria
    matching_criteria = Column(JSON, nullable=False)
    urgency_level = Column(PG_ENUM(UrgencyLevel, name="urgency_level_recip"), default="MEDIUM", index=True)
    urgency_reason = Column(Text)
    
    # HLA Typing
    hla_typing = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="recipient")
    requests = relationship("Request", back_populates="recipient")
    
    __table_args__ = (
        Index("idx_verified", "is_verified_by_hospital"),
    )


class Request(Base):
    """Blood/Organ Request"""
    __tablename__ = "requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String(36), ForeignKey("recipients.id"), nullable=False, index=True)
    
    # Request Details
    request_type = Column(PG_ENUM(RequestType, name="request_type"), nullable=False, index=True)
    blood_group_needed = Column(String(5))
    organ_type_needed = Column(String(50))
    quantity_needed = Column(Integer)
    
    # Urgency & Timeline
    urgency_level = Column(PG_ENUM(UrgencyLevel, name="urgency_level_req"), nullable=False, index=True)
    needed_by = Column(DateTime, nullable=False)
    
    # Status
    status = Column(
        PG_ENUM(RequestStatus, name="request_status"),
        default="OPEN",
        nullable=False,
        index=True
    )
    matched_donor_id = Column(String(36))
    matched_at = Column(DateTime)
    
    # Hospital
    hospital_location = Column(JSON, nullable=False)
    hospital_name = Column(String(255))
    receiving_doctor_name = Column(String(100))
    receiving_doctor_phone = Column(String(20))
    
    # Additional Info
    clinical_notes = Column(Text)
    required_tests = Column(JSON, default=[])
    additional_requirements = Column(Text)
    
    # Visibility
    is_public = Column(Boolean, default=False)
    shared_with_hospitals = Column(JSON, default=[])
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    fulfilled_at = Column(DateTime)
    
    # Relationships
    recipient = relationship("Recipient", back_populates="requests")
    matches = relationship("Match", back_populates="request", foreign_keys="Match.request_id")
    
    __table_args__ = (
        Index("idx_blood_organ_status", "blood_group_needed", "organ_type_needed", "status"),
    )


class Match(Base):
    """Donor-Request Matching"""
    __tablename__ = "matches"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True)
    donor_id = Column(String(36), ForeignKey("donors.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Match Score
    compatibility_score = Column(DECIMAL(5, 2), nullable=False, index=True)
    distance_km = Column(DECIMAL(10, 2), nullable=False)
    score_components = Column(JSON, nullable=False)
    
    # Status
    status = Column(
        PG_ENUM(MatchStatus, name="match_status"),
        default="SUGGESTED",
        nullable=False,
        index=True
    )
    
    # Donor Response
    donor_response = Column(PG_ENUM(DonorResponse, name="donor_response"), default="PENDING")
    donor_response_at = Column(DateTime)
    donor_response_reason = Column(Text)
    
    # Recipient Response
    recipient_response = Column(PG_ENUM(RecipientResponse, name="recipient_response"), default="PENDING")
    recipient_response_at = Column(DateTime)
    
    # Donation Execution
    appointment_scheduled_at = Column(DateTime)
    donation_completed_at = Column(DateTime)
    donation_failed_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    request = relationship("Request", back_populates="matches", foreign_keys=[request_id])
    donor = relationship("Donor", back_populates="matches", foreign_keys=[donor_id])
    
    __table_args__ = (
        UniqueConstraint("request_id", "donor_id", name="unique_request_donor"),
    )


class Notification(Base):
    """Real-Time Notifications"""
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Type
    notification_type = Column(
        PG_ENUM(NotificationType, name="notification_type_enum"),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related Entity
    related_entity_type = Column(String(50))
    related_entity_id = Column(String(36))
    
    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime)
    
    # Delivery
    deliver_via = Column(JSON, default=["IN_APP"])
    email_sent = Column(Boolean, default=False)
    sms_sent = Column(Boolean, default=False)
    push_sent = Column(Boolean, default=False)
    
    # Retry
    delivery_attempts = Column(Integer, default=0)
    last_delivery_attempt = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        Index("idx_user_unread", "user_id", "is_read"),
    )


class AdminAction(Base):
    """Admin Actions Audit Trail"""
    __tablename__ = "admin_actions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Action
    action_type = Column(
        PG_ENUM(AdminActionType, name="admin_action_type_enum"),
        nullable=False,
        index=True
    )
    target_entity_type = Column(String(50), nullable=False)
    target_entity_id = Column(String(36), nullable=False, index=True)
    
    # Decision
    decision = Column(Text)
    reason = Column(Text)
    evidence_urls = Column(JSON, default=[])
    
    # Status
    status = Column(PG_ENUM(ActionStatus, name="action_status"), default="APPROVED")
    status_updated_by = Column(String(36), ForeignKey("users.id"))
    status_updated_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    action_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = relationship("User", back_populates="admin_actions", foreign_keys=[admin_id])
    
    __table_args__ = (
        Index("idx_admin_action_type", "admin_id", "action_type"),
    )


class Analytics(Base):
    """Daily Analytics & Metrics"""
    __tablename__ = "analytics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(String(10), unique=True, nullable=False, index=True)
    
    # Donors & Recipients
    total_donors = Column(Integer, default=0)
    total_recipients = Column(Integer, default=0)
    active_donors = Column(Integer, default=0)
    active_recipients = Column(Integer, default=0)
    
    # Requests
    new_requests = Column(Integer, default=0)
    fulfilled_requests = Column(Integer, default=0)
    pending_requests = Column(Integer, default=0)
    
    # Matches
    total_matches = Column(Integer, default=0)
    successful_matches = Column(Integer, default=0)
    match_success_rate = Column(DECIMAL(5, 2))
    
    # Blood Metrics
    blood_requests = Column(Integer, default=0)
    blood_fulfilled = Column(Integer, default=0)
    
    # Organ Metrics
    organ_requests = Column(Integer, default=0)
    organ_fulfilled = Column(Integer, default=0)
    
    # Response Times
    avg_response_time_minutes = Column(Integer)
    avg_matching_time_minutes = Column(Integer)
    
    # Geographic
    top_requesting_city = Column(String(100))
    top_donor_city = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
