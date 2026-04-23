# FastAPI Main Application
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import logging

from app.config import settings
from app.core.exceptions import AppException
from app.core.security import SecurityManager
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.session import SessionLocal
from app.models import (
    Base,
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_default_auth_users() -> None:
    """Seed baseline users in development so local login works out of the box."""
    environment = (settings.ENVIRONMENT or "").lower()
    if not settings.DEBUG and environment not in {"development", "dev", "local"}:
        return

    default_users = [
        {
            "email": settings.ADMIN_EMAIL,
            "phone": settings.ADMIN_PHONE,
            "username": "admin_demo",
            "password": "SecurePass@123",
            "role": UserRole.ADMIN,
            "id_verified": True,
        },
        {
            "email": "donor@blooddonation.com",
            "phone": "+918888888888",
            "username": "donor_demo",
            "password": "SecurePass@123",
            "role": UserRole.DONOR,
            "id_verified": True,
        },
    ]

    db = SessionLocal()
    try:
        for item in default_users:
            user = db.query(User).filter(User.email == item["email"]).first()
            if user is None:
                user = User(
                    email=item["email"],
                    phone=item["phone"],
                    username=item["username"],
                    password_hash=SecurityManager.hash_password(item["password"]),
                    role=item["role"],
                    is_active=True,
                    is_blocked=False,
                    email_verified=True,
                    phone_verified=True,
                    id_verified=item["id_verified"],
                )
                db.add(user)
                continue

            # Keep demo credentials predictable for local testing.
            user.password_hash = SecurityManager.hash_password(item["password"])
            user.role = item["role"]
            user.is_active = True
            user.is_blocked = False
            user.email_verified = True
            user.phone_verified = True
            user.id_verified = item["id_verified"]

        db.commit()
        logger.info("Default development auth users ensured.")
    except Exception:
        db.rollback()
        logger.exception("Failed to seed default auth users")
    finally:
        db.close()


def seed_dummy_workflow_data() -> None:
    """Seed recipient and request data so full user->admin workflow can be tested quickly."""
    environment = (settings.ENVIRONMENT or "").lower()
    if not settings.DEBUG and environment not in {"development", "dev", "local"}:
        return

    db = SessionLocal()
    try:
        donor_user = db.query(User).filter(User.email == "donor@blooddonation.com").first()
        donor_profile = None
        if donor_user is not None:
            donor_profile = db.query(Profile).filter(Profile.user_id == donor_user.id).first()
            if donor_profile is None:
                donor_profile = Profile(
                    user_id=donor_user.id,
                    first_name="Arjun",
                    last_name="Patel",
                    date_of_birth="1992-06-12",
                    gender=Gender.MALE,
                    address="Lokhandwala, Andheri West",
                    city="Mumbai",
                    state="Maharashtra",
                    postal_code="400053",
                    country="India",
                    latitude=Decimal("19.1328"),
                    longitude=Decimal("72.8264"),
                    blood_group=BloodGroup.O_POS,
                    emergency_contact_name="Nisha Patel",
                    emergency_contact_phone="+919899998888",
                )
                db.add(donor_profile)
                db.flush()

            donor_record = db.query(Donor).filter(Donor.user_id == donor_user.id).first()
            if donor_record is None:
                donor_record = Donor(
                    user_id=donor_user.id,
                    profile_id=donor_profile.id,
                    is_available=True,
                    can_donate_blood=True,
                    organ_types=["KIDNEY"],
                    organ_donation_registered=True,
                    preferred_donation_time="ANYTIME",
                )
                db.add(donor_record)
            else:
                donor_record.profile_id = donor_profile.id
                donor_record.is_available = True
                donor_record.can_donate_blood = True
                donor_record.organ_donation_registered = True

        recipient_user = db.query(User).filter(User.email == "recipient@blooddonation.com").first()
        if recipient_user is None:
            recipient_user = User(
                email="recipient@blooddonation.com",
                phone="+917777777777",
                username="recipient_demo",
                password_hash=SecurityManager.hash_password("SecurePass@123"),
                role=UserRole.RECIPIENT,
                is_active=True,
                is_blocked=False,
                email_verified=True,
                phone_verified=True,
                id_verified=True,
            )
            db.add(recipient_user)
            db.flush()
        else:
            recipient_user.password_hash = SecurityManager.hash_password("SecurePass@123")
            recipient_user.role = UserRole.RECIPIENT
            recipient_user.is_active = True
            recipient_user.is_blocked = False
            recipient_user.email_verified = True
            recipient_user.phone_verified = True
            recipient_user.id_verified = True

        profile = db.query(Profile).filter(Profile.user_id == recipient_user.id).first()
        if profile is None:
            profile = Profile(
                user_id=recipient_user.id,
                first_name="Riya",
                last_name="Sharma",
                date_of_birth="1995-01-01",
                gender=Gender.FEMALE,
                address="Demo Residency, Andheri East",
                city="Mumbai",
                state="Maharashtra",
                postal_code="400069",
                country="India",
                latitude=Decimal("19.1196"),
                longitude=Decimal("72.8697"),
                blood_group=BloodGroup.AB_POS,
                emergency_contact_name="Rahul Sharma",
                emergency_contact_phone="+919876543210",
            )
            db.add(profile)
            db.flush()
        else:
            profile.first_name = profile.first_name or "Riya"
            profile.last_name = profile.last_name or "Sharma"
            profile.city = profile.city or "Mumbai"
            profile.state = profile.state or "Maharashtra"
            profile.address = profile.address or "Demo Residency, Andheri East"

        recipient = db.query(Recipient).filter(Recipient.user_id == recipient_user.id).first()
        if recipient is None:
            recipient = Recipient(
                user_id=recipient_user.id,
                profile_id=profile.id,
                is_active=True,
                primary_disease="Acute blood loss",
                diagnosis_date="2026-03-15",
                surgery_needed_date="2026-05-10",
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
        else:
            recipient.profile_id = profile.id
            recipient.is_active = True
            recipient.hospital_name = recipient.hospital_name or "Metro Care Hospital"

        demo_requests = [
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "O+",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.CRITICAL,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "Metro Care Hospital",
                "clinical_notes": "Original nearby request for O+",
                "needed_by": datetime.utcnow() + timedelta(days=1),
                "hospital_location": {"latitude": 19.1196, "longitude": 72.8697, "address": "Andheri East"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "O-",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.CRITICAL,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "Sunrise Trauma Center",
                "clinical_notes": "Original nearby request for O-",
                "needed_by": datetime.utcnow() + timedelta(days=1),
                "hospital_location": {"latitude": 19.1054, "longitude": 72.8869, "address": "Powai"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "A+",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.MEDIUM,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "City Health Hospital",
                "clinical_notes": "Original nearby request for A+",
                "needed_by": datetime.utcnow() + timedelta(days=2),
                "hospital_location": {"latitude": 19.0896, "longitude": 72.8656, "address": "Bandra East"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "A-",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.MEDIUM,
                "status": RequestStatus.MATCHED,
                "hospital_name": "North Point Hospital",
                "clinical_notes": "Original nearby request for A-",
                "needed_by": datetime.utcnow() + timedelta(days=2),
                "hospital_location": {"latitude": 19.0731, "longitude": 72.8893, "address": "Kurla"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "B+",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.CRITICAL,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "LifeBridge Medical",
                "clinical_notes": "Original nearby request for B+",
                "needed_by": datetime.utcnow() + timedelta(days=1),
                "hospital_location": {"latitude": 19.1452, "longitude": 72.8326, "address": "Goregaon"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "B-",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.MEDIUM,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "Harbor Multispeciality",
                "clinical_notes": "Original nearby request for B-",
                "needed_by": datetime.utcnow() + timedelta(days=3),
                "hospital_location": {"latitude": 19.0405, "longitude": 72.8506, "address": "Worli"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "AB+",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.LOW,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "Starlight Hospital",
                "clinical_notes": "Original nearby request for AB+",
                "needed_by": datetime.utcnow() + timedelta(days=4),
                "hospital_location": {"latitude": 19.1679, "longitude": 72.8442, "address": "Malad"},
            },
            {
                "request_type": RequestType.BLOOD,
                "blood_group_needed": "AB-",
                "organ_type_needed": None,
                "urgency_level": UrgencyLevel.CRITICAL,
                "status": RequestStatus.MATCHED,
                "hospital_name": "Emergency Central Hospital",
                "clinical_notes": "Original nearby request for AB-",
                "needed_by": datetime.utcnow() + timedelta(days=1),
                "hospital_location": {"latitude": 19.0623, "longitude": 72.8721, "address": "Sion"},
            },
            {
                "request_type": RequestType.ORGAN,
                "blood_group_needed": None,
                "organ_type_needed": "KIDNEY",
                "urgency_level": UrgencyLevel.MEDIUM,
                "status": RequestStatus.IN_PROGRESS,
                "hospital_name": "Lifeline Transplant Center",
                "clinical_notes": "Original nearby kidney request",
                "needed_by": datetime.utcnow() + timedelta(days=5),
                "hospital_location": {"latitude": 19.0760, "longitude": 72.8777, "address": "Dadar"},
            },
        ]

        for item in demo_requests:
            exists = (
                db.query(Request)
                .filter(
                    Request.recipient_id == recipient.id,
                    Request.hospital_name == item["hospital_name"],
                    Request.clinical_notes == item["clinical_notes"],
                )
                .first()
            )
            if exists is not None:
                continue

            db.add(
                Request(
                    recipient_id=recipient.id,
                    request_type=item["request_type"],
                    blood_group_needed=item["blood_group_needed"],
                    organ_type_needed=item["organ_type_needed"],
                    quantity_needed=1,
                    urgency_level=item["urgency_level"],
                    needed_by=item["needed_by"],
                    status=item["status"],
                    hospital_location=item["hospital_location"],
                    hospital_name=item["hospital_name"],
                    receiving_doctor_name="Dr. Demo",
                    receiving_doctor_phone="+919833334444",
                    clinical_notes=item["clinical_notes"],
                    required_tests=["CBC"],
                    is_public=True,
                )
            )

        db.commit()
        logger.info("Dummy workflow seed data ensured.")
    except Exception:
        db.rollback()
        logger.exception("Failed to seed dummy workflow data")
    finally:
        db.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.API_TITLE,
        description="Blood & Organ Donation Portal API",
        version=settings.APP_VERSION,
        docs_url="/api/v1/docs" if not settings.DEBUG else "/docs",
        redoc_url="/api/v1/redoc" if not settings.DEBUG else "/redoc",
    )
    
    # ==================== MIDDLEWARE ====================
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request ID Middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        logger.info(f"Request ID: {request_id}, Path: {request.url.path}, Method: {request.method}")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    
    # ==================== EXCEPTION HANDLERS ====================
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle custom application exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors"""
        details = []
        for error in exc.errors():
            details.append({
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "Internal server error",
                    "details": {} if not settings.DEBUG else {"error": str(exc)},
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )
    
    # ==================== ROUTES ====================
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/", tags=["Root"])
    async def root():
        """API root endpoint"""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs": "/api/v1/docs",
            "openapi": "/api/v1/openapi.json"
        }
    
    # ==================== API V1 ROUTES ====================
    @app.on_event("startup")
    def startup_tasks() -> None:
        # Ensure schema exists for local development.
        Base.metadata.create_all(bind=engine)
        seed_default_auth_users()
        seed_dummy_workflow_data()

    app.include_router(api_router)
    
    @app.get(f"{settings.API_V1_STR}/", tags=["API"])
    async def api_root():
        """API V1 root endpoint"""
        return {
            "message": "Blood & Organ Donation Portal API V1",
            "endpoints": {
                "auth": f"{settings.API_V1_STR}/auth",
                "users": f"{settings.API_V1_STR}/users",
                "donors": f"{settings.API_V1_STR}/donors",
                "recipients": f"{settings.API_V1_STR}/recipients",
                "requests": f"{settings.API_V1_STR}/requests",
                "matches": f"{settings.API_V1_STR}/matches",
                "notifications": f"{settings.API_V1_STR}/notifications",
                "admin": f"{settings.API_V1_STR}/admin",
            }
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
