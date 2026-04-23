# Pydantic Schemas - Request/Response Validation
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================
class RoleEnum(str, Enum):
    DONOR = "DONOR"
    RECIPIENT = "RECIPIENT"
    ADMIN = "ADMIN"


class UrgencyEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"


class RequestTypeEnum(str, Enum):
    BLOOD = "BLOOD"
    ORGAN = "ORGAN"
    PLASMA = "PLASMA"


class RequestStatusEnum(str, Enum):
    OPEN = "OPEN"
    MATCHED = "MATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class BloodGroupEnum(str, Enum):
    O_PLUS = "O+"
    O_MINUS = "O-"
    A_PLUS = "A+"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B_MINUS = "B-"
    AB_PLUS = "AB+"
    AB_MINUS = "AB-"


# ==================== AUTH SCHEMAS ====================
class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: RoleEnum
    
    @validator("password")
    def password_strong(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        if not any(c in "!@#$%^&*" for c in v):
            raise ValueError("Password must contain special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class VerifyPhoneRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


# ==================== USER PROFILE SCHEMAS ====================
class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    blood_group: Optional[BloodGroupEnum] = None
    allergies: Optional[str] = None
    chronic_diseases: Optional[str] = None
    current_medications: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class ProfileResponse(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    gender: Optional[str]
    city: str
    blood_group: Optional[BloodGroupEnum]
    profile_photo_url: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: str
    email: str
    phone: str
    username: str
    role: RoleEnum
    email_verified: bool
    phone_verified: bool
    id_verified: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== DONOR SCHEMAS ====================
class DonorRegisterRequest(BaseModel):
    can_donate_blood: bool = False
    blood_donation_last_date: Optional[str] = None
    organ_types: Optional[List[str]] = []
    organ_donation_registered: bool = False
    organ_registration_certificate_url: Optional[str] = None
    willing_hospital_list: Optional[List[str]] = []
    preferred_donation_time: Optional[str] = None
    medical_clearance_report_url: Optional[str] = None


class DonorUpdateRequest(BaseModel):
    is_available: Optional[bool] = None
    can_donate_blood: Optional[bool] = None
    organ_types: Optional[List[str]] = None
    willing_hospital_list: Optional[List[str]] = None
    preferred_donation_time: Optional[str] = None


class DonorResponse(BaseModel):
    id: str
    user_id: str
    is_available: bool
    can_donate_blood: bool
    blood_donation_eligible_date: Optional[str]
    organ_types: List[str]
    blood_donations_count: int
    lives_saved: int
    medical_clearance: bool
    
    class Config:
        from_attributes = True


class DonorListResponse(BaseModel):
    donor_id: str
    first_name: str
    city: str
    blood_group: Optional[BloodGroupEnum]
    distance_km: float
    is_available: bool
    organ_types: List[str]
    rating: Optional[float] = 4.8


# ==================== RECIPIENT SCHEMAS ====================
class RecipientRegisterRequest(BaseModel):
    primary_disease: str
    diagnosis_date: str
    surgery_needed_date: str
    hospital_name: str
    hospital_contact_phone: str
    doctor_name: str
    doctor_phone: str
    doctor_registration_number: str
    hospital_verification_document_url: Optional[str] = None
    is_hospital_case: bool = True
    matching_criteria: Dict[str, Any]


class RecipientUpdateRequest(BaseModel):
    primary_disease: Optional[str] = None
    surgery_needed_date: Optional[str] = None
    urgency_level: Optional[UrgencyEnum] = None
    matching_criteria: Optional[Dict[str, Any]] = None


class RecipientResponse(BaseModel):
    id: str
    user_id: str
    primary_disease: str
    hospital_name: str
    doctor_name: str
    urgency_level: UrgencyEnum
    is_verified_by_hospital: bool
    
    class Config:
        from_attributes = True


# ==================== REQUEST SCHEMAS ====================
class HospitalLocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str


class BloodRequestCreateRequest(BaseModel):
    request_type: RequestTypeEnum = RequestTypeEnum.BLOOD
    blood_group_needed: BloodGroupEnum
    quantity_needed: int = Field(..., ge=1)
    urgency_level: UrgencyEnum
    needed_by: datetime
    hospital_location: HospitalLocationRequest
    hospital_name: str
    receiving_doctor_name: str
    receiving_doctor_phone: str
    clinical_notes: Optional[str] = None
    required_tests: Optional[List[str]] = []
    is_public: bool = False


class OrganRequestCreateRequest(BaseModel):
    request_type: RequestTypeEnum = RequestTypeEnum.ORGAN
    organ_type_needed: str
    urgency_level: UrgencyEnum
    needed_by: datetime
    hospital_location: HospitalLocationRequest
    hospital_name: str
    receiving_doctor_name: str
    receiving_doctor_phone: str
    clinical_notes: Optional[str] = None
    required_tests: Optional[List[str]] = []
    is_public: bool = False


class RequestResponse(BaseModel):
    id: str
    request_type: RequestTypeEnum
    blood_group_needed: Optional[str]
    organ_type_needed: Optional[str]
    urgency_level: UrgencyEnum
    status: RequestStatusEnum
    hospital_name: str
    created_at: datetime
    needed_by: datetime
    matches_found: int = 0
    
    class Config:
        from_attributes = True


class RequestListResponse(BaseModel):
    request_id: str
    request_type: RequestTypeEnum
    urgency_level: UrgencyEnum
    status: RequestStatusEnum
    hospital_name: str
    created_at: datetime
    matches_found: int


# ==================== MATCH SCHEMAS ====================
class MatchResponse(BaseModel):
    match_id: str
    donor_id: str
    donor_name: str
    distance_km: float
    compatibility_score: float
    status: str
    donor_response: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MatchAcceptRequest(BaseModel):
    appointment_preferred_date: str
    appointment_preferred_time: str
    notes: Optional[str] = None


class MatchRejectRequest(BaseModel):
    reason: str
    details: Optional[str] = None


# ==================== NOTIFICATION SCHEMAS ====================
class NotificationResponse(BaseModel):
    notification_id: str
    notification_type: str
    title: str
    message: str
    is_read: bool
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== ADMIN SCHEMAS ====================
class UserListItemResponse(BaseModel):
    user_id: str
    email: str
    phone: str
    role: RoleEnum
    email_verified: bool
    phone_verified: bool
    id_verified: bool
    is_active: bool
    created_at: datetime
    registration_status: str


class VerifyUserRequest(BaseModel):
    verified: bool
    notes: str


class BlockUserRequest(BaseModel):
    reason: str = Field(..., max_length=500)
    details: Optional[str] = None


class AdminRequestActionRequest(BaseModel):
    reason: str = Field(default="Reviewed and approved by admin", max_length=500)
    details: Optional[str] = None


class AnalyticsResponse(BaseModel):
    period: Dict[str, str]
    metrics: Dict[str, Any]
    blood_metrics: Dict[str, Any]
    organ_metrics: Dict[str, Any]
    
    class Config:
        from_attributes = True


# ==================== ERROR RESPONSE ====================
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    error: Dict[str, Any] = Field(..., example={
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": [{"field": "email", "message": "Invalid email format"}],
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": "req_123456"
    })


# ==================== SUCCESS RESPONSE ====================
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
