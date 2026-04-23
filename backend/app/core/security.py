# Security Utilities - JWT & Password Hashing
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import base64
import hashlib
import hmac
import os

from jose import JWTError, jwt
from app.config import settings
from app.core.exceptions import AuthenticationError


class SecurityManager:
    """Centralized security operations"""

    PBKDF2_ALGORITHM = "sha256"
    PBKDF2_ITERATIONS = 260000
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using PBKDF2-SHA256."""
        password_bytes = password.encode("utf-8")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            SecurityManager.PBKDF2_ALGORITHM,
            password_bytes,
            salt,
            SecurityManager.PBKDF2_ITERATIONS,
        )
        salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
        digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii")
        return (
            f"pbkdf2_{SecurityManager.PBKDF2_ALGORITHM}"
            f"${SecurityManager.PBKDF2_ITERATIONS}"
            f"${salt_b64}"
            f"${digest_b64}"
        )
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hashed version."""
        try:
            scheme, iterations, salt_b64, digest_b64 = hashed_password.split("$", 3)
            if scheme != f"pbkdf2_{SecurityManager.PBKDF2_ALGORITHM}":
                return False

            salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
            actual = hashlib.pbkdf2_hmac(
                SecurityManager.PBKDF2_ALGORITHM,
                plain_password.encode("utf-8"),
                salt,
                int(iterations),
            )
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token (long-lived)"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    @staticmethod
    def extract_user_id_from_token(token: str) -> str:
        """Extract user_id from JWT token"""
        payload = SecurityManager.verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token does not contain user_id")
        return user_id
    
    @staticmethod
    def extract_user_role_from_token(token: str) -> str:
        """Extract user role from JWT token"""
        payload = SecurityManager.verify_token(token)
        role = payload.get("role")
        if not role:
            raise AuthenticationError("Token does not contain role")
        return role


# Utility functions for token creation
def create_user_tokens(user_id: str, role: str, email: str) -> Dict[str, str]:
    """Create both access and refresh tokens for a user"""
    access_token_data = {
        "sub": user_id,
        "role": role,
        "email": email,
        "type": "access"
    }
    refresh_token_data = {
        "sub": user_id,
        "role": role,
        "type": "refresh"
    }
    
    access_token = SecurityManager.create_access_token(access_token_data)
    refresh_token = SecurityManager.create_refresh_token(refresh_token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer"
    }


# Generate OTP for email/phone verification
def generate_otp() -> str:
    """Generate 6-digit OTP"""
    import random
    return "".join([str(random.randint(0, 9)) for _ in range(6)])
