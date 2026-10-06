"""Authority intervention endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import InterventionStatus, User, UserRole
from app.schemas.interventions import (
    InterventionCreate,
    InterventionPage,
    InterventionResponse,
    InterventionStatusValue,
    InterventionUpdate,
)
from app.services.intervention_service import (
    InterventionPersistenceError,
    InterventionService,
)


router = APIRouter(prefix="/interventions", tags=["interventions"])


def intervention_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> InterventionService:
    return InterventionService(session)


def require_authority(service: InterventionService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Development user does not exist")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Authority role is required")


@router.post("", response_model=InterventionResponse, status_code=status.HTTP_201_CREATED)
def create_intervention(
    payload: InterventionCreate,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[InterventionService, Depends(intervention_service)],
) -> InterventionResponse:
    require_authority(service, user_id)
    if not service.hotspot_exists(payload.hotspot_id):
        raise HTTPException(status_code=404, detail="Hotspot not found")
    try:
        return InterventionResponse.model_validate(service.create(payload))
    except InterventionPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not create intervention") from exc


@router.get("", response_model=InterventionPage)
def list_interventions(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    hotspot_id: UUID | None = None,
    status_filter: InterventionStatusValue | None = Query(default=None, alias="status"),
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[InterventionService, Depends(intervention_service)] = None,
) -> InterventionPage:
    require_authority(service, user_id)
    try:
        items, total = service.list(
            page=page,
            page_size=page_size,
            hotspot_id=hotspot_id,
            status=InterventionStatus(status_filter.value) if status_filter else None,
        )
    except InterventionPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not list interventions") from exc
    total_pages = (total + page_size - 1) // page_size if total else 0
    return InterventionPage(
        items=[InterventionResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{intervention_id}", response_model=InterventionResponse)
def get_intervention(
    intervention_id: UUID,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[InterventionService, Depends(intervention_service)],
) -> InterventionResponse:
    require_authority(service, user_id)
    try:
        intervention = service.get(intervention_id)
    except InterventionPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve intervention") from exc
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return InterventionResponse.model_validate(intervention)


@router.patch("/{intervention_id}", response_model=InterventionResponse)
def update_intervention(
    intervention_id: UUID,
    payload: InterventionUpdate,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[InterventionService, Depends(intervention_service)],
) -> InterventionResponse:
    require_authority(service, user_id)
    try:
        intervention = service.update(intervention_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Intervention not found") from exc
    except InterventionPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not update intervention") from exc
    return InterventionResponse.model_validate(intervention)
