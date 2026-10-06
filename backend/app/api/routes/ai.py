"""Development-user local LLM text analysis API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_development_user_id
from app.core.config import MAX_IMAGE_SIZE_BYTES
from app.models.entities import Report, User
from app.schemas.orchestration import (
    EvidenceConsistency,
    UnifiedImageAnalysis,
    UnifiedReportIntelligenceResponse,
    UnifiedTextAnalysis,
)
from app.schemas.ai import AITextAnalysisRequest, AITextAnalysisResponse
from app.schemas.vlm import VLMImageValidationResponse
from app.services.upload_service import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
)
from app.services.llm_service import LLMService, LocalOpenAIChatLLMService
from app.services.vlm_service import (
    VLMService,
    LocalOpenAIMultimodalVLMService,
)
from app.services.report_intelligence_service import (
    ReportIntelligenceService,
    ReportNotFoundError,
)


router = APIRouter(prefix="/ai", tags=["ai-analysis"])


def llm_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LLMService:
    return LocalOpenAIChatLLMService(session=session)


def vlm_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> VLMService:
    return LocalOpenAIMultimodalVLMService(session=session)


def report_intelligence_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ReportIntelligenceService:
    return ReportIntelligenceService(
        session=session,
        llm=LocalOpenAIChatLLMService(session=session),
        vlm=LocalOpenAIMultimodalVLMService(session=session),
    )


def require_existing_user(service: LLMService | VLMService, user_id: UUID) -> None:
    user = service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Development user does not exist")


@router.post("/text-analyze", response_model=AITextAnalysisResponse)
def text_analyze(
    request: AITextAnalysisRequest,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[LLMService, Depends(llm_service)] = None,
) -> AITextAnalysisResponse:
    require_existing_user(service, user_id)
    return service.analyze_text(request.issue_category, request.description)


@router.post("/image-validate", response_model=VLMImageValidationResponse)
async def image_validate(
    issue_category: Annotated[str, Form(min_length=1, max_length=100)],
    image: Annotated[UploadFile, File(description="JPG, PNG, or WEBP image")],
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[VLMService, Depends(vlm_service)] = None,
) -> VLMImageValidationResponse:
    require_existing_user(service, user_id)

    if not issue_category.strip():
        await image.close()
        raise HTTPException(status_code=422, detail="issue_category must not be empty")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS or image.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        await image.close()
        raise HTTPException(
            status_code=422,
            detail="Image must be a JPG, PNG, or WEBP file",
        )

    try:
        image_bytes = await image.read()
    finally:
        await image.close()

    if not image_bytes:
        raise HTTPException(status_code=422, detail="Image must not be empty")
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the configured size limit",
        )

    return service.validate_image(
        issue_category.strip(),
        image_bytes,
        image.content_type,
    )


@router.get(
    "/analyze-report/{report_id}",
    response_model=UnifiedReportIntelligenceResponse,
)
def get_report_intelligence(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[ReportIntelligenceService, Depends(report_intelligence_service)] = None,
) -> UnifiedReportIntelligenceResponse:
    require_existing_user(service.llm, user_id)
    try:
        stored = service.get_analysis(report_id)
        if stored is not None:
            return stored
        report = service.session.get(Report, report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report does not exist")
        return UnifiedReportIntelligenceResponse(
            report_id=report.id,
            issue_category=report.issue_category,
            analysis_available=False,
            text_analysis=UnifiedTextAnalysis(
                available=False,
                summary="AI analysis has not been run yet.",
                keywords=[],
                category_consistent=False,
                urgency_indicators=[],
                hazard_indicators=[],
                confidence=0.0,
                needs_review=True,
                explanation="Analysis pending. Tap 'Re-run AI Analysis' to generate.",
            ),
            image_analysis=UnifiedImageAnalysis(
                available=False,
                validation_result="UNCERTAIN",
                image_consistent=False,
                confidence=0.0,
                needs_review=True,
                explanation="Visual validation pending.",
            ),
            overall_needs_review=True,
            evidence_consistency=EvidenceConsistency(
                text_category_consistent=False,
                image_category_consistent=None,
                agreement=None,
                consistency_status="UNCERTAIN",
            ),
            explanation="No AI analysis has been generated yet for this report.",
        )
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report does not exist") from exc


@router.post(
    "/analyze-report/{report_id}",
    response_model=UnifiedReportIntelligenceResponse,
)
def analyze_report(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_development_user_id)] = None,
    service: Annotated[ReportIntelligenceService, Depends(report_intelligence_service)] = None,
) -> UnifiedReportIntelligenceResponse:
    require_existing_user(service.llm, user_id)
    try:
        return service.analyze(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report does not exist") from exc

