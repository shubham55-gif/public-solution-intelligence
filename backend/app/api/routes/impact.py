"""Authority endpoints for hotspot intervention impact measurement."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import Intervention, User, UserRole
from app.schemas.impact import (
    ImpactMeasureRequest,
    ImpactResponse,
    ImpactSnapshotRequest,
    ImpactSnapshotResponse,
)
from app.services.impact_service import (
    ImpactPersistenceError,
    ImpactService,
    ImpactValidationError,
)


router = APIRouter(prefix="/impact", tags=["impact"])


def impact_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ImpactService:
    return ImpactService(session)


def require_authority(service: ImpactService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Development user does not exist")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Authority role is required")


@router.post("/{hotspot_id}/snapshot", response_model=ImpactSnapshotResponse)
def create_snapshot(
    hotspot_id: UUID,
    payload: ImpactSnapshotRequest,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[ImpactService, Depends(impact_service)],
) -> ImpactSnapshotResponse:
    require_authority(service, user_id)
    try:
        return ImpactSnapshotResponse.model_validate(
            service.snapshot(hotspot_id, payload.measured_at)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{hotspot_id}/measure", response_model=ImpactResponse)
def measure_impact(
    hotspot_id: UUID,
    payload: ImpactMeasureRequest,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[ImpactService, Depends(impact_service)],
) -> ImpactResponse:
    require_authority(service, user_id)
    try:
        metric = service.measure(hotspot_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImpactValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ImpactPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not store impact measurement") from exc
    return ImpactResponse.model_validate(metric)


@router.get("/interventions/{intervention_id}/impact", response_model=list[ImpactResponse])
def intervention_impact(
    intervention_id: UUID,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[ImpactService, Depends(impact_service)],
) -> list[ImpactResponse]:
    require_authority(service, user_id)
    if service.session.get(Intervention, intervention_id) is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    try:
        metrics = service.for_intervention(intervention_id)
    except ImpactPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve intervention impact") from exc
    return [ImpactResponse.model_validate(metric) for metric in metrics]


@router.get("/{hotspot_id}", response_model=ImpactResponse)
def latest_impact(
    hotspot_id: UUID,
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[ImpactService, Depends(impact_service)],
) -> ImpactResponse:
    require_authority(service, user_id)
    if not service.hotspot_exists(hotspot_id):
        raise HTTPException(status_code=404, detail="Hotspot not found")
    try:
        metric = service.latest(hotspot_id)
    except ImpactPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve impact measurement") from exc
    if metric is None:
        raise HTTPException(status_code=404, detail="Impact measurement not found")
    return ImpactResponse.model_validate(metric)
