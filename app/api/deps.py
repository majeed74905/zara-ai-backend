from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.config import settings
from app.core import security
from app.models import User
from app.schemas import token as token_schemas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = token_schemas.TokenPayload(sub=str(user_id))
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_verified:
        raise HTTPException(status_code=400, detail="User not verified")
    return current_user

def get_current_user_optional(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Returns the user if token is valid, otherwise returns None.
    Does NOT raise HTTPException for missing/invalid tokens.
    """
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_data = token_schemas.TokenPayload(sub=str(user_id))
    except (JWTError, Exception):
        # Invalid token or any other error -> Guest Mode
        return None
    
    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if not user:
        return None
        
    if not user.is_active:
        return None # Inactive users are treated as Guests (or could be blocked, but None is safer for non-blocking)
        
    return user
