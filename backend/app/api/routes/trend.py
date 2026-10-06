"""Authority endpoints for hotspot trend analysis."""

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
from app.schemas.trend import TrendResponse
from app.services.trend_service import (
    TrendPersistenceError,
    TrendService,
    TrendValidationError,
)


router = APIRouter(prefix="/analytics/trend", tags=["trend-analysis"])


def trend_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> TrendService:
    return TrendService(session)


def require_authority(service: TrendService, user_id: UUID) -> None:
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
    service: TrendService,
) -> TrendResponse:
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
    except TrendValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TrendPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not analyze trend") from exc


@router.get("", response_model=list[TrendResponse])
def all_hotspot_trends(
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    period_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    analysis_window_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[TrendService, Depends(trend_service)] = None,
) -> list[TrendResponse]:
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


@router.get("/{hotspot_id}", response_model=TrendResponse)
def hotspot_trend(
    hotspot_id: UUID,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    period_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    analysis_window_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[TrendService, Depends(trend_service)] = None,
) -> TrendResponse:
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
