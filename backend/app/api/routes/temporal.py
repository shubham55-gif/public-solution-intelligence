"""Authority endpoint for temporal report analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import User, UserRole
from app.schemas.temporal import TemporalAnalysisResponse
from app.services.temporal_service import (
    TemporalPersistenceError,
    TemporalService,
    TemporalValidationError,
)


router = APIRouter(prefix="/analytics/temporal", tags=["temporal-analysis"])


def temporal_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> TemporalService:
    return TemporalService(session)


def require_authority(service: TemporalService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Development user does not exist")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Authority role is required")


@router.get("", response_model=TemporalAnalysisResponse)
def analyze_temporal(
    hotspot_id: Annotated[UUID | None, Query()] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    window_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[TemporalService, Depends(temporal_service)] = None,
) -> TemporalAnalysisResponse:
    require_authority(service, user_id)
    try:
        return service.analyze(
            hotspot_id=hotspot_id,
            category=category,
            from_=from_,
            to=to,
            window_days=window_days,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TemporalValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except TemporalPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not analyze report timing") from exc
