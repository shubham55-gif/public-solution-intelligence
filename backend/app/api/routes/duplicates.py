"""Authority endpoints for deterministic related-report analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import User, UserRole
from app.schemas.duplicates import DuplicateCheckResponse
from app.services.duplicate_service import (
    DuplicatePersistenceError,
    DuplicateService,
    DuplicateValidationError,
)


router = APIRouter(prefix="/analytics/duplicates", tags=["duplicate-analysis"])


def duplicate_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> DuplicateService:
    return DuplicateService(session)


def require_authority(service: DuplicateService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Development user does not exist")
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authority role is required")


@router.post("/check/{report_id}", response_model=DuplicateCheckResponse)
def check_duplicates(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[DuplicateService, Depends(duplicate_service)],
) -> DuplicateCheckResponse:
    require_authority(service, user_id)
    try:
        return service.check(report_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicatePersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not analyze duplicate reports") from exc


@router.get("", response_model=list[DuplicateCheckResponse])
def list_duplicates(
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[DuplicateService, Depends(duplicate_service)] = None,
) -> list[DuplicateCheckResponse]:
    require_authority(service, user_id)
    try:
        return service.list_detected(category=category, from_=from_, to=to)
    except DuplicateValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicatePersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve duplicate reports") from exc
