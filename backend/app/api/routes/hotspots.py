"""Authority endpoints for DBSCAN geographic hotspot detection."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.models.entities import User, UserRole
from app.schemas.hotspots import HotspotDetectionResponse, HotspotSummary
from app.services.hotspot_service import HotspotPersistenceError, HotspotService


router = APIRouter(prefix="/analytics/hotspots", tags=["hotspots"])


def hotspot_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> HotspotService:
    return HotspotService(session)


def require_authority(service: HotspotService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Development user does not exist")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Authority role is required")


@router.post("/detect", response_model=HotspotDetectionResponse)
def detect_hotspots(
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[HotspotService, Depends(hotspot_service)],
) -> HotspotDetectionResponse:
    require_authority(service, user_id)
    try:
        return service.detect()
    except HotspotPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not persist hotspot detection",
        ) from exc


@router.get("", response_model=list[HotspotSummary])
def list_hotspots(
    user_id: Annotated[UUID, Depends(get_development_user_id)],
    service: Annotated[HotspotService, Depends(hotspot_service)],
) -> list[HotspotSummary]:
    require_authority(service, user_id)
    try:
        return service.list_hotspots()
    except HotspotPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve hotspots",
        ) from exc
