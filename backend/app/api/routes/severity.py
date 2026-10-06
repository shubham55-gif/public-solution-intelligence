"""Authority endpoints for hotspot severity aggregation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import Hotspot, User, UserRole
from app.schemas.severity import SeverityAggregationResponse
from app.services.severity_service import (
    SeverityPersistenceError,
    SeverityService,
    SeverityValidationError,
)


router = APIRouter(prefix="/analytics/severity", tags=["severity-analysis"])


def severity_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SeverityService:
    return SeverityService(session)


def require_authority(service: SeverityService, user_id: UUID) -> None:
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
    service: SeverityService,
) -> SeverityAggregationResponse:
    try:
        return service.analyze(hotspot_id, category=category, from_=from_, to=to)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SeverityValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SeverityPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not aggregate severity") from exc


@router.get("", response_model=list[SeverityAggregationResponse])
def all_hotspot_severity(
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[SeverityService, Depends(severity_service)] = None,
) -> list[SeverityAggregationResponse]:
    require_authority(service, user_id)
    try:
        service.validate_range(from_, to)
    except SeverityValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        hotspot_ids = list(service.session.scalars(select(Hotspot.id)))
    except SQLAlchemyError as exc:
        service.session.rollback()
        raise HTTPException(status_code=500, detail="Could not retrieve hotspots") from exc
    return [
        run_analysis(hotspot_id, category=category, from_=from_, to=to, service=service)
        for hotspot_id in hotspot_ids
    ]


@router.get("/{hotspot_id}", response_model=SeverityAggregationResponse)
def hotspot_severity(
    hotspot_id: UUID,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[SeverityService, Depends(severity_service)] = None,
) -> SeverityAggregationResponse:
    require_authority(service, user_id)
    return run_analysis(hotspot_id, category=category, from_=from_, to=to, service=service)
