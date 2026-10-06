"""Authority endpoints for hotspot recurrence analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import Hotspot, User, UserRole
from app.schemas.recurrence import RecurrenceResponse
from app.services.recurrence_service import (
    RecurrencePersistenceError,
    RecurrenceService,
    RecurrenceValidationError,
)


router = APIRouter(prefix="/analytics/recurrence", tags=["recurrence-analysis"])


def recurrence_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RecurrenceService:
    return RecurrenceService(session)


def require_authority(service: RecurrenceService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Development user does not exist")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Authority role is required")


def run_analysis(
    hotspot_id: UUID,
    *,
    category: str | None,
    from_: datetime | None,
    to: datetime | None,
    period_days: int | None,
    analysis_window_days: int | None,
    service: RecurrenceService,
) -> RecurrenceResponse:
    try:
        return service.analyze(
            hotspot_id,
            category=category,
            from_=from_,
            to=to,
            period_days=period_days,
            analysis_window_days=analysis_window_days,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecurrenceValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RecurrencePersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not analyze recurrence") from exc


@router.get("/{hotspot_id}", response_model=RecurrenceResponse)
def hotspot_recurrence(
    hotspot_id: UUID,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    period_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    analysis_window_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[RecurrenceService, Depends(recurrence_service)] = None,
) -> RecurrenceResponse:
    require_authority(service, user_id)
    return run_analysis(
        hotspot_id,
        category=category,
        from_=from_,
        to=to,
        period_days=period_days,
        analysis_window_days=analysis_window_days,
        service=service,
    )


@router.get("", response_model=list[RecurrenceResponse])
def all_hotspot_recurrence(
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    period_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    analysis_window_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[RecurrenceService, Depends(recurrence_service)] = None,
) -> list[RecurrenceResponse]:
    require_authority(service, user_id)
    try:
        hotspot_ids = list(service.session.scalars(select(Hotspot.id)))
    except SQLAlchemyError as exc:
        service.session.rollback()
        raise HTTPException(status_code=500, detail="Could not retrieve hotspots") from exc
    return [
        run_analysis(
            hotspot_id,
            category=category,
            from_=from_,
            to=to,
            period_days=period_days,
            analysis_window_days=analysis_window_days,
            service=service,
        )
        for hotspot_id in hotspot_ids
    ]
