"""Opaque sessions: only token hashes are stored in PostgreSQL."""
import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import AuthSession, User, utcnow

DB = Annotated[Session, Depends(get_db)]
password_hasher = PasswordHash.recommended()
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def start_session(db: Session, user: User, response: Response, old_token: str | None):
    now = utcnow()
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    if old_token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(old_token)))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id,
                       expires_at=now + timedelta(hours=config.SESSION_HOURS)))
    db.commit()
    response.set_cookie(config.COOKIE_NAME, token, max_age=config.SESSION_HOURS * 3600,
                        httponly=True, secure=config.COOKIE_SECURE, samesite="lax", path="/api")


def current_user(request: Request, db: DB) -> User:
    token = request.cookies.get(config.COOKIE_NAME)
    if not token or len(token) > 128:
        raise HTTPException(401, "Please sign in to continue.")
    session = db.scalar(select(AuthSession).where(
        AuthSession.token_hash == token_hash(token), AuthSession.expires_at > utcnow()))
    if not session or not session.user.is_active:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    return session.user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Only an administrator can change ticket details.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]

# Local single-process limiter; deployment must add a shared edge/Redis limit.
_attempts: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def limit_auth(request: Request, action: str):
    host = request.client.host if request.client else "unknown"
    key = action + ":" + host
    seconds, limit = (300, 20) if action == "login" else (1800, 10)
    now = time.monotonic()
    with _lock:
        # Remove idle keys so the dictionary does not grow without bound.
        for old in [k for k, values in _attempts.items() if not values or values[-1] < now - 1800]:
            del _attempts[old]
        values = _attempts[key]
        while values and values[0] <= now - seconds:
            values.popleft()
        if len(values) >= limit:
            raise HTTPException(429, "Too many attempts. Please wait before trying again.",
                                headers={"Retry-After": str(seconds)})
        values.append(now)
