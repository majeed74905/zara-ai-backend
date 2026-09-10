from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import jwt
from app.core.config import settings

# Token "type" claims. Only "access" tokens authenticate API requests; the others are
# single-purpose tokens delivered by email and accepted only by their own endpoint.
ACCESS = "access"
REFRESH = "refresh"
EMAIL_VERIFY = "email_verify"
PASSWORD_RESET = "password_reset"
MAGIC_LOGIN = "magic_login"


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"sub": str(subject), "exp": expire, "type": ACCESS}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"sub": str(subject), "exp": expire, "type": REFRESH}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_purpose_token(subject: Union[str, Any], purpose: str, minutes: int = 15) -> str:
    """Short-lived single-purpose token (email verification, password reset, magic login)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode = {"sub": str(subject), "exp": expire, "type": purpose}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_purpose_token(token: str, purpose: str) -> Optional[str]:
    """Return the subject if `token` is valid AND was issued for `purpose`, else None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None
    if payload.get("type") != purpose:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None
