from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db import get_db
from app.models import RefreshToken, User
from app.schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserMe, UserUpdate
from app.services.ratelimit import get_limiter

router = APIRouter(prefix="/auth", tags=["auth"])
# Verifying against a dummy hash keeps login timing similar for unknown emails.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _issue(db: Session, user: User) -> TokenOut:
    raw, digest = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days),
        )
    )
    db.commit()
    return TokenOut(access_token=create_access_token(str(user.id), user.role), refresh_token=raw)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    get_limiter().enforce(f"register:{_ip(request)}", 10, 3600)
    user = User(
        email=body.email.lower(),
        handle=body.handle,
        handle_lower=body.handle.lower(),
        password_hash=hash_password(body.password),
    )  # role is never taken from the client
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "ACCOUNT_EXISTS", "That email or handle is already taken.") from None
    return _issue(db, user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    get_limiter().enforce(f"login:{_ip(request)}", 20, 300)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise ApiError(401, "INVALID_CREDENTIALS", "Incorrect email or password.")
    return _issue(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if row is None or row.revoked or row.expires_at < datetime.now(UTC):
        raise ApiError(401, "INVALID_REFRESH", "Session expired. Please sign in again.")
    row.revoked = True  # rotation: every refresh token is single-use
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        db.commit()
        raise ApiError(401, "INVALID_REFRESH", "Session expired. Please sign in again.")
    db.commit()
    return _issue(db, user)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if row:
        row.revoked = True
        db.commit()


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(current_user)):
    return user


@router.patch("/me", response_model=UserMe)
def update_me(body: UserUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value.upper() if field == "country" and value else value)
    db.commit()
    return user
