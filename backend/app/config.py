# Configuration Management
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    text = str(raw).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in text.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application Settings"""
    
    # App
    APP_NAME: str = "Blood & Organ Donation Portal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = _env_bool("DEBUG", False)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # API
    API_V1_STR: str = "/api/v1"
    API_TITLE: str = "Donation Portal API"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/donation_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list[str] = _env_list(
        "CORS_ORIGINS",
        [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "https://blooddonation.com",
        ],
    )
    CORS_ORIGIN_REGEX: str = os.getenv("CORS_ORIGIN_REGEX", "")
    
    # Email Service
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@blooddonation.com")
    
    # SMS Service (Twilio)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Cloud Storage (AWS S3)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME", "donation-portal")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # Geolocation
    GEOLOCATION_DEFAULT_RADIUS_KM: float = 50.0  # Default search radius
    HAVERSINE_EARTH_RADIUS_KM: float = 6371.0
    
    # Matching Algorithm
    MATCH_SEARCH_RADIUS_KM: float = 100.0
    TOP_MATCHES_RETURNED: int = 5
    URGENCY_WEIGHT_CRITICAL: float = 1.0
    URGENCY_WEIGHT_MEDIUM: float = 0.7
    URGENCY_WEIGHT_LOW: float = 0.4
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # Admin
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@blooddonation.com")
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "+919999999999")
    
    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True


settings = Settings()
