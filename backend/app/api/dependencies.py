"""Dependencies for database sessions and authentication."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import SessionLocal
from app.models.entities import User, UserRole


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    session: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_development_user_id: Annotated[str | None, Header()] = None,
) -> User:
    """Extract and validate user from Bearer JWT or fallback X-Development-User-Id."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        try:
            payload = decode_token(token)
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            user_id = UUID(user_id_str)
        except (JWTError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            ) from exc

        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user

    if x_development_user_id:
        try:
            dev_id = UUID(x_development_user_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="X-Development-User-Id must be a valid UUID",
            ) from exc

        user = session.get(User, dev_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Development user not found",
            )
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization header (Bearer token) or X-Development-User-Id required",
    )


def get_development_user_id(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UUID:
    """Backwards-compatible dependency that returns the authenticated UUID."""
    return current_user.id


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure authenticated user has the authority role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authority role required",
        )
    return current_user

