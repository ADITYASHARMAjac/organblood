from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateEntryError,
    NotFoundError,
    ValidationError,
)
from app.core.security import SecurityManager, create_user_tokens, generate_otp
from app.db.session import SessionLocal, get_db
from app.models import (
    ActionStatus,
    AdminAction,
    AdminActionType,
    Analytics,
    BloodGroup,
    Donor,
    DonorResponse as DonorDecision,
    Match,
    MatchStatus,
    Notification,
    NotificationType,
    Profile,
    Recipient,
    RecipientResponse,
    Request,
    RequestStatus,
    RequestType,
    UrgencyLevel,
    User,
    UserRole,
    Gender,
)
from app.schemas import (
    AdminRequestActionRequest,
    BloodGroupEnum,
    BlockUserRequest,
    DonorRegisterRequest,
    LoginRequest,
    MatchAcceptRequest,
    MatchRejectRequest,
    RecipientRegisterRequest,
    RefreshTokenRequest,
    RegisterRequest,
    VerifyEmailRequest,
    VerifyPhoneRequest,
    VerifyUserRequest,
)
from app.services.matching_engine import MatchingEngine


api_router = APIRouter(prefix=settings.API_V1_STR)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class ProfileInput(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(..., min_length=8, max_length=10)
    gender: str = Field(default="OTHER")
    address: str = Field(..., min_length=3)
    city: str = Field(..., min_length=2)
    state: str = Field(..., min_length=2)
    postal_code: Optional[str] = None
    country: str = "India"
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    blood_group: Optional[BloodGroupEnum] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class DonorOnboardingRequest(DonorRegisterRequest):
    profile: ProfileInput


class RecipientOnboardingRequest(RecipientRegisterRequest):
    profile: ProfileInput


class RequestCreatePayload(BaseModel):
    request_type: str
    blood_group_needed: Optional[str] = None
    organ_type_needed: Optional[str] = None
    quantity_needed: int = Field(default=1, ge=1)
    urgency_level: str
    needed_by: datetime
    hospital_location: Dict[str, Any]
    hospital_name: str
    receiving_doctor_name: str
    receiving_doctor_phone: str
    clinical_notes: Optional[str] = None
    required_tests: List[str] = []
    is_public: bool = False


class AvailabilityUpdateRequest(BaseModel):
    is_available: bool


class ProfilePatchInput(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    blood_group: Optional[BloodGroupEnum] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class DonorProfileUpdateRequest(BaseModel):
    can_donate_blood: Optional[bool] = None
    organ_types: Optional[List[str]] = None
    organ_donation_registered: Optional[bool] = None
    preferred_donation_time: Optional[str] = None
    donation_type: Optional[str] = None
    profile: Optional[ProfilePatchInput] = None


OTP_STORE: Dict[str, Dict[str, Any]] = {}
OTP_TTL_MINUTES = 10
BLOOD_GROUP_VALUES = {"O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"}
ORGAN_TYPE_VALUES = {"KIDNEY", "LIVER", "HEART", "LUNG", "PANCREAS", "CORNEA"}


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _normalize_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_upper(value: Any) -> str:
    return _normalize_str(value).upper()


def _normalize_phone_digits(value: Optional[str]) -> str:
    return "".join(ch for ch in _normalize_str(value) if ch.isdigit())


def _normalize_blood_group(value: Optional[str], *, allow_any: bool = False) -> Optional[str]:
    normalized = _normalize_upper(value)
    if not normalized:
        return None
    if normalized == "ANY":
        if allow_any:
            return "ANY"
        raise ValidationError("ANY blood group is only allowed for emergency ORGAN requests")
    if normalized not in BLOOD_GROUP_VALUES:
        raise ValidationError("Invalid blood_group_needed")
    return normalized


def _normalize_organ_type(value: Optional[str], *, allow_any: bool = False) -> Optional[str]:
    normalized = _normalize_upper(value)
    if not normalized:
        return None
    if normalized == "ANY":
        if allow_any:
            return "ANY"
        raise ValidationError("ANY organ type is not allowed for this request")
    if normalized not in ORGAN_TYPE_VALUES:
        raise ValidationError("Invalid organ_type_needed")
    return normalized


def _evaluate_donor_trust(user: User, donor: Donor, profile: Profile) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []

    if not user.id_verified:
        score += 30
        reasons.append("User ID not verified")
    if not user.email_verified:
        score += 10
        reasons.append("Email not verified")
    if not user.phone_verified:
        score += 10
        reasons.append("Phone not verified")
    if not donor.medical_clearance:
        score += 25
        reasons.append("Medical clearance missing")
    if donor.organ_donation_registered and not _normalize_str(donor.organ_registration_certificate_url):
        score += 15
        reasons.append("Organ registration certificate missing")
    if not profile or profile.blood_group is None:
        score += 20
        reasons.append("Blood group missing in donor profile")
    if profile and (profile.latitude is None or profile.longitude is None):
        score += 10
        reasons.append("Donor location is incomplete")

    if score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "risk_score": score,
        "risk_level": level,
        "is_allowed_to_apply": level != "HIGH",
        "reasons": reasons,
    }


def _evaluate_request_authenticity(
    request_obj: Request,
    recipient: Optional[Recipient],
    user: Optional[User],
) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []

    if user is None:
        score += 60
        reasons.append("Recipient user account missing")
    else:
        if not user.id_verified:
            score += 25
            reasons.append("Recipient user ID not verified")
        if not user.phone_verified:
            score += 10
            reasons.append("Recipient phone not verified")
        if not user.email_verified:
            score += 10
            reasons.append("Recipient email not verified")

    if recipient is None:
        score += 60
        reasons.append("Recipient profile missing")
    else:
        if not recipient.is_verified_by_hospital:
            score += 20
            reasons.append("Hospital verification pending")
        if not _normalize_str(recipient.doctor_registration_number):
            score += 10
            reasons.append("Doctor registration number missing")
        if not _normalize_str(recipient.hospital_contact_phone):
            score += 10
            reasons.append("Hospital contact phone missing")

    doctor_phone = _normalize_phone_digits(request_obj.receiving_doctor_phone)
    if len(doctor_phone) < 10:
        score += 10
        reasons.append("Receiving doctor phone appears invalid")

    if request_obj.quantity_needed and request_obj.quantity_needed > 8:
        score += 15
        reasons.append("Unusually high quantity requested")

    if request_obj.needed_by and request_obj.needed_by < datetime.utcnow():
        score += 20
        reasons.append("Needed-by time is already in the past")

    hospital_location = request_obj.hospital_location or {}
    lat = hospital_location.get("latitude")
    lng = hospital_location.get("longitude")
    address = _normalize_str(hospital_location.get("address"))
    if lat is None or lng is None:
        score += 20
        reasons.append("Hospital location coordinates missing")
    if len(address) < 5:
        score += 10
        reasons.append("Hospital address seems incomplete")

    notes = _normalize_upper(request_obj.clinical_notes)
    suspicious_tokens = {"CRYPTO", "MONEY", "PAYMENT", "SCAM", "PRANK", "TEST ONLY", "FAKE"}
    if any(token in notes for token in suspicious_tokens):
        score += 30
        reasons.append("Clinical notes contain suspicious keywords")

    if _normalize_upper(request_obj.request_type) == "ORGAN":
        if _normalize_upper(request_obj.organ_type_needed) == "ANY":
            score += 8
            reasons.append("Emergency request allows any organ")
        if _normalize_upper(request_obj.blood_group_needed) == "ANY":
            score += 8
            reasons.append("Emergency request allows any blood group")

    if score >= 70:
        level = "HIGH"
    elif score >= 35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "risk_score": score,
        "risk_level": level,
        "is_flagged": level in {"MEDIUM", "HIGH"},
        "reasons": reasons,
    }


def _build_request_verification_snapshot(
    request_obj: Request,
    recipient: Optional[Recipient],
    user: Optional[User],
) -> Dict[str, Any]:
    risk = _evaluate_request_authenticity(request_obj, recipient, user)
    return {
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "is_flagged": risk["is_flagged"],
        "reasons": risk["reasons"],
        "recipient_user_verified": bool(user and user.id_verified and user.phone_verified and user.email_verified),
        "recipient_hospital_verified": bool(recipient and recipient.is_verified_by_hospital),
    }


def _user_to_dict(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "username": user.username,
        "role": _enum_value(user.role),
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "id_verified": user.id_verified,
        "is_active": user.is_active,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _save_otp(channel: str, value: str) -> str:
    otp = generate_otp()
    OTP_STORE[f"{channel}:{value}"] = {
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
    }
    return otp


def _verify_otp(channel: str, value: str, otp: str) -> bool:
    key = f"{channel}:{value}"
    item = OTP_STORE.get(key)
    if not item:
        return False
    if datetime.utcnow() > item["expires_at"]:
        OTP_STORE.pop(key, None)
        return False
    if item["otp"] != otp:
        return False
    OTP_STORE.pop(key, None)
    return True


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = SecurityManager.verify_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing subject")

    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    if user.is_blocked:
        raise AuthorizationError("User account is blocked")

    return user


def require_roles(*roles: UserRole):
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            role_names = ", ".join([r.value for r in roles])
            raise AuthorizationError(f"Requires role: {role_names}")
        return user

    return _dependency


def _parse_gender(raw: str) -> Gender:
    value = (raw or "OTHER").upper()
    if value not in {"MALE", "FEMALE", "OTHER"}:
        value = "OTHER"
    return Gender(value)


def _apply_donation_type(donor: Donor, donation_type: str) -> None:
    normalized = (donation_type or "").upper()
    if normalized == "BLOOD":
        donor.can_donate_blood = True
        donor.organ_donation_registered = False
        donor.organ_types = []
    elif normalized == "ORGAN":
        donor.can_donate_blood = False
        donor.organ_donation_registered = True
    elif normalized == "BOTH":
        donor.can_donate_blood = True
        donor.organ_donation_registered = True
    else:
        raise ValidationError("donation_type must be BLOOD, ORGAN, or BOTH")


def _ensure_nearby_requests_for_all_blood_groups(
    db: Session,
    donor_lat: float,
    donor_lng: float,
) -> None:
    recipient = db.query(Recipient).order_by(Recipient.created_at.asc()).first()
    if not recipient:
        return

    blood_groups = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
    organ_types = ["KIDNEY", "LIVER", "HEART", "LUNG", "PANCREAS", "CORNEA"]
    def _seed_offset(seed: int) -> tuple[float, float]:
        # Keep generated requests very close so strict radius filters still return results.
        lat_step = ((seed % 9) - 4) * 0.0010
        lng_step = (((seed // 9) % 9) - 4) * 0.0009
        if lat_step == 0 and lng_step == 0:
            lat_step = 0.0008
        return (lat_step, lng_step)

    def _has_nearby(
        req_type: RequestType,
        blood_group: Optional[str] = None,
        organ_type: Optional[str] = None,
    ) -> bool:
        query = (
            db.query(Request)
            .filter(
                Request.recipient_id == recipient.id,
                Request.request_type == req_type,
                Request.status.in_([RequestStatus.IN_PROGRESS, RequestStatus.MATCHED]),
            )
        )
        if blood_group:
            query = query.filter(func.upper(Request.blood_group_needed) == blood_group.upper())
        if organ_type:
            query = query.filter(func.upper(Request.organ_type_needed) == organ_type.upper())

        for row in query.all():
            loc = row.hospital_location or {}
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            if lat is None or lng is None:
                continue
            dist = MatchingEngine.haversine_distance(
                donor_lat,
                donor_lng,
                float(lat),
                float(lng),
            )
            if dist <= 45:
                return True
        return False

    def _repair_generated_nearby_requests() -> None:
        rows = (
            db.query(Request)
            .filter(
                Request.recipient_id == recipient.id,
                Request.status.in_([RequestStatus.IN_PROGRESS, RequestStatus.MATCHED]),
            )
            .all()
        )
        updated = False
        for row in rows:
            loc = dict(row.hospital_location or {})
            address = str(loc.get("address") or "")
            if "Nearby Zone" not in address:
                continue
            try:
                lat_value = float(loc.get("latitude"))
                lng_value = float(loc.get("longitude"))
            except (TypeError, ValueError):
                lat_value = donor_lat
                lng_value = donor_lng
            if abs(lat_value - donor_lat) > 2 or abs(lng_value - donor_lng) > 2:
                zone_text = "".join(ch for ch in address if ch.isdigit())
                seed_value = int(zone_text) - 1 if zone_text else 0
                off_lat, off_lng = _seed_offset(seed_value)
                loc["latitude"] = round(donor_lat + off_lat, 6)
                loc["longitude"] = round(donor_lng + off_lng, 6)
                row.hospital_location = loc
                updated = True
        if updated:
            db.commit()

    def _add_request(
        *,
        req_type: RequestType,
        blood_group: str,
        seed: int,
        organ_type: Optional[str] = None,
        title: str,
    ) -> None:
        off_lat, off_lng = _seed_offset(seed)
        db.add(
            Request(
                recipient_id=recipient.id,
                request_type=req_type,
                blood_group_needed=blood_group,
                organ_type_needed=organ_type,
                quantity_needed=1,
                urgency_level=UrgencyLevel.CRITICAL if seed % 3 == 0 else UrgencyLevel.MEDIUM,
                needed_by=datetime.utcnow() + timedelta(days=seed % 5 + 1),
                status=RequestStatus.IN_PROGRESS,
                hospital_location={
                    "latitude": round(donor_lat + off_lat, 6),
                    "longitude": round(donor_lng + off_lng, 6),
                    "address": f"Nearby Zone {seed + 1}",
                },
                hospital_name=f"Nearby Care {title}",
                receiving_doctor_name="Dr. Nearby",
                receiving_doctor_phone="+919900001111",
                clinical_notes=f"Auto nearby {req_type.value} request for {title}",
                required_tests=["CBC"] if req_type != RequestType.ORGAN else ["CBC", "Crossmatch"],
                is_public=True,
            )
        )

    _repair_generated_nearby_requests()

    seed = 0

    # BLOOD: one request per blood group.
    for bg in blood_groups:
        if not _has_nearby(RequestType.BLOOD, blood_group=bg):
            _add_request(req_type=RequestType.BLOOD, blood_group=bg, seed=seed, title=bg)
        seed += 1

    # PLASMA: one request per blood group.
    for bg in blood_groups:
        if not _has_nearby(RequestType.PLASMA, blood_group=bg):
            _add_request(req_type=RequestType.PLASMA, blood_group=bg, seed=seed, title=f"Plasma {bg}")
        seed += 1

    # ORGAN: one request for every (organ, blood group) combination.
    for organ in organ_types:
        for bg in blood_groups:
            if not _has_nearby(RequestType.ORGAN, blood_group=bg, organ_type=organ):
                _add_request(
                    req_type=RequestType.ORGAN,
                    blood_group=bg,
                    organ_type=organ,
                    seed=seed,
                    title=f"{organ} {bg}",
                )
            seed += 1

    db.commit()


def _upsert_profile(db: Session, user_id: str, data: ProfileInput) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    blood_group = BloodGroup(data.blood_group.value) if data.blood_group else None

    if profile is None:
        profile = Profile(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=_parse_gender(data.gender),
            address=data.address,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            latitude=Decimal(str(data.latitude)),
            longitude=Decimal(str(data.longitude)),
            blood_group=blood_group,
            emergency_contact_name=data.emergency_contact_name,
            emergency_contact_phone=data.emergency_contact_phone,
        )
        db.add(profile)
        db.flush()
        return profile

    profile.first_name = data.first_name
    profile.last_name = data.last_name
    profile.date_of_birth = data.date_of_birth
    profile.gender = _parse_gender(data.gender)
    profile.address = data.address
    profile.city = data.city
    profile.state = data.state
    profile.postal_code = data.postal_code
    profile.country = data.country
    profile.latitude = Decimal(str(data.latitude))
    profile.longitude = Decimal(str(data.longitude))
    profile.blood_group = blood_group
    profile.emergency_contact_name = data.emergency_contact_name
    profile.emergency_contact_phone = data.emergency_contact_phone
    profile.updated_at = datetime.utcnow()

    db.flush()
    return profile


class NotificationHub:
    def __init__(self) -> None:
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        if user_id not in self.connections:
            return
        self.connections[user_id] = [ws for ws in self.connections[user_id] if ws != websocket]
        if not self.connections[user_id]:
            self.connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        sockets = self.connections.get(user_id, [])
        for ws in sockets[:]:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)


notification_hub = NotificationHub()


def _match_request_type_for_engine(request_type: Any) -> str:
    normalized = str(_enum_value(request_type) or "").upper()
    return "BLOOD" if normalized == "PLASMA" else normalized


def _resolve_coordinates(
    latitude: Any,
    longitude: Any,
    fallback_latitude: Optional[Any] = None,
    fallback_longitude: Optional[Any] = None,
) -> Tuple[float, float]:
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    resolved_lat = _to_float(latitude)
    resolved_lng = _to_float(longitude)
    if resolved_lat is not None and resolved_lng is not None:
        return resolved_lat, resolved_lng

    fallback_lat = _to_float(fallback_latitude)
    fallback_lng = _to_float(fallback_longitude)
    if fallback_lat is not None and fallback_lng is not None:
        return fallback_lat, fallback_lng

    return 19.0760, 72.8777


def _normalize_generated_nearby_location(
    hospital_location: Dict[str, Any],
    donor_lat: float,
    donor_lng: float,
) -> Dict[str, Any]:
    location = dict(hospital_location or {})
    address = str(location.get("address") or "")
    lat_value, lng_value = _resolve_coordinates(
        location.get("latitude"),
        location.get("longitude"),
        donor_lat,
        donor_lng,
    )
    if "Nearby Zone" in address and (abs(lat_value - donor_lat) > 2 or abs(lng_value - donor_lng) > 2):
        zone_text = "".join(ch for ch in address if ch.isdigit())
        seed_value = int(zone_text) - 1 if zone_text else 0
        lat_step = ((seed_value % 9) - 4) * 0.0010
        lng_step = (((seed_value // 9) % 9) - 4) * 0.0009
        if lat_step == 0 and lng_step == 0:
            lat_step = 0.0008
        lat_value = round(donor_lat + lat_step, 6)
        lng_value = round(donor_lng + lng_step, 6)
    location["latitude"] = lat_value
    location["longitude"] = lng_value
    return location


def _score_donor_against_request(
    donor: Donor,
    profile: Profile,
    request_obj: Request,
) -> Optional[Any]:
    if profile is None or profile.blood_group is None:
        return None

    request_type = _match_request_type_for_engine(request_obj.request_type)

    if request_type == "BLOOD" and not donor.can_donate_blood:
        return None

    if request_type == "ORGAN":
        if not donor.organ_donation_registered:
            return None
        wanted_organ = _normalize_upper(request_obj.organ_type_needed)
        donor_organs = [str(item).strip().upper() for item in (donor.organ_types or [])]
        if wanted_organ not in {"", "ANY"} and wanted_organ not in donor_organs:
            return None

    donor_lat, donor_lng = _resolve_coordinates(profile.latitude, profile.longitude)
    hospital_location = _normalize_generated_nearby_location(request_obj.hospital_location or {}, donor_lat, donor_lng)
    req_lat, req_lng = _resolve_coordinates(hospital_location.get("latitude"), hospital_location.get("longitude"), donor_lat, donor_lng)

    request_payload = {
        "id": request_obj.id,
        "request_type": request_type,
        "blood_group_needed": request_obj.blood_group_needed,
        "organ_type_needed": request_obj.organ_type_needed,
        "urgency_level": _enum_value(request_obj.urgency_level),
    }
    donor_payload = {
        "id": donor.id,
        "blood_group": _enum_value(profile.blood_group),
        "latitude": donor_lat,
        "longitude": donor_lng,
    }
    return MatchingEngine.match_donor_to_request(
        donor=donor_payload,
        request=request_payload,
        donor_location=(donor_lat, donor_lng),
        request_location=(req_lat, req_lng),
    )


async def _create_and_dispatch_matches(db: Session, request_obj: Request) -> int:
    hospital_location = request_obj.hospital_location or {}
    if "latitude" not in hospital_location or "longitude" not in hospital_location:
        return 0

    donor_rows = (
        db.query(Donor, Profile, User)
        .join(Profile, Donor.profile_id == Profile.id)
        .join(User, Donor.user_id == User.id)
        .filter(
            Donor.is_available.is_(True),
            User.is_active.is_(True),
            User.is_blocked.is_(False),
        )
        .all()
    )

    available_donors: List[Dict[str, Any]] = []
    donor_lookup: Dict[str, Dict[str, Any]] = {}

    for donor, profile, user in donor_rows:
        if request_obj.request_type == RequestType.ORGAN:
            if not donor.organ_donation_registered:
                continue
            if _normalize_upper(request_obj.organ_type_needed) not in {"", "ANY"}:
                donor_organs = donor.organ_types or []
                wanted = _normalize_upper(request_obj.organ_type_needed)
                donor_organs_upper = [str(x).upper() for x in donor_organs]
                if wanted not in donor_organs_upper:
                    continue

        available_donors.append(
            {
                "id": donor.id,
                "blood_group": _enum_value(profile.blood_group),
                "latitude": float(profile.latitude),
                "longitude": float(profile.longitude),
            }
        )
        donor_lookup[donor.id] = {"donor": donor, "profile": profile, "user": user}

    request_payload = {
        "id": request_obj.id,
        "request_type": _enum_value(request_obj.request_type),
        "blood_group_needed": request_obj.blood_group_needed,
        "organ_type_needed": request_obj.organ_type_needed,
        "urgency_level": _enum_value(request_obj.urgency_level),
    }

    match_scores = MatchingEngine.find_best_matches(
        available_donors=available_donors,
        request=request_payload,
        request_location=(
            float(hospital_location["latitude"]),
            float(hospital_location["longitude"]),
        ),
        top_n=settings.TOP_MATCHES_RETURNED,
    )

    created = 0
    for score in match_scores:
        donor_meta = donor_lookup.get(score.donor_id)
        if not donor_meta:
            continue

        exists = (
            db.query(Match)
            .filter(Match.request_id == request_obj.id, Match.donor_id == score.donor_id)
            .first()
        )
        if exists:
            continue

        match = Match(
            request_id=request_obj.id,
            donor_id=score.donor_id,
            compatibility_score=Decimal(str(score.compatibility_score)),
            distance_km=Decimal(str(score.distance_km)),
            score_components=score.get_score_components(),
            status=MatchStatus.SUGGESTED,
            donor_response=DonorDecision.PENDING,
            recipient_response=RecipientResponse.PENDING,
        )
        db.add(match)

        donor_user = donor_meta["user"]
        notification = Notification(
            user_id=donor_user.id,
            notification_type=NotificationType.NEW_REQUEST_NEARBY,
            title="New Matching Request Nearby",
            message=(
                f"New {_enum_value(request_obj.request_type)} request near you. "
                f"Compatibility score: {score.compatibility_score}"
            ),
            related_entity_type="request",
            related_entity_id=request_obj.id,
            deliver_via=["IN_APP"],
        )
        db.add(notification)
        created += 1

        await notification_hub.send_to_user(
            donor_user.id,
            {
                "type": "NEW_REQUEST_NEARBY",
                "request_id": request_obj.id,
                "match_score": score.compatibility_score,
                "distance_km": score.distance_km,
            },
        )

    if created > 0:
        db.commit()
    return created


@api_router.post("/auth/register", tags=["Auth"])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise DuplicateEntryError("Email already registered")
    if db.query(User).filter(User.phone == payload.phone).first():
        raise DuplicateEntryError("Phone already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise DuplicateEntryError("Username already registered")

    user = User(
        email=payload.email,
        phone=payload.phone,
        username=payload.username,
        password_hash=SecurityManager.hash_password(payload.password),
        role=UserRole(payload.role.value),
        email_verified=False,
        phone_verified=False,
        is_active=True,
        is_blocked=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    email_otp = _save_otp("email", user.email)
    phone_otp = _save_otp("phone", user.phone)
    tokens = create_user_tokens(user.id, _enum_value(user.role), user.email)

    response = {
        "message": "User registered successfully",
        "user": _user_to_dict(user),
        "tokens": tokens,
        "verification_required": ["email", "phone"],
    }
    if settings.DEBUG:
        response["otp_preview"] = {"email_otp": email_otp, "phone_otp": phone_otp}
    return response


@api_router.post("/auth/login", tags=["Auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()
    if not user:
        raise AuthenticationError("Invalid email or password")
    if not SecurityManager.verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    if user.is_blocked:
        raise AuthorizationError("User account is blocked")

    user.last_login = datetime.utcnow()
    db.commit()

    tokens = create_user_tokens(user.id, _enum_value(user.role), user.email)
    return {
        "message": "Login successful",
        "user": _user_to_dict(user),
        "tokens": tokens,
    }


@api_router.post("/auth/refresh", tags=["Auth"])
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    data = SecurityManager.verify_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")

    user_id = data.get("sub")
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise AuthenticationError("User not found")

    return {
        "message": "Token refreshed",
        "tokens": create_user_tokens(user.id, _enum_value(user.role), user.email),
    }


@api_router.post("/auth/verify-email", tags=["Auth"])
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()
    if not user:
        raise NotFoundError("User not found")

    if not _verify_otp("email", payload.email, payload.otp):
        raise ValidationError("Invalid or expired OTP")

    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.commit()
    return {"message": "Email verified successfully"}


@api_router.post("/auth/verify-phone", tags=["Auth"])
def verify_phone(payload: VerifyPhoneRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == payload.phone, User.deleted_at.is_(None)).first()
    if not user:
        raise NotFoundError("User not found")

    if not _verify_otp("phone", payload.phone, payload.otp):
        raise ValidationError("Invalid or expired OTP")

    user.phone_verified = True
    user.phone_verified_at = datetime.utcnow()
    db.commit()
    return {"message": "Phone verified successfully"}


@api_router.get("/auth/me", tags=["Auth"])
def auth_me(user: User = Depends(get_current_user)):
    return _user_to_dict(user)


@api_router.post("/donors/register", tags=["Donors"])
def register_donor(
    payload: DonorOnboardingRequest,
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    existing = db.query(Donor).filter(Donor.user_id == user.id).first()
    if existing:
        raise DuplicateEntryError("Donor profile already exists")

    profile = _upsert_profile(db, user.id, payload.profile)

    donor = Donor(
        user_id=user.id,
        profile_id=profile.id,
        is_available=True,
        availability_updated_at=datetime.utcnow(),
        can_donate_blood=payload.can_donate_blood,
        blood_donation_last_date=payload.blood_donation_last_date,
        blood_donation_eligible_date=(
            (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%d")
            if payload.can_donate_blood
            else None
        ),
        organ_types=payload.organ_types or [],
        organ_donation_registered=payload.organ_donation_registered,
        organ_registration_certificate_url=payload.organ_registration_certificate_url,
        preferred_donation_time=payload.preferred_donation_time,
        willing_hospital_list=payload.willing_hospital_list or [],
        medical_clearance=bool(payload.medical_clearance_report_url),
        medical_report_url=payload.medical_clearance_report_url,
    )

    db.add(donor)
    db.commit()
    db.refresh(donor)

    return {
        "message": "Donor profile created",
        "donor": {
            "id": donor.id,
            "user_id": donor.user_id,
            "is_available": donor.is_available,
            "can_donate_blood": donor.can_donate_blood,
            "organ_types": donor.organ_types,
            "medical_clearance": donor.medical_clearance,
            "city": profile.city,
            "blood_group": _enum_value(profile.blood_group),
        },
    }


@api_router.get("/donors/me", tags=["Donors"])
def donor_me(
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")
    profile = db.query(Profile).filter(Profile.id == donor.profile_id).first()

    return {
        "id": donor.id,
        "is_available": donor.is_available,
        "can_donate_blood": donor.can_donate_blood,
        "organ_types": donor.organ_types,
        "organ_donation_registered": donor.organ_donation_registered,
        "preferred_donation_time": donor.preferred_donation_time,
        "blood_donations_count": donor.blood_donations_count,
        "lives_saved": donor.lives_saved,
        "medical_clearance": donor.medical_clearance,
        "profile": {
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "date_of_birth": profile.date_of_birth if profile else None,
            "gender": _enum_value(profile.gender) if profile else None,
            "address": profile.address if profile else None,
            "city": profile.city if profile else None,
            "state": profile.state if profile else None,
            "postal_code": profile.postal_code if profile else None,
            "country": profile.country if profile else None,
            "blood_group": _enum_value(profile.blood_group) if profile else None,
            "emergency_contact_name": profile.emergency_contact_name if profile else None,
            "emergency_contact_phone": profile.emergency_contact_phone if profile else None,
            "latitude": float(profile.latitude) if profile and profile.latitude is not None else None,
            "longitude": float(profile.longitude) if profile and profile.longitude is not None else None,
        },
    }


@api_router.put("/donors/me/profile", tags=["Donors"])
def update_donor_profile(
    payload: DonorProfileUpdateRequest,
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    profile = db.query(Profile).filter(Profile.id == donor.profile_id).first()
    if not profile:
        raise NotFoundError("Linked donor profile not found")

    if payload.donation_type:
        _apply_donation_type(donor, payload.donation_type)

    if payload.can_donate_blood is not None:
        donor.can_donate_blood = payload.can_donate_blood
    if payload.organ_donation_registered is not None:
        donor.organ_donation_registered = payload.organ_donation_registered
    if payload.organ_types is not None:
        donor.organ_types = [str(x).strip().upper() for x in payload.organ_types if str(x).strip()]
    if payload.preferred_donation_time is not None:
        donor.preferred_donation_time = payload.preferred_donation_time

    profile_patch = payload.profile
    if profile_patch:
        if profile_patch.first_name is not None:
            profile.first_name = profile_patch.first_name
        if profile_patch.last_name is not None:
            profile.last_name = profile_patch.last_name
        if profile_patch.date_of_birth is not None:
            profile.date_of_birth = profile_patch.date_of_birth
        if profile_patch.gender is not None:
            profile.gender = _parse_gender(profile_patch.gender)
        if profile_patch.address is not None:
            profile.address = profile_patch.address
        if profile_patch.city is not None:
            profile.city = profile_patch.city
        if profile_patch.state is not None:
            profile.state = profile_patch.state
        if profile_patch.postal_code is not None:
            profile.postal_code = profile_patch.postal_code
        if profile_patch.country is not None:
            profile.country = profile_patch.country
        if profile_patch.latitude is not None:
            profile.latitude = Decimal(str(profile_patch.latitude))
        if profile_patch.longitude is not None:
            profile.longitude = Decimal(str(profile_patch.longitude))
        if profile_patch.blood_group is not None:
            profile.blood_group = BloodGroup(profile_patch.blood_group.value)
        if profile_patch.emergency_contact_name is not None:
            profile.emergency_contact_name = profile_patch.emergency_contact_name
        if profile_patch.emergency_contact_phone is not None:
            profile.emergency_contact_phone = profile_patch.emergency_contact_phone

    profile.updated_at = datetime.utcnow()
    donor.updated_at = datetime.utcnow()
    donor.availability_updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Donor profile updated",
        "donor": {
            "id": donor.id,
            "is_available": donor.is_available,
            "can_donate_blood": donor.can_donate_blood,
            "organ_types": donor.organ_types,
            "organ_donation_registered": donor.organ_donation_registered,
            "preferred_donation_time": donor.preferred_donation_time,
            "profile": {
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "date_of_birth": profile.date_of_birth,
                "gender": _enum_value(profile.gender),
                "address": profile.address,
                "city": profile.city,
                "state": profile.state,
                "postal_code": profile.postal_code,
                "country": profile.country,
                "blood_group": _enum_value(profile.blood_group),
                "emergency_contact_name": profile.emergency_contact_name,
                "emergency_contact_phone": profile.emergency_contact_phone,
                "latitude": float(profile.latitude) if profile.latitude is not None else None,
                "longitude": float(profile.longitude) if profile.longitude is not None else None,
            },
        },
    }


@api_router.put("/donors/me/availability", tags=["Donors"])
def update_availability(
    payload: AvailabilityUpdateRequest,
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    donor.is_available = payload.is_available
    donor.availability_updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Availability updated", "is_available": donor.is_available}


@api_router.get("/donors/nearby", tags=["Donors"])
def nearby_donors(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(20, ge=1, le=500),
    blood_group: Optional[BloodGroupEnum] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = (
        db.query(Donor, Profile)
        .join(Profile, Donor.profile_id == Profile.id)
        .filter(Donor.is_available.is_(True))
        .all()
    )

    results: List[Dict[str, Any]] = []
    for donor, profile in rows:
        if blood_group and _enum_value(profile.blood_group) != blood_group.value:
            continue

        dist = MatchingEngine.haversine_distance(
            latitude,
            longitude,
            float(profile.latitude),
            float(profile.longitude),
        )
        if dist <= radius_km:
            results.append(
                {
                    "donor_id": donor.id,
                    "city": profile.city,
                    "blood_group": _enum_value(profile.blood_group),
                    "distance_km": dist,
                    "organ_types": donor.organ_types,
                    "is_available": donor.is_available,
                }
            )

    results.sort(key=lambda x: x["distance_km"])
    return {"count": len(results), "items": results}


@api_router.get("/donors/me/nearby-requests", tags=["Donors"])
def donor_nearby_requests(
    radius_km: float = Query(50, ge=0.1, le=500),
    urgency: Optional[str] = Query(None),
    blood_group: Optional[BloodGroupEnum] = Query(None),
    request_type: Optional[str] = Query(None),
    organ_type: Optional[str] = Query(None),
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if donor is None:
        raise NotFoundError("Donor profile not found")

    profile = None
    if donor.profile_id:
        profile = db.query(Profile).filter(Profile.id == donor.profile_id).first()
    if profile is None:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        raise NotFoundError("Donor profile details not found")

    donor_lat, donor_lng = _resolve_coordinates(
        profile.latitude if profile else None,
        profile.longitude if profile else None,
    )

    urgency_filter = urgency.upper() if urgency else None
    if urgency_filter and urgency_filter not in {"LOW", "MEDIUM", "CRITICAL"}:
        raise ValidationError("urgency must be LOW, MEDIUM, or CRITICAL")

    request_type_filter = request_type.upper() if request_type else None
    if request_type_filter and request_type_filter not in {"BLOOD", "ORGAN", "PLASMA"}:
        raise ValidationError("request_type must be BLOOD, ORGAN, or PLASMA")

    organ_type_filter = organ_type.strip().upper() if organ_type and organ_type.strip() else None

    # Keep local donor testing simple: always ensure nearby sample requests for all blood groups and organ types.
    _ensure_nearby_requests_for_all_blood_groups(db, donor_lat, donor_lng)

    requests = (
        db.query(Request)
        .filter(Request.status.in_([RequestStatus.OPEN, RequestStatus.MATCHED, RequestStatus.IN_PROGRESS]))
        .order_by(Request.created_at.desc())
        .limit(300)
        .all()
    )

    donor_matches = db.query(Match).filter(Match.donor_id == donor.id).all()
    match_map: Dict[str, Match] = {m.request_id: m for m in donor_matches}

    items: List[Dict[str, Any]] = []

    for request_obj in requests:
        if urgency_filter and _enum_value(request_obj.urgency_level) != urgency_filter:
            continue
        if request_type_filter and _enum_value(request_obj.request_type) != request_type_filter:
            continue
        if blood_group and (request_obj.blood_group_needed or "").upper() != blood_group.value.upper():
            continue
        if organ_type_filter and (request_obj.organ_type_needed or "").upper() != organ_type_filter:
            continue

        hospital_location = _normalize_generated_nearby_location(request_obj.hospital_location or {}, donor_lat, donor_lng)
        req_lat, req_lng = _resolve_coordinates(hospital_location.get("latitude"), hospital_location.get("longitude"), donor_lat, donor_lng)

        distance_km = MatchingEngine.haversine_distance(
            donor_lat,
            donor_lng,
            req_lat,
            req_lng,
        )

        request_status = _enum_value(request_obj.status)

        match_obj = match_map.get(request_obj.id)
        if match_obj is None:
            score = _score_donor_against_request(donor, profile, request_obj)
            if score is None:
                continue
        recipient_obj = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
        recipient_user = db.query(User).filter(User.id == recipient_obj.user_id).first() if recipient_obj else None
        verification = _build_request_verification_snapshot(request_obj, recipient_obj, recipient_user)

        items.append(
            {
                "request_id": request_obj.id,
                "request_type": _enum_value(request_obj.request_type),
                "blood_group_needed": request_obj.blood_group_needed,
                "organ_type_needed": request_obj.organ_type_needed,
                "urgency_level": _enum_value(request_obj.urgency_level),
                "status": request_status,
                "hospital_name": request_obj.hospital_name,
                "hospital_location": hospital_location,
                "clinical_notes": request_obj.clinical_notes,
                "distance_km": distance_km,
                "match_id": match_obj.id if match_obj else None,
                "compatibility_score": float(match_obj.compatibility_score) if match_obj else float(score.compatibility_score),
                "match_status": _enum_value(match_obj.status) if match_obj else None,
                "donor_response": _enum_value(match_obj.donor_response) if match_obj else None,
                "verification": verification,
                "created_at": request_obj.created_at.isoformat() if request_obj.created_at else None,
            }
        )

    items.sort(key=lambda x: (x["distance_km"], -(x["compatibility_score"] or 0)))
    return {"count": len(items), "items": items}


@api_router.get("/donors/me/recipient-requests", tags=["Donors"])
def donor_recipient_requests(
    radius_km: float = Query(50, ge=0.1, le=500),
    urgency: Optional[str] = Query(None),
    blood_group: Optional[BloodGroupEnum] = Query(None),
    request_type: Optional[str] = Query(None),
    organ_type: Optional[str] = Query(None),
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    profile = None
    if donor.profile_id:
        profile = db.query(Profile).filter(Profile.id == donor.profile_id).first()
    if profile is None:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        raise NotFoundError("Donor profile details not found")

    urgency_filter = urgency.upper() if urgency else None
    if urgency_filter and urgency_filter not in {"LOW", "MEDIUM", "CRITICAL"}:
        raise ValidationError("urgency must be LOW, MEDIUM, or CRITICAL")

    request_type_filter = request_type.upper() if request_type else None
    if request_type_filter and request_type_filter not in {"BLOOD", "ORGAN", "PLASMA"}:
        raise ValidationError("request_type must be BLOOD, ORGAN, or PLASMA")

    organ_type_filter = organ_type.strip().upper() if organ_type and organ_type.strip() else None

    rows = (
        db.query(Request, Recipient, Profile, User)
        .join(Recipient, Recipient.id == Request.recipient_id)
        .join(Profile, Profile.user_id == Recipient.user_id)
        .join(User, User.id == Recipient.user_id)
        .filter(Request.status == RequestStatus.OPEN)
        .order_by(Request.created_at.desc())
        .limit(300)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for request_obj, recipient_obj, recipient_profile, recipient_user in rows:
        if urgency_filter and _enum_value(request_obj.urgency_level) != urgency_filter:
            continue
        if request_type_filter and _enum_value(request_obj.request_type) != request_type_filter:
            continue
        if blood_group and (request_obj.blood_group_needed or "").upper() != blood_group.value.upper():
            continue
        if organ_type_filter and (request_obj.organ_type_needed or "").upper() != organ_type_filter:
            continue

        verification = _build_request_verification_snapshot(request_obj, recipient_obj, recipient_user)

        score = _score_donor_against_request(donor, profile, request_obj)
        if score is None:
            continue

        hospital_location = dict(request_obj.hospital_location or {})
        req_lat, req_lng = _resolve_coordinates(
            hospital_location.get("latitude"),
            hospital_location.get("longitude"),
            recipient_profile.latitude if recipient_profile else None,
            recipient_profile.longitude if recipient_profile else None,
        )
        hospital_location.setdefault("latitude", req_lat)
        hospital_location.setdefault("longitude", req_lng)

        recipient_name = f"{recipient_profile.first_name} {recipient_profile.last_name}".strip()
        items.append(
            {
                "request_id": request_obj.id,
                "recipient_id": recipient_obj.id,
                "recipient_name": recipient_name or "Recipient",
                "request_type": _enum_value(request_obj.request_type),
                "blood_group_needed": request_obj.blood_group_needed,
                "organ_type_needed": request_obj.organ_type_needed,
                "urgency_level": _enum_value(request_obj.urgency_level),
                "status": _enum_value(request_obj.status),
                "hospital_name": request_obj.hospital_name,
                "hospital_location": hospital_location,
                "clinical_notes": request_obj.clinical_notes,
                "required_tests": request_obj.required_tests,
                "receiving_doctor_name": request_obj.receiving_doctor_name,
                "receiving_doctor_phone": request_obj.receiving_doctor_phone,
                "distance_km": float(score.distance_km),
                "compatibility_score": float(score.compatibility_score),
                "verification": verification,
                "needed_by": request_obj.needed_by.isoformat() if request_obj.needed_by else None,
                "created_at": request_obj.created_at.isoformat() if request_obj.created_at else None,
            }
        )

    items.sort(key=lambda item: (-item["compatibility_score"], item["distance_km"]))
    return {"count": len(items), "items": items}


@api_router.get("/donors/me/top-matches", tags=["Donors"])
def donor_top_matches(
    limit: int = Query(20, ge=1, le=100),
    max_distance_km: float = Query(100, ge=0.1, le=500),
    urgency: Optional[str] = Query(None),
    blood_group: Optional[BloodGroupEnum] = Query(None),
    request_type: Optional[str] = Query(None),
    organ_type: Optional[str] = Query(None),
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    urgency_filter = urgency.upper() if urgency else None
    if urgency_filter and urgency_filter not in {"LOW", "MEDIUM", "CRITICAL"}:
        raise ValidationError("urgency must be LOW, MEDIUM, or CRITICAL")

    request_type_filter = request_type.upper() if request_type else None
    if request_type_filter and request_type_filter not in {"BLOOD", "ORGAN", "PLASMA"}:
        raise ValidationError("request_type must be BLOOD, ORGAN, or PLASMA")

    organ_type_filter = organ_type.strip().upper() if organ_type and organ_type.strip() else None

    rows = (
        db.query(Match, Request)
        .join(Request, Match.request_id == Request.id)
        .filter(Match.donor_id == donor.id)
        .order_by(Match.compatibility_score.desc(), Match.created_at.desc())
        .limit(300)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for match_obj, request_obj in rows:
        if float(match_obj.distance_km) > max_distance_km:
            continue
        if urgency_filter and _enum_value(request_obj.urgency_level) != urgency_filter:
            continue
        if request_type_filter and _enum_value(request_obj.request_type) != request_type_filter:
            continue
        if blood_group and (request_obj.blood_group_needed or "").upper() != blood_group.value.upper():
            continue
        if organ_type_filter and (request_obj.organ_type_needed or "").upper() != organ_type_filter:
            continue

        items.append(
            {
                "match_id": match_obj.id,
                "request_id": request_obj.id,
                "request_type": _enum_value(request_obj.request_type),
                "blood_group_needed": request_obj.blood_group_needed,
                "organ_type_needed": request_obj.organ_type_needed,
                "urgency_level": _enum_value(request_obj.urgency_level),
                "request_status": _enum_value(request_obj.status),
                "hospital_name": request_obj.hospital_name,
                "hospital_location": request_obj.hospital_location,
                "clinical_notes": request_obj.clinical_notes,
                "compatibility_score": float(match_obj.compatibility_score),
                "distance_km": float(match_obj.distance_km),
                "match_status": _enum_value(match_obj.status),
                "donor_response": _enum_value(match_obj.donor_response),
                "donor_response_reason": match_obj.donor_response_reason,
                "recipient_response": _enum_value(match_obj.recipient_response),
                "recipient_response_at": match_obj.recipient_response_at.isoformat() if match_obj.recipient_response_at else None,
                "appointment_scheduled_at": match_obj.appointment_scheduled_at.isoformat() if match_obj.appointment_scheduled_at else None,
                "created_at": match_obj.created_at.isoformat() if match_obj.created_at else None,
            }
        )

    items.sort(key=lambda x: (-x["compatibility_score"], x["distance_km"]))
    return {"count": len(items[:limit]), "items": items[:limit]}


@api_router.get("/donors/me/appointments", tags=["Donors"])
def donor_appointments(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    rows = (
        db.query(Match, Request)
        .join(Request, Match.request_id == Request.id)
        .filter(Match.donor_id == donor.id)
        .filter(Match.donor_response == DonorDecision.ACCEPTED)
        .filter(Match.recipient_response == RecipientResponse.ACCEPTED)
        .order_by(Match.recipient_response_at.desc(), Match.created_at.desc())
        .limit(limit)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for match_obj, request_obj in rows:
        items.append(
            {
                "match_id": match_obj.id,
                "request_id": request_obj.id,
                "request_type": _enum_value(request_obj.request_type),
                "blood_group_needed": request_obj.blood_group_needed,
                "organ_type_needed": request_obj.organ_type_needed,
                "urgency_level": _enum_value(request_obj.urgency_level),
                "request_status": _enum_value(request_obj.status),
                "hospital_name": request_obj.hospital_name,
                "hospital_location": request_obj.hospital_location,
                "receiving_doctor_name": request_obj.receiving_doctor_name,
                "receiving_doctor_phone": request_obj.receiving_doctor_phone,
                "clinical_notes": request_obj.clinical_notes,
                "required_tests": request_obj.required_tests,
                "distance_km": float(match_obj.distance_km),
                "compatibility_score": float(match_obj.compatibility_score),
                "match_status": _enum_value(match_obj.status),
                "donor_response": _enum_value(match_obj.donor_response),
                "donor_response_reason": match_obj.donor_response_reason,
                "recipient_response": _enum_value(match_obj.recipient_response),
                "recipient_response_at": match_obj.recipient_response_at.isoformat() if match_obj.recipient_response_at else None,
                "appointment_scheduled_at": match_obj.appointment_scheduled_at.isoformat() if match_obj.appointment_scheduled_at else None,
                "created_at": match_obj.created_at.isoformat() if match_obj.created_at else None,
                "updated_at": match_obj.updated_at.isoformat() if match_obj.updated_at else None,
            }
        )

    return {"count": len(items), "items": items}


@api_router.post("/requests/{request_id}/apply", tags=["Requests"])
async def donor_apply_for_request(
    request_id: str,
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if donor is None:
        raise ValidationError("Donor profile not found. Complete donor onboarding first.")

    donor_profile = None
    if donor.profile_id:
        donor_profile = db.query(Profile).filter(Profile.id == donor.profile_id).first()
    if donor_profile is None:
        donor_profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if donor_profile is None:
        raise ValidationError("Donor profile details missing. Update your donor profile first.")

    donor_trust = _evaluate_donor_trust(user, donor, donor_profile)

    request_obj = (
        db.query(Request)
        .filter(
            Request.id == request_id,
            Request.status.in_([RequestStatus.OPEN, RequestStatus.MATCHED, RequestStatus.IN_PROGRESS]),
        )
        .first()
    )
    if not request_obj:
        raise NotFoundError("Request not available for donor application")

    recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
    recipient_user = db.query(User).filter(User.id == recipient.user_id).first() if recipient else None
    request_verification = _build_request_verification_snapshot(request_obj, recipient, recipient_user)

    donor_lat, donor_lng = _resolve_coordinates(
        donor_profile.latitude if donor_profile else None,
        donor_profile.longitude if donor_profile else None,
    )
    hospital_location = _normalize_generated_nearby_location(request_obj.hospital_location or {}, donor_lat, donor_lng)
    req_lat, req_lng = _resolve_coordinates(hospital_location.get("latitude"), hospital_location.get("longitude"), donor_lat, donor_lng)
    request_obj.hospital_location = hospital_location

    donor_blood = _enum_value(donor_profile.blood_group)
    request_payload = {
        "id": request_obj.id,
        "request_type": _enum_value(request_obj.request_type),
        "blood_group_needed": request_obj.blood_group_needed,
        "organ_type_needed": request_obj.organ_type_needed,
        "urgency_level": _enum_value(request_obj.urgency_level),
    }
    donor_payload = {
        "id": donor.id,
        "blood_group": donor_blood,
        "latitude": donor_lat,
        "longitude": donor_lng,
    }
    score = MatchingEngine.match_donor_to_request(
        donor=donor_payload,
        request=request_payload,
        donor_location=(donor_lat, donor_lng),
        request_location=(req_lat, req_lng),
    )

    compatibility_score = float(score.compatibility_score) if score else 100.0
    distance_km = float(score.distance_km) if score else MatchingEngine.haversine_distance(
        donor_lat,
        donor_lng,
        req_lat,
        req_lng,
    )
    score_components = score.get_score_components() if score else {
        "manual_override": True,
        "reason": "Accepted from donor dashboard without compatibility gate",
        "donor_verification_risk": donor_trust.get("risk_level"),
        "request_verification_risk": request_verification.get("risk_level"),
    }

    match = (
        db.query(Match)
        .filter(Match.request_id == request_obj.id, Match.donor_id == donor.id)
        .first()
    )

    if match is None:
        match = Match(
            request_id=request_obj.id,
            donor_id=donor.id,
            compatibility_score=Decimal(str(compatibility_score)),
            distance_km=Decimal(str(distance_km)),
            score_components=score_components,
            status=MatchStatus.ACCEPTED,
            donor_response=DonorDecision.ACCEPTED,
            donor_response_at=datetime.utcnow(),
            donor_response_reason="Applied from nearby requests",
            recipient_response=RecipientResponse.PENDING,
        )
        db.add(match)
    else:
        match.compatibility_score = Decimal(str(compatibility_score))
        match.distance_km = Decimal(str(distance_km))
        match.score_components = score_components
        match.status = MatchStatus.ACCEPTED
        match.donor_response = DonorDecision.ACCEPTED
        match.donor_response_at = datetime.utcnow()
        match.donor_response_reason = "Applied from nearby requests"

    request_obj.status = RequestStatus.MATCHED
    request_obj.matched_donor_id = donor.id
    request_obj.matched_at = datetime.utcnow()

    if recipient:
        db.add(
            Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.REQUEST_MATCHED,
                title="Donor Applied to Your Request",
                message="A donor has applied from nearby requests.",
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
        )

        await notification_hub.send_to_user(
            recipient.user_id,
            {
                "type": "REQUEST_MATCHED",
                "match_id": match.id,
                "request_id": request_obj.id,
            },
        )

    admin_users = (
        db.query(User)
        .filter(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.is_blocked.is_(False),
            User.deleted_at.is_(None),
        )
        .all()
    )
    for admin_user in admin_users:
        db.add(
            Notification(
                user_id=admin_user.id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Donor Accepted Case",
                message=(
                    f"Donor accepted request {request_obj.id} for hospital "
                    f"{request_obj.hospital_name or 'N/A'}."
                ),
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
        )
        await notification_hub.send_to_user(
            admin_user.id,
            {
                "type": "SYSTEM_ALERT",
                "event": "DONOR_CASE_ACCEPTED",
                "match_id": match.id,
                "request_id": request_obj.id,
            },
        )

    db.commit()

    return {
        "message": "Applied successfully",
        "request_id": request_obj.id,
        "match_id": match.id,
        "distance_km": float(match.distance_km),
        "compatibility_score": float(match.compatibility_score),
        "donor_verification": donor_trust,
        "request_verification": request_verification,
    }


@api_router.post("/recipients/register", tags=["Recipients"])
def register_recipient(
    payload: RecipientOnboardingRequest,
    user: User = Depends(require_roles(UserRole.RECIPIENT)),
    db: Session = Depends(get_db),
):
    existing = db.query(Recipient).filter(Recipient.user_id == user.id).first()
    if existing:
        raise DuplicateEntryError("Recipient profile already exists")

    profile = _upsert_profile(db, user.id, payload.profile)

    urgency_value = payload.matching_criteria.get("urgency", "MEDIUM")
    urgency_value = urgency_value.upper() if isinstance(urgency_value, str) else "MEDIUM"
    if urgency_value not in {"LOW", "MEDIUM", "CRITICAL"}:
        urgency_value = "MEDIUM"

    recipient = Recipient(
        user_id=user.id,
        profile_id=profile.id,
        primary_disease=payload.primary_disease,
        diagnosis_date=payload.diagnosis_date,
        surgery_needed_date=payload.surgery_needed_date,
        hospital_name=payload.hospital_name,
        hospital_contact_phone=payload.hospital_contact_phone,
        doctor_name=payload.doctor_name,
        doctor_phone=payload.doctor_phone,
        doctor_registration_number=payload.doctor_registration_number,
        hospital_verification_document_url=payload.hospital_verification_document_url,
        is_verified_by_hospital=bool(payload.hospital_verification_document_url),
        matching_criteria=payload.matching_criteria,
        urgency_level=UrgencyLevel(urgency_value),
    )

    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    return {
        "message": "Recipient profile created",
        "recipient": {
            "id": recipient.id,
            "user_id": recipient.user_id,
            "primary_disease": recipient.primary_disease,
            "hospital_name": recipient.hospital_name,
            "urgency_level": _enum_value(recipient.urgency_level),
            "is_verified_by_hospital": recipient.is_verified_by_hospital,
        },
    }


@api_router.get("/recipients/me", tags=["Recipients"])
def recipient_me(
    user: User = Depends(require_roles(UserRole.RECIPIENT)),
    db: Session = Depends(get_db),
):
    recipient = db.query(Recipient).filter(Recipient.user_id == user.id).first()
    if not recipient:
        raise NotFoundError("Recipient profile not found")

    return {
        "id": recipient.id,
        "primary_disease": recipient.primary_disease,
        "hospital_name": recipient.hospital_name,
        "hospital_contact_phone": recipient.hospital_contact_phone,
        "doctor_name": recipient.doctor_name,
        "doctor_phone": recipient.doctor_phone,
        "doctor_registration_number": recipient.doctor_registration_number,
        "hospital_verification_document_url": recipient.hospital_verification_document_url,
        "urgency_level": _enum_value(recipient.urgency_level),
        "matching_criteria": recipient.matching_criteria,
        "is_verified_by_hospital": recipient.is_verified_by_hospital,
    }


@api_router.post("/requests", tags=["Requests"])
async def create_request(
    payload: RequestCreatePayload,
    user: User = Depends(require_roles(UserRole.RECIPIENT)),
    db: Session = Depends(get_db),
):
    recipient = db.query(Recipient).filter(Recipient.user_id == user.id).first()
    if not recipient:
        raise NotFoundError("Recipient profile not found")

    req_type_raw = _normalize_upper(payload.request_type)
    if req_type_raw not in {"BLOOD", "ORGAN", "PLASMA"}:
        raise ValidationError("Invalid request_type")

    urgency_raw = _normalize_upper(payload.urgency_level)
    if urgency_raw not in {"LOW", "MEDIUM", "CRITICAL"}:
        raise ValidationError("Invalid urgency_level")

    blood_group_needed = _normalize_blood_group(
        payload.blood_group_needed,
        allow_any=(req_type_raw == "ORGAN" and urgency_raw == "CRITICAL"),
    )
    organ_type_needed = _normalize_organ_type(
        payload.organ_type_needed,
        allow_any=(req_type_raw == "ORGAN" and urgency_raw == "CRITICAL"),
    )

    if req_type_raw == "BLOOD" and not blood_group_needed:
        raise ValidationError("blood_group_needed is required for BLOOD requests")
    if req_type_raw == "ORGAN" and not organ_type_needed:
        raise ValidationError("organ_type_needed is required for ORGAN requests")
    if req_type_raw == "ORGAN" and not blood_group_needed:
        raise ValidationError("blood_group_needed is required for ORGAN requests")

    request_obj = Request(
        recipient_id=recipient.id,
        request_type=RequestType(req_type_raw),
        blood_group_needed=blood_group_needed,
        organ_type_needed=organ_type_needed,
        quantity_needed=payload.quantity_needed,
        urgency_level=UrgencyLevel(urgency_raw),
        needed_by=payload.needed_by,
        status=RequestStatus.OPEN,
        hospital_location=payload.hospital_location,
        hospital_name=payload.hospital_name,
        receiving_doctor_name=payload.receiving_doctor_name,
        receiving_doctor_phone=payload.receiving_doctor_phone,
        clinical_notes=payload.clinical_notes,
        required_tests=payload.required_tests,
        is_public=payload.is_public,
    )

    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)

    recipient_user = db.query(User).filter(User.id == recipient.user_id).first()
    verification = _build_request_verification_snapshot(request_obj, recipient, recipient_user)

    admin_users = (
        db.query(User)
        .filter(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.is_blocked.is_(False),
            User.deleted_at.is_(None),
        )
        .all()
    )
    for admin_user in admin_users:
        db.add(
            Notification(
                user_id=admin_user.id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="New Request Pending Approval",
                message=(
                    f"A new {_enum_value(request_obj.request_type)} request is awaiting admin review "
                    f"from hospital {request_obj.hospital_name or 'N/A'}."
                ),
                related_entity_type="request",
                related_entity_id=request_obj.id,
                deliver_via=["IN_APP"],
            )
        )

    if verification["risk_level"] != "HIGH":
        donor_rows = (
            db.query(Donor, Profile, User)
            .join(Profile, Donor.profile_id == Profile.id)
            .join(User, Donor.user_id == User.id)
            .filter(
                Donor.is_available.is_(True),
                User.role == UserRole.DONOR,
                User.is_active.is_(True),
                User.is_blocked.is_(False),
                User.deleted_at.is_(None),
            )
            .all()
        )
        for donor, donor_profile, donor_user in donor_rows:
            score = _score_donor_against_request(donor, donor_profile, request_obj)
            if score is None:
                continue

            db.add(
                Notification(
                    user_id=donor_user.id,
                    notification_type=NotificationType.NEW_REQUEST_NEARBY,
                    title="New Recipient Request Matches You",
                    message=(
                        f"A new {_enum_value(request_obj.request_type)} request from "
                        f"{request_obj.hospital_name or 'N/A'} matches your profile."
                    ),
                    related_entity_type="request",
                    related_entity_id=request_obj.id,
                    deliver_via=["IN_APP"],
                )
            )

            await notification_hub.send_to_user(
                donor_user.id,
                {
                    "type": "NEW_REQUEST_NEARBY",
                    "request_id": request_obj.id,
                    "request_type": _enum_value(request_obj.request_type),
                    "hospital_name": request_obj.hospital_name,
                    "compatibility_score": score.compatibility_score,
                    "distance_km": score.distance_km,
                },
            )

    db.commit()

    return {
        "message": "Request submitted and sent to admin and matching donors",
        "request": {
            "id": request_obj.id,
            "request_type": _enum_value(request_obj.request_type),
            "blood_group_needed": request_obj.blood_group_needed,
            "organ_type_needed": request_obj.organ_type_needed,
            "urgency_level": _enum_value(request_obj.urgency_level),
            "status": _enum_value(request_obj.status),
            "hospital_name": request_obj.hospital_name,
            "needed_by": request_obj.needed_by.isoformat(),
            "created_at": request_obj.created_at.isoformat() if request_obj.created_at else None,
            "matches_found": 0,
        },
        "verification": verification,
    }


@api_router.get("/requests", tags=["Requests"])
def list_requests(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Request)

    if current_user.role == UserRole.RECIPIENT:
        recipient = db.query(Recipient).filter(Recipient.user_id == current_user.id).first()
        if not recipient:
            return {"count": 0, "items": []}
        query = query.filter(Request.recipient_id == recipient.id)
    elif current_user.role == UserRole.DONOR:
        donor = db.query(Donor).filter(Donor.user_id == current_user.id).first()
        if not donor:
            return {"count": 0, "items": []}
        query = (
            query.join(Match, Match.request_id == Request.id)
            .filter(Match.donor_id == donor.id)
            .distinct()
        )
    elif current_user.role == UserRole.ADMIN:
        rows = (
            db.query(Request, Recipient, Profile)
            .join(Recipient, Recipient.id == Request.recipient_id)
            .join(Profile, Profile.user_id == Recipient.user_id)
            .order_by(Request.created_at.desc())
            .limit(300)
            .all()
        )
        if status:
            status_upper = status.upper()
            if status_upper in {"OPEN", "MATCHED", "IN_PROGRESS", "FULFILLED", "CANCELLED", "EXPIRED"}:
                rows = [row for row in rows if row[0].status == RequestStatus(status_upper)]

        data = []
        for request_item, recipient_item, profile_item in rows:
            recipient_name = f"{profile_item.first_name} {profile_item.last_name}".strip()
            data.append(
                {
                    "id": request_item.id,
                    "request_type": _enum_value(request_item.request_type),
                    "blood_group_needed": request_item.blood_group_needed,
                    "organ_type_needed": request_item.organ_type_needed,
                    "urgency_level": _enum_value(request_item.urgency_level),
                    "status": _enum_value(request_item.status),
                    "hospital_name": request_item.hospital_name,
                    "recipient_name": recipient_name or recipient_item.user.username,
                    "created_at": request_item.created_at.isoformat() if request_item.created_at else None,
                    "needed_by": request_item.needed_by.isoformat() if request_item.needed_by else None,
                }
            )
        return {"count": len(data), "items": data}

    if status:
        status_upper = status.upper()
        if status_upper in {"OPEN", "MATCHED", "IN_PROGRESS", "FULFILLED", "CANCELLED", "EXPIRED"}:
            query = query.filter(Request.status == RequestStatus(status_upper))

    items = query.order_by(Request.created_at.desc()).limit(100).all()

    data = []
    for item in items:
        data.append(
            {
                "id": item.id,
                "request_type": _enum_value(item.request_type),
                "blood_group_needed": item.blood_group_needed,
                "organ_type_needed": item.organ_type_needed,
                "urgency_level": _enum_value(item.urgency_level),
                "status": _enum_value(item.status),
                "hospital_name": item.hospital_name,
                "recipient_name": None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "needed_by": item.needed_by.isoformat() if item.needed_by else None,
            }
        )

    return {"count": len(data), "items": data}


@api_router.get("/matches/for-request/{request_id}", tags=["Matches"])
def matches_for_request(
    request_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = (
        db.query(Match, Donor, Profile)
        .join(Donor, Match.donor_id == Donor.id)
        .join(Profile, Donor.profile_id == Profile.id)
        .filter(Match.request_id == request_id)
        .order_by(Match.compatibility_score.desc())
        .all()
    )

    items = []
    for match, donor, profile in rows:
        items.append(
            {
                "match_id": match.id,
                "donor_id": donor.id,
                "donor_name": f"{profile.first_name} {profile.last_name}",
                "distance_km": float(match.distance_km),
                "compatibility_score": float(match.compatibility_score),
                "status": _enum_value(match.status),
                "donor_response": _enum_value(match.donor_response),
                "created_at": match.created_at.isoformat() if match.created_at else None,
            }
        )

    return {"count": len(items), "items": items}


@api_router.post("/matches/{match_id}/accept", tags=["Matches"])
async def accept_match(
    match_id: str,
    payload: MatchAcceptRequest,
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    match = db.query(Match).filter(Match.id == match_id, Match.donor_id == donor.id).first()
    if not match:
        raise NotFoundError("Match not found")

    match.status = MatchStatus.ACCEPTED
    match.donor_response = DonorDecision.ACCEPTED
    match.donor_response_at = datetime.utcnow()
    match.donor_response_reason = payload.notes
    match.appointment_scheduled_at = datetime.utcnow()
    if match.recipient_response is None:
        match.recipient_response = RecipientResponse.PENDING

    request_obj = db.query(Request).filter(Request.id == match.request_id).first()
    if request_obj:
        request_obj.status = RequestStatus.MATCHED
        request_obj.matched_donor_id = donor.id
        request_obj.matched_at = datetime.utcnow()

        recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
        if recipient:
            notification = Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.REQUEST_MATCHED,
                title="Donor Accepted Your Request",
                message="A donor has accepted your request. Please proceed with scheduling.",
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
            db.add(notification)
            await notification_hub.send_to_user(
                recipient.user_id,
                {
                    "type": "REQUEST_MATCHED",
                    "match_id": match.id,
                    "request_id": request_obj.id,
                },
            )

        admin_users = (
            db.query(User)
            .filter(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
                User.is_blocked.is_(False),
                User.deleted_at.is_(None),
            )
            .all()
        )
        for admin_user in admin_users:
            db.add(
                Notification(
                    user_id=admin_user.id,
                    notification_type=NotificationType.SYSTEM_ALERT,
                    title="Donor Accepted Case",
                    message=(
                        f"Donor accepted request {request_obj.id} for hospital "
                        f"{request_obj.hospital_name or 'N/A'}."
                    ),
                    related_entity_type="match",
                    related_entity_id=match.id,
                    deliver_via=["IN_APP"],
                )
            )
            await notification_hub.send_to_user(
                admin_user.id,
                {
                    "type": "SYSTEM_ALERT",
                    "event": "DONOR_CASE_ACCEPTED",
                    "match_id": match.id,
                    "request_id": request_obj.id,
                },
            )

    db.commit()

    return {
        "message": "Match accepted",
        "match_id": match.id,
        "appointment_preferred_date": payload.appointment_preferred_date,
        "appointment_preferred_time": payload.appointment_preferred_time,
    }


@api_router.post("/matches/{match_id}/reject", tags=["Matches"])
async def reject_match(
    match_id: str,
    payload: MatchRejectRequest,
    user: User = Depends(require_roles(UserRole.DONOR)),
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if not donor:
        raise NotFoundError("Donor profile not found")

    match = db.query(Match).filter(Match.id == match_id, Match.donor_id == donor.id).first()
    if not match:
        raise NotFoundError("Match not found")

    match.status = MatchStatus.REJECTED
    match.donor_response = DonorDecision.REJECTED
    match.donor_response_at = datetime.utcnow()
    match.donor_response_reason = payload.reason

    db.commit()

    return {"message": "Match rejected", "match_id": match.id}


@api_router.get("/notifications/me", tags=["Notifications"])
def my_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    rows = query.order_by(Notification.created_at.desc()).limit(limit).all()
    items = []
    for n in rows:
        items.append(
            {
                "notification_id": n.id,
                "notification_type": _enum_value(n.notification_type),
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "related_entity_type": n.related_entity_type,
                "related_entity_id": n.related_entity_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
        )

    return {"count": len(items), "items": items}


@api_router.post("/notifications/{notification_id}/read", tags=["Notifications"])
def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if not notification:
        raise NotFoundError("Notification not found")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"message": "Notification marked as read"}


@api_router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket, token: str):
    try:
        user_id = SecurityManager.extract_user_id_from_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await notification_hub.connect(user_id, websocket)

    with SessionLocal() as db:
        unread = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .order_by(Notification.created_at.desc())
            .limit(10)
            .all()
        )
        await websocket.send_json(
            {
                "type": "INIT_UNREAD",
                "count": len(unread),
                "items": [
                    {
                        "notification_id": item.id,
                        "title": item.title,
                        "message": item.message,
                        "notification_type": _enum_value(item.notification_type),
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in unread
                ],
            }
        )

    try:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json({"type": "pong", "at": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)
    except Exception:
        notification_hub.disconnect(user_id, websocket)


@api_router.get("/admin/users", tags=["Admin"])
def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    total = db.query(func.count(User.id)).scalar() or 0

    rows = (
        db.query(User)
        .filter(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for u in rows:
        items.append(
            {
                "user_id": u.id,
                "email": u.email,
                "phone": u.phone,
                "role": _enum_value(u.role),
                "email_verified": u.email_verified,
                "phone_verified": u.phone_verified,
                "id_verified": u.id_verified,
                "is_active": u.is_active,
                "is_blocked": u.is_blocked,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
        )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }


@api_router.post("/admin/verify-user/{user_id}", tags=["Admin"])
def admin_verify_user(
    user_id: str,
    payload: VerifyUserRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target:
        raise NotFoundError("User not found")

    target.id_verified = payload.verified
    target.id_verified_at = datetime.utcnow() if payload.verified else None

    action = AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.VERIFY_ID,
        target_entity_type="user",
        target_entity_id=target.id,
        decision=payload.notes,
        reason=payload.notes,
        status=ActionStatus.APPROVED if payload.verified else ActionStatus.REJECTED,
        status_updated_by=admin.id,
        status_updated_at=datetime.utcnow(),
    )
    db.add(action)

    notification = Notification(
        user_id=target.id,
        notification_type=NotificationType.VERIFICATION_NEEDED,
        title="ID Verification Updated",
        message=(
            "Your ID verification has been approved."
            if payload.verified
            else "Your ID verification was rejected. Please upload valid documents."
        ),
        related_entity_type="user",
        related_entity_id=target.id,
        deliver_via=["IN_APP"],
    )
    db.add(notification)
    db.commit()

    return {"message": "User verification updated", "id_verified": target.id_verified}


@api_router.post("/admin/block-user/{user_id}", tags=["Admin"])
def admin_block_user(
    user_id: str,
    payload: BlockUserRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target:
        raise NotFoundError("User not found")

    target.is_blocked = True
    target.block_reason = payload.reason

    action = AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.BLOCK_USER,
        target_entity_type="user",
        target_entity_id=target.id,
        reason=payload.reason,
        decision=payload.details or payload.reason,
        status=ActionStatus.APPROVED,
        status_updated_by=admin.id,
        status_updated_at=datetime.utcnow(),
    )
    db.add(action)

    notification = Notification(
        user_id=target.id,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Account Blocked",
        message="Your account has been blocked by an administrator.",
        related_entity_type="user",
        related_entity_id=target.id,
        deliver_via=["IN_APP"],
    )
    db.add(notification)

    db.commit()

    return {"message": "User blocked successfully"}


@api_router.get("/admin/requests", tags=["Admin"])
def admin_requests(
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Request, Recipient, User)
        .outerjoin(Recipient, Recipient.id == Request.recipient_id)
        .outerjoin(User, User.id == Recipient.user_id)
        .order_by(Request.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for r, recipient, recipient_user in rows:
        verification = _build_request_verification_snapshot(r, recipient, recipient_user)
        items.append(
            {
                "request_id": r.id,
                "recipient_id": r.recipient_id,
                "request_type": _enum_value(r.request_type),
                "blood_group_needed": r.blood_group_needed,
                "organ_type_needed": r.organ_type_needed,
                "urgency_level": _enum_value(r.urgency_level),
                "status": _enum_value(r.status),
                "hospital_name": r.hospital_name,
                "verification": verification,
                "needed_by": r.needed_by.isoformat() if r.needed_by else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )

    return {"count": len(items), "items": items}


@api_router.get("/admin/donor-requests", tags=["Admin"])
def admin_donor_requests(
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Match, Request, Donor, Profile, User)
        .join(Request, Match.request_id == Request.id)
        .join(Donor, Match.donor_id == Donor.id)
        .join(Profile, Donor.profile_id == Profile.id)
        .join(User, User.id == Donor.user_id)
        .filter(Match.donor_response == DonorDecision.ACCEPTED)
        .filter(
            or_(
                Match.recipient_response == RecipientResponse.PENDING,
                Match.recipient_response.is_(None),
            )
        )
        .order_by(Match.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for match, request_obj, donor, profile, donor_user in rows:
        recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
        recipient_user = db.query(User).filter(User.id == recipient.user_id).first() if recipient else None
        request_verification = _build_request_verification_snapshot(request_obj, recipient, recipient_user)
        donor_verification = _evaluate_donor_trust(donor_user, donor, profile)
        items.append(
            {
                "match_id": match.id,
                "request_id": request_obj.id,
                "request_type": _enum_value(request_obj.request_type),
                "blood_group_needed": request_obj.blood_group_needed,
                "organ_type_needed": request_obj.organ_type_needed,
                "urgency_level": _enum_value(request_obj.urgency_level),
                "request_status": _enum_value(request_obj.status),
                "hospital_name": request_obj.hospital_name,
                "distance_km": float(match.distance_km),
                "compatibility_score": float(match.compatibility_score),
                "donor_name": f"{profile.first_name} {profile.last_name}",
                "donor_blood_group": _enum_value(profile.blood_group),
                "donor_response": _enum_value(match.donor_response),
                "admin_review_status": _enum_value(match.recipient_response) or RecipientResponse.PENDING.value,
                "request_verification": request_verification,
                "donor_verification": donor_verification,
                "recipient_response_at": match.recipient_response_at.isoformat() if match.recipient_response_at else None,
                "appointment_scheduled_at": match.appointment_scheduled_at.isoformat() if match.appointment_scheduled_at else None,
                "created_at": match.created_at.isoformat() if match.created_at else None,
            }
        )

    return {"count": len(items), "items": items}


@api_router.get("/admin/schedules", tags=["Admin"])
def admin_schedules(
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Match, Request, Donor, Profile, User)
        .join(Request, Match.request_id == Request.id)
        .join(Donor, Match.donor_id == Donor.id)
        .join(Profile, Donor.profile_id == Profile.id)
        .join(User, User.id == Donor.user_id)
        .filter(Match.donor_response == DonorDecision.ACCEPTED)
        .filter(Match.recipient_response == RecipientResponse.ACCEPTED)
        .order_by(Match.recipient_response_at.desc().nullslast(), Match.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for match, request_obj, donor, profile, donor_user in rows:
        recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
        recipient_user = db.query(User).filter(User.id == recipient.user_id).first() if recipient else None
        request_verification = _build_request_verification_snapshot(request_obj, recipient, recipient_user)
        donor_verification = _evaluate_donor_trust(donor_user, donor, profile)
        items.append(
            {
                "match_id": match.id,
                "request_id": request_obj.id,
                "request_type": _enum_value(request_obj.request_type),
                "blood_group_needed": request_obj.blood_group_needed,
                "organ_type_needed": request_obj.organ_type_needed,
                "urgency_level": _enum_value(request_obj.urgency_level),
                "request_status": _enum_value(request_obj.status),
                "hospital_name": request_obj.hospital_name,
                "receiving_doctor_name": request_obj.receiving_doctor_name,
                "receiving_doctor_phone": request_obj.receiving_doctor_phone,
                "distance_km": float(match.distance_km),
                "compatibility_score": float(match.compatibility_score),
                "donor_name": f"{profile.first_name} {profile.last_name}",
                "donor_blood_group": _enum_value(profile.blood_group),
                "donor_response": _enum_value(match.donor_response),
                "admin_review_status": _enum_value(match.recipient_response),
                "request_verification": request_verification,
                "donor_verification": donor_verification,
                "recipient_response_at": match.recipient_response_at.isoformat() if match.recipient_response_at else None,
                "appointment_scheduled_at": match.appointment_scheduled_at.isoformat() if match.appointment_scheduled_at else None,
                "created_at": match.created_at.isoformat() if match.created_at else None,
            }
        )

    return {"count": len(items), "items": items}


@api_router.post("/admin/donor-requests/{match_id}/accept", tags=["Admin"])
def admin_accept_donor_request(
    match_id: str,
    payload: AdminRequestActionRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundError("Match not found")

    request_obj = db.query(Request).filter(Request.id == match.request_id).first()
    donor = db.query(Donor).filter(Donor.id == match.donor_id).first()
    if not request_obj or not donor:
        raise NotFoundError("Related request or donor not found")

    match.status = MatchStatus.ACCEPTED
    match.recipient_response = RecipientResponse.ACCEPTED
    match.recipient_response_at = datetime.utcnow()
    match.appointment_scheduled_at = datetime.utcnow()

    request_obj.status = RequestStatus.IN_PROGRESS
    request_obj.matched_donor_id = donor.id
    request_obj.matched_at = datetime.utcnow()
    request_obj.updated_at = datetime.utcnow()

    donor_user = db.query(User).filter(User.id == donor.user_id).first()
    recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()

    if donor_user:
        db.add(
            Notification(
                user_id=donor_user.id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Your Applied Request Was Approved",
                message=f"Admin approved your application for {request_obj.hospital_name}.",
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
        )

    if recipient:
        db.add(
            Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.REQUEST_MATCHED,
                title="Donor Application Approved",
                message=f"Admin approved the donor application for {request_obj.hospital_name}.",
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
        )

    db.add(
        AdminAction(
            admin_id=admin.id,
            action_type=AdminActionType.REMOVE_SPAM,
            target_entity_type="match",
            target_entity_id=match.id,
            reason=payload.reason,
            decision=payload.details or payload.reason,
            status=ActionStatus.APPROVED,
            status_updated_by=admin.id,
            status_updated_at=datetime.utcnow(),
        )
    )

    db.commit()

    return {"message": "Donor request approved", "match_id": match.id, "request_id": request_obj.id}


@api_router.post("/admin/donor-requests/{match_id}/reject", tags=["Admin"])
def admin_reject_donor_request(
    match_id: str,
    payload: AdminRequestActionRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundError("Match not found")

    request_obj = db.query(Request).filter(Request.id == match.request_id).first()
    donor = db.query(Donor).filter(Donor.id == match.donor_id).first()
    if not request_obj or not donor:
        raise NotFoundError("Related request or donor not found")

    match.status = MatchStatus.REJECTED
    match.recipient_response = RecipientResponse.REJECTED
    match.recipient_response_at = datetime.utcnow()

    request_obj.status = RequestStatus.OPEN
    request_obj.matched_donor_id = None
    request_obj.matched_at = None
    request_obj.updated_at = datetime.utcnow()

    donor_user = db.query(User).filter(User.id == donor.user_id).first()
    recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()

    if donor_user:
        db.add(
            Notification(
                user_id=donor_user.id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Your Applied Request Was Rejected",
                message=f"Admin rejected your application for {request_obj.hospital_name}.",
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
        )

    if recipient:
        db.add(
            Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Donor Application Rejected",
                message=f"Admin rejected the donor application for {request_obj.hospital_name}.",
                related_entity_type="match",
                related_entity_id=match.id,
                deliver_via=["IN_APP"],
            )
        )

    db.add(
        AdminAction(
            admin_id=admin.id,
            action_type=AdminActionType.REJECT_REQUEST,
            target_entity_type="match",
            target_entity_id=match.id,
            reason=payload.reason,
            decision=payload.details or payload.reason,
            status=ActionStatus.APPROVED,
            status_updated_by=admin.id,
            status_updated_at=datetime.utcnow(),
        )
    )

    db.commit()

    return {"message": "Donor request rejected", "match_id": match.id, "request_id": request_obj.id}


@api_router.post("/admin/requests/{request_id}/accept", tags=["Admin"])
async def admin_accept_request(
    request_id: str,
    payload: AdminRequestActionRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    request_obj = db.query(Request).filter(Request.id == request_id).first()
    if not request_obj:
        raise NotFoundError("Request not found")

    if request_obj.status != RequestStatus.OPEN:
        raise ValidationError("Only OPEN requests can be accepted by admin")

    recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
    recipient_user = db.query(User).filter(User.id == recipient.user_id).first() if recipient else None
    verification = _build_request_verification_snapshot(request_obj, recipient, recipient_user)
    if verification["risk_level"] == "HIGH":
        raise ValidationError(
            "Request is flagged high-risk. Verify recipient identity and hospital documents before approval."
        )

    request_obj.status = RequestStatus.IN_PROGRESS
    request_obj.updated_at = datetime.utcnow()

    created_matches = await _create_and_dispatch_matches(db, request_obj)

    if recipient:
        db.add(
            Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Request Accepted by Admin",
                message=(
                    f"Your request is accepted for processing. Matches generated: {created_matches}. "
                    f"Reason: {payload.reason}"
                ),
                related_entity_type="request",
                related_entity_id=request_obj.id,
                deliver_via=["IN_APP"],
            )
        )

    db.add(
        AdminAction(
            admin_id=admin.id,
            action_type=AdminActionType.REMOVE_SPAM,
            target_entity_type="request",
            target_entity_id=request_obj.id,
            reason=payload.reason,
            decision=payload.details or payload.reason,
            status=ActionStatus.APPROVED,
            status_updated_by=admin.id,
            status_updated_at=datetime.utcnow(),
        )
    )

    db.commit()

    return {
        "message": "Request accepted by admin",
        "request_id": request_obj.id,
        "status": _enum_value(request_obj.status),
        "matches_found": created_matches,
        "verification": verification,
    }


@api_router.post("/admin/requests/{request_id}/block", tags=["Admin"])
def admin_block_request(
    request_id: str,
    payload: AdminRequestActionRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    request_obj = db.query(Request).filter(Request.id == request_id).first()
    if not request_obj:
        raise NotFoundError("Request not found")

    request_obj.status = RequestStatus.CANCELLED
    request_obj.matched_donor_id = None
    request_obj.matched_at = None
    request_obj.updated_at = datetime.utcnow()

    matches = db.query(Match).filter(Match.request_id == request_obj.id).all()
    for item in matches:
        if item.status not in {MatchStatus.COMPLETED, MatchStatus.FAILED}:
            item.status = MatchStatus.FAILED
        if item.donor_response == DonorDecision.PENDING:
            item.donor_response = DonorDecision.UNAVAILABLE
        item.donor_response_reason = payload.reason

    recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()
    if recipient:
        db.add(
            Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Request Blocked by Admin",
                message=f"Your request has been blocked by admin. Reason: {payload.reason}",
                related_entity_type="request",
                related_entity_id=request_obj.id,
                deliver_via=["IN_APP"],
            )
        )

    db.add(
        AdminAction(
            admin_id=admin.id,
            action_type=AdminActionType.REJECT_REQUEST,
            target_entity_type="request",
            target_entity_id=request_obj.id,
            reason=payload.reason,
            decision=payload.details or payload.reason,
            status=ActionStatus.APPROVED,
            status_updated_by=admin.id,
            status_updated_at=datetime.utcnow(),
        )
    )

    db.commit()

    return {
        "message": "Request blocked by admin",
        "request_id": request_obj.id,
        "status": _enum_value(request_obj.status),
    }


@api_router.delete("/admin/requests/{request_id}", tags=["Admin"])
def admin_delete_request(
    request_id: str,
    reason: str = Query("Removed by admin", min_length=3, max_length=500),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    request_obj = db.query(Request).filter(Request.id == request_id).first()
    if not request_obj:
        raise NotFoundError("Request not found")

    recipient = db.query(Recipient).filter(Recipient.id == request_obj.recipient_id).first()

    if recipient:
        db.add(
            Notification(
                user_id=recipient.user_id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Request Deleted by Admin",
                message=f"Your request was removed by admin. Reason: {reason}",
                related_entity_type="request",
                related_entity_id=request_obj.id,
                deliver_via=["IN_APP"],
            )
        )

    db.add(
        AdminAction(
            admin_id=admin.id,
            action_type=AdminActionType.REMOVE_SPAM,
            target_entity_type="request",
            target_entity_id=request_obj.id,
            reason=reason,
            decision=reason,
            status=ActionStatus.APPROVED,
            status_updated_by=admin.id,
            status_updated_at=datetime.utcnow(),
        )
    )

    db.query(Match).filter(Match.request_id == request_obj.id).delete(synchronize_session=False)
    db.delete(request_obj)
    db.commit()

    return {
        "message": "Request deleted by admin",
        "request_id": request_id,
    }


@api_router.get("/admin/analytics", tags=["Admin"])
def admin_analytics(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    total_donors = db.query(func.count(Donor.id)).scalar() or 0
    total_recipients = db.query(func.count(Recipient.id)).scalar() or 0
    total_requests = db.query(func.count(Request.id)).scalar() or 0
    open_requests = db.query(func.count(Request.id)).filter(Request.status == RequestStatus.OPEN).scalar() or 0
    total_matches = db.query(func.count(Match.id)).scalar() or 0
    successful_matches = (
        db.query(func.count(Match.id)).filter(Match.status.in_([MatchStatus.ACCEPTED, MatchStatus.COMPLETED])).scalar()
        or 0
    )

    blood_requests = (
        db.query(func.count(Request.id)).filter(Request.request_type == RequestType.BLOOD).scalar() or 0
    )
    organ_requests = (
        db.query(func.count(Request.id)).filter(Request.request_type == RequestType.ORGAN).scalar() or 0
    )

    success_rate = 0.0
    if total_matches > 0:
        success_rate = round((successful_matches / total_matches) * 100, 2)

    top_city_row = (
        db.query(Profile.city, func.count(Profile.id).label("cnt"))
        .group_by(Profile.city)
        .order_by(func.count(Profile.id).desc())
        .first()
    )

    today = datetime.utcnow().strftime("%Y-%m-%d")
    analytics_row = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics_row:
        analytics_row = Analytics(
            date=today,
            total_donors=total_donors,
            total_recipients=total_recipients,
            new_requests=total_requests,
            pending_requests=open_requests,
            total_matches=total_matches,
            successful_matches=successful_matches,
            match_success_rate=Decimal(str(success_rate)),
            blood_requests=blood_requests,
            organ_requests=organ_requests,
            top_requesting_city=top_city_row[0] if top_city_row else None,
            top_donor_city=top_city_row[0] if top_city_row else None,
        )
        db.add(analytics_row)
        db.commit()

    return {
        "period": {"date": today},
        "metrics": {
            "total_donors": total_donors,
            "total_recipients": total_recipients,
            "total_requests": total_requests,
            "open_requests": open_requests,
            "total_matches": total_matches,
            "successful_matches": successful_matches,
            "match_success_rate": success_rate,
        },
        "blood_metrics": {
            "blood_requests": blood_requests,
        },
        "organ_metrics": {
            "organ_requests": organ_requests,
        },
        "geographic": {
            "top_city": top_city_row[0] if top_city_row else None,
        },
    }
