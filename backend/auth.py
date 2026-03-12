"""
JWT Authentication Module

Provides user registration, login, and token verification.
Auth is optional — set AUTH_ENABLED=true in backend/.env to require login.
When disabled (default for local dev), all endpoints remain publicly accessible.

Required packages:
  python-jose[cryptography]>=3.3.0
  passlib[bcrypt]>=1.7.4
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db, User

# ── Config ────────────────────────────────────────────────────────────────────

AUTH_ENABLED   = os.getenv("AUTH_ENABLED", "false").lower() == "true"
SECRET_KEY     = os.getenv("AUTH_SECRET_KEY", "change-me-in-production-minimum-32-chars!!")
ALGORITHM      = "HS256"
TOKEN_EXPIRE_H = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "168"))   # 7 days default

# Graceful degradation if libs not installed
try:
    from jose import jwt, JWTError
    from passlib.context import CryptContext
    _HAS_LIBS = True
    _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    _HAS_LIBS = False
    _pwd = None


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    _need_libs()
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not _HAS_LIBS:
        return False
    return _pwd.verify(plain, hashed)


# ── Token helpers ─────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    _need_libs()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_H)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict:
    _need_libs()
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


# ── User management ───────────────────────────────────────────────────────────

def register_user(db: Session, email: str, password: str, name: str = "") -> User:
    """Create a new user. Raises 409 if email already taken."""
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        name=name or email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Verify credentials. Returns User or None."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def get_current_user_optional(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Returns the authenticated User if a valid Bearer token is provided.
    Returns None if auth is disabled or no token is present.
    """
    if not AUTH_ENABLED or not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    uid = payload.get("sub")
    if not uid:
        return None
    return db.query(User).filter(User.id == uid).first()


def require_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Strict dependency — raises 401 if not authenticated."""
    user = get_current_user_optional(authorization=authorization, db=db)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# ── Internal ──────────────────────────────────────────────────────────────────

def _need_libs():
    if not _HAS_LIBS:
        raise HTTPException(
            status_code=501,
            detail=(
                "Auth libraries not installed. "
                "Run: pip install 'python-jose[cryptography]' 'passlib[bcrypt]'"
            ),
        )
