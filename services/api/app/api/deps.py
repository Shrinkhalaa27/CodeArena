import uuid
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db import get_db
from app.models import Role, User


def request_id_for(request: Request) -> str:
    return getattr(request.state, "request_id", uuid4().hex)


def _user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    data = decode_access_token(token)
    if not data:
        return None
    try:
        user = db.get(User, uuid.UUID(data["sub"]))
    except (ValueError, KeyError):
        return None
    return user if user and user.is_active else None


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def current_user_optional(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User | None:
    return _user_from_token(db, _bearer(authorization))


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "Authentication required.")
    return user


def require_roles(*roles: Role):
    allowed = {r.value for r in roles} | {Role.ADMIN.value}

    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:  # backend is authoritative; hiding UI is not authorization
            raise ApiError(403, "FORBIDDEN", "You do not have permission to do that.")
        return user

    return dep


def is_staff(user: User | None) -> bool:
    return bool(user and user.role in {Role.ADMIN.value, Role.CONTEST_ADMIN.value})


def now_utc() -> datetime:
    return datetime.now(UTC)
