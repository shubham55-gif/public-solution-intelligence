"""Authority endpoints for explainable hotspot risk scoring."""

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
from app.schemas.risk import RiskResponse
from app.services.risk_service import (
    RiskPersistenceError,
    RiskService,
    RiskValidationError,
)


router = APIRouter(prefix="/analytics/risk", tags=["risk-analysis"])


def risk_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RiskService:
    return RiskService(session)


def require_authority(service: RiskService, user_id: UUID) -> None:
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
    service: RiskService,
) -> RiskResponse:
    try:
        return service.analyze(
            hotspot_id, category=category, from_=from_, to=to
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RiskValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RiskPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not calculate risk") from exc


@router.get("", response_model=list[RiskResponse])
def all_hotspot_risk(
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[RiskService, Depends(risk_service)] = None,
) -> list[RiskResponse]:
    require_authority(service, user_id)
    try:
        service._validate_range(from_, to)
        hotspot_ids = list(service.session.scalars(select(Hotspot.id)))
    except RiskValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        service.session.rollback()
        raise HTTPException(status_code=500, detail="Could not retrieve hotspots") from exc
    return [
        run_analysis(
            hotspot_id, category=category, from_=from_, to=to, service=service
        )
        for hotspot_id in hotspot_ids
    ]


@router.get("/{hotspot_id}", response_model=RiskResponse)
def hotspot_risk(
    hotspot_id: UUID,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[RiskService, Depends(risk_service)] = None,
) -> RiskResponse:
    require_authority(service, user_id)
    return run_analysis(
        hotspot_id, category=category, from_=from_, to=to, service=service
    )
