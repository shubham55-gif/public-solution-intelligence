"""Authentication endpoints: register, login, profile, notifications, admin stats."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import (
    HotspotReport,
    Notification,
    Report,
    ReportStatus,
    User,
    UserRole,
)
from app.schemas.auth import (
    AdminStatsResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> TokenResponse:
    """Register a new citizen account."""
    existing = session.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole.CITIZEN,
    )
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role.value,
        phone=user.phone,
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> TokenResponse:
    """Authenticate citizen or admin and return a JWT."""
    user = session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role.value,
        phone=user.phone,
    )


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> UserProfileResponse:
    """Return the authenticated user's profile and report statistics."""
    # Count reports by status
    counts = session.execute(
        select(Report.status, func.count().label("cnt"))
        .where(Report.user_id == current_user.id)
        .group_by(Report.status)
    ).fetchall()

    stats = {row.status: row.cnt for row in counts}
    total = sum(stats.values())

    return UserProfileResponse(
        user_id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role.value,
        phone=current_user.phone,
        member_since=current_user.created_at.strftime("%Y-%m-%d"),
        total_reports=total,
        pending_reports=stats.get(ReportStatus.PENDING, 0),
        in_progress_reports=stats.get(ReportStatus.IN_PROGRESS, 0),
        resolved_reports=stats.get(ReportStatus.RESOLVED, 0),
    )


# ── Admin stats ───────────────────────────────────────────────────────────────

@router.get("/admin/stats", response_model=AdminStatsResponse)
def admin_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> AdminStatsResponse:
    """Return system-wide statistics for the admin dashboard (authority only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Authority role required")

    citizens = session.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.CITIZEN)
    ) or 0
    admins = session.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.AUTHORITY)
    ) or 0

    report_counts = session.execute(
        select(Report.status, func.count().label("cnt")).group_by(Report.status)
    ).fetchall()
    status_map = {row.status: row.cnt for row in report_counts}

    high_risk = session.scalar(
        select(func.count()).select_from(Report).where(
            Report.severity.in_(["high", "critical"])
        )
    ) or 0

    repeated = session.scalar(
        select(func.count()).select_from(HotspotReport)
    ) or 0

    return AdminStatsResponse(
        total_citizens=citizens,
        total_admins=admins,
        total_reports=sum(status_map.values()),
        pending=status_map.get(ReportStatus.PENDING, 0),
        in_progress=status_map.get(ReportStatus.IN_PROGRESS, 0),
        resolved=status_map.get(ReportStatus.RESOLVED, 0),
        high_risk=high_risk,
        repeated=repeated,
    )


# ── Notifications ─────────────────────────────────────────────────────────────

@notifications_router.get("")
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    """Return unread count and all notifications for the authenticated citizen."""
    notifs = session.scalars(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ).all()

    unread = sum(1 for n in notifs if not n.is_read)
    return {
        "unread_count": unread,
        "notifications": [
            {
                "id": str(n.id),
                "report_id": str(n.report_id) if n.report_id else None,
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": bool(n.is_read),
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ],
    }


@notifications_router.post("/{notification_id}/read")
def mark_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    """Mark a notification as read."""
    notif = session.get(Notification, notification_id)
    if notif is None or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    session.commit()
    return {"ok": True}


@notifications_router.post("/read-all")
def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    """Mark all of the authenticated user's notifications as read."""
    session.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    notifs = session.scalars(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    ).all()
    for n in notifs:
        n.is_read = True
    session.commit()
    return {"ok": True, "marked": len(notifs)}
