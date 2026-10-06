"""Initial citizen report endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin, get_current_user, get_db_session
from app.models.entities import ReportStatus, User, UserRole
from app.schemas.reports import (
    ReportCreate,
    ReportPage,
    ReportResponse,
    ReportSeverity,
    ReportStatusUpdate,
)
from app.services.report_service import ReportPersistenceError, ReportService
from app.services.upload_service import save_report_image


router = APIRouter(prefix="/reports", tags=["reports"])
admin_router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


def report_service(session: Annotated[Session, Depends(get_db_session)]) -> ReportService:
    return ReportService(session)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: Annotated[ReportCreate, Depends(ReportCreate.as_form)],
    image: Annotated[UploadFile | None, File(description="Optional JPG, PNG, or WEBP image")] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[ReportService, Depends(report_service)] = None,
) -> ReportResponse:
    """Create a report for the authenticated user."""
    image_path: str | None = None
    saved_file: Path | None = None

    if image is not None:
        image_path, saved_file = await save_report_image(image)

    try:
        report = service.create_report(data=payload, user_id=current_user.id, image_path=image_path)
        # Automatic AI/VLM analysis trigger on report creation
        try:
            from app.services.llm_service import LocalOpenAIChatLLMService
            from app.services.vlm_service import LocalOpenAIMultimodalVLMService
            from app.services.report_intelligence_service import ReportIntelligenceService
            intelligence = ReportIntelligenceService(
                session=service.session,
                llm=LocalOpenAIChatLLMService(session=service.session),
                vlm=LocalOpenAIMultimodalVLMService(session=service.session),
            )
            intelligence.analyze(report.id)
            service.session.refresh(report)
        except Exception:
            pass # Keep citizen report intact even if AI analysis is unavailable
    except ReportPersistenceError as exc:
        if saved_file is not None:
            saved_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create report",
        ) from exc

    return ReportResponse.model_validate(report)


@router.get("/my", response_model=ReportPage)
def list_my_reports(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    service: Annotated[ReportService, Depends(report_service)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> ReportPage:
    """List reports strictly owned by the authenticated citizen."""
    try:
        reports, total = service.list_reports(page=page, page_size=page_size, user_id=current_user.id)
    except ReportPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve reports") from exc
    return ReportPage.create(
        items=[ReportResponse.model_validate(report) for report in reports],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("", response_model=ReportPage)
def list_reports(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    status_filter: Annotated[ReportStatus | None, Query(alias="status")] = None,
    severity: Annotated[ReportSeverity | None, Query()] = None,
    service: Annotated[ReportService, Depends(report_service)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> ReportPage:
    """Return a paginated report list for authorities or feed."""
    try:
        reports, total = service.list_reports(
            page=page,
            page_size=page_size,
            category=category,
            status=status_filter,
            severity=severity,
        )
    except ReportPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve reports") from exc
    return ReportPage.create(
        items=[ReportResponse.model_validate(report) for report in reports],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID,
    service: Annotated[ReportService, Depends(report_service)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> ReportResponse:
    """Return one report by UUID, enforcing citizen isolation."""
    try:
        report = service.get_report(report_id)
    except ReportPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not retrieve report") from exc
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    # Enforce citizen isolation: citizens can only view their own reports.
    # Authorities/Admins can view any report.
    if not current_user.is_admin and report.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only view your own reports",
        )

    return ReportResponse.model_validate(report)


@admin_router.patch("/{report_id}/status", response_model=ReportResponse)
def update_report_status(
    report_id: UUID,
    payload: ReportStatusUpdate,
    admin_user: Annotated[User, Depends(get_current_admin)] = None,
    service: Annotated[ReportService, Depends(report_service)] = None,
) -> ReportResponse:
    """Update a report status (authority only, tracks admin ID)."""
    try:
        report = service.update_status(
            report_id=report_id,
            new_status=payload.status,
            changed_by=admin_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc
    except ReportPersistenceError as exc:
        raise HTTPException(status_code=500, detail="Could not update report status") from exc
    return ReportResponse.model_validate(report)


@admin_router.post("/{report_id}/resolve", response_model=ReportResponse)
async def resolve_report_endpoint(
    report_id: UUID,
    resolution_note: Annotated[str | None, Form(description="Optional note about how it was resolved")] = None,
    resolution_image: Annotated[UploadFile | None, File(description="Optional after-resolution photo")] = None,
    image: Annotated[UploadFile | None, File(description="Optional fallback after-resolution photo")] = None,
    admin_user: Annotated[User, Depends(get_current_admin)] = None,
    service: Annotated[ReportService, Depends(report_service)] = None,
) -> ReportResponse:
    """Resolve a report with an optional after-resolution photo and note (authority only)."""
    uploaded_file = resolution_image if (resolution_image is not None and resolution_image.filename) else image
    image_path: str | None = None
    saved_file: Path | None = None
    if uploaded_file is not None and uploaded_file.filename:
        image_path, saved_file = await save_report_image(uploaded_file)

    try:
        report = service.resolve_report(
            report_id=report_id,
            changed_by=admin_user.id,
            resolution_note=resolution_note,
            resolution_image_path=image_path,
        )
    except LookupError as exc:
        if saved_file is not None:
            saved_file.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="Report not found") from exc
    except ReportPersistenceError as exc:
        if saved_file is not None:
            saved_file.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not resolve report") from exc

    return ReportResponse.model_validate(report)
