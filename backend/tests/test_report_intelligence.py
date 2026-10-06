"""Focused tests for unified report intelligence orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

import app.services.report_intelligence_service as orchestration
from app.api.dependencies import get_development_user_id
from app.models.entities import AIAnalysis, Report, ReportStatus, VlmValidationStatus
from app.schemas.ai import AITextAnalysisResponse
from app.schemas.vlm import VLMImageValidationResponse
from app.services.llm_service import LLMService
from app.services.vlm_service import VLMService


class FakeLLM(LLMService):
    def __init__(self, result: AITextAnalysisResponse):
        super().__init__()
        self.result = result

    def analyze_text(self, issue_category: str, description: str) -> AITextAnalysisResponse:
        return self.result


class FakeVLM(VLMService):
    def __init__(self, result: VLMImageValidationResponse):
        super().__init__()
        self.result = result
        self.calls = 0

    def validate_image(self, issue_category: str, image_bytes: bytes, media_type: str):
        self.calls += 1
        return self.result


def text_result(*, available: bool = True, consistent: bool = True) -> AITextAnalysisResponse:
    return AITextAnalysisResponse(
        analysis_available=available,
        issue_category="Road Damage",
        summary="A reported road issue.",
        keywords=["road"],
        category_consistent=consistent,
        urgency_indicators=[],
        hazard_indicators=["road obstruction"] if available else [],
        confidence=0.8 if available else 0.0,
        needs_review=not available or not consistent,
        explanation="Validated text evidence." if available else "Text unavailable.",
    )


def image_result(result: str = "YES", *, available: bool = True):
    return VLMImageValidationResponse(
        analysis_available=available,
        issue_category="Road Damage",
        image_consistent=result == "YES",
        validation_result=result,
        confidence=0.8 if available else 0.0,
        needs_review=not available or result == "UNCERTAIN",
        explanation="Validated visual evidence.",
    )


def add_report(client, *, image_path: str | None = None):
    with client.testing_session_factory() as session:
        report = Report(
            user_id=client.development_user_id,
            issue_category="Road Damage",
            description="A pothole is blocking part of the road.",
            latitude=28.6,
            longitude=77.2,
            reported_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            severity="high",
            status=ReportStatus.PENDING,
            image_path=image_path,
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return report.id


def install_service_override(client, llm, vlm):
    from app.api.routes.ai import report_intelligence_service

    def dependency():
        session = client.testing_session_factory()
        llm.session = session
        vlm.session = session
        return orchestration.ReportIntelligenceService(
            session=session,
            llm=llm,
            vlm=vlm,
        )

    client.app.dependency_overrides[report_intelligence_service] = dependency


def test_text_and_image_are_combined_and_persisted(client, tmp_path: Path):
    image_root = tmp_path / "uploads"
    image_file = image_root / "reports" / "road.jpg"
    image_file.parent.mkdir(parents=True)
    image_file.write_bytes(b"image")
    orchestration.UPLOADS_DIR = image_root
    report_id = add_report(client, image_path="uploads/reports/road.jpg")
    vlm = FakeVLM(image_result("YES"))
    install_service_override(client, FakeLLM(text_result()), vlm)

    response = client.post(f"/api/v1/ai/analyze-report/{report_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["analysis_available"] is True
    assert body["image_analysis"]["validation_result"] == "YES"
    assert body["evidence_consistency"]["agreement"] is True
    assert body["overall_needs_review"] is False
    assert vlm.calls == 1
    with client.testing_session_factory() as session:
        saved = session.scalar(select(AIAnalysis).where(AIAnalysis.report_id == report_id))
        assert saved is not None
        assert saved.vlm_validation_status == VlmValidationStatus.VALIDATED


def test_no_image_does_not_call_vlm_and_is_not_by_itself_review(client):
    report_id = add_report(client)
    vlm = FakeVLM(image_result("YES"))
    install_service_override(client, FakeLLM(text_result()), vlm)

    response = client.post(f"/api/v1/ai/analyze-report/{report_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["image_analysis"]["available"] is False
    assert "no usable image" in body["image_analysis"]["explanation"].lower()
    assert body["evidence_consistency"]["agreement"] is None
    assert body["overall_needs_review"] is False
    assert vlm.calls == 0


def test_invalid_image_reference_is_not_exposed_or_sent_to_vlm(client):
    report_id = add_report(client, image_path="uploads/reports/missing.jpg")
    vlm = FakeVLM(image_result("YES"))
    install_service_override(client, FakeLLM(text_result()), vlm)

    response = client.post(f"/api/v1/ai/analyze-report/{report_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["image_analysis"]["available"] is False
    assert "missing.jpg" not in body["explanation"]
    assert vlm.calls == 0


@pytest.mark.parametrize(
    ("vlm_result", "expected_review", "expected_agreement"),
    [("YES", False, True), ("NO", True, False), ("UNCERTAIN", True, False)],
)
def test_visual_result_controls_agreement_and_review(
    client,
    vlm_result: str,
    expected_review: bool,
    expected_agreement: bool,
    tmp_path: Path,
):
    image_root = tmp_path / "uploads"
    image_file = image_root / "reports" / "road.jpg"
    image_file.parent.mkdir(parents=True)
    image_file.write_bytes(b"image")
    orchestration.UPLOADS_DIR = image_root
    report_id = add_report(client, image_path="uploads/reports/road.jpg")
    install_service_override(client, FakeLLM(text_result()), FakeVLM(image_result(vlm_result)))

    body = client.post(f"/api/v1/ai/analyze-report/{report_id}").json()

    assert body["overall_needs_review"] is expected_review
    assert body["evidence_consistency"]["agreement"] is expected_agreement


def test_text_failure_keeps_visual_evidence_but_requires_review(client, tmp_path: Path):
    image_root = tmp_path / "uploads"
    image_file = image_root / "reports" / "road.jpg"
    image_file.parent.mkdir(parents=True)
    image_file.write_bytes(b"image")
    orchestration.UPLOADS_DIR = image_root
    report_id = add_report(client, image_path="uploads/reports/road.jpg")
    install_service_override(client, FakeLLM(text_result(available=False)), FakeVLM(image_result()))

    body = client.post(f"/api/v1/ai/analyze-report/{report_id}").json()

    assert body["text_analysis"]["available"] is False
    assert body["image_analysis"]["available"] is True
    assert body["overall_needs_review"] is True


def test_vlm_failure_keeps_text_evidence_and_requires_review(client, tmp_path: Path):
    image_root = tmp_path / "uploads"
    image_file = image_root / "reports" / "road.jpg"
    image_file.parent.mkdir(parents=True)
    image_file.write_bytes(b"image")
    orchestration.UPLOADS_DIR = image_root
    report_id = add_report(client, image_path="uploads/reports/road.jpg")
    install_service_override(
        client,
        FakeLLM(text_result()),
        FakeVLM(image_result("UNCERTAIN", available=False)),
    )

    body = client.post(f"/api/v1/ai/analyze-report/{report_id}").json()

    assert body["text_analysis"]["available"] is True
    assert body["image_analysis"]["available"] is False
    assert body["overall_needs_review"] is True


def test_missing_report_and_invalid_user_are_rejected(client):
    from uuid import uuid4

    install_service_override(client, FakeLLM(text_result()), FakeVLM(image_result()))
    missing = client.post(f"/api/v1/ai/analyze-report/{uuid4()}")
    assert missing.status_code == 404

    client.app.dependency_overrides[get_development_user_id] = lambda: uuid4()
    response = client.post(f"/api/v1/ai/analyze-report/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["citizen", "authority"])
def test_existing_citizen_and_authority_users_can_request_analysis(client, role):
    from app.api.routes.ai import report_intelligence_service

    report_id = add_report(client)
    user_id = (
        client.development_user_id
        if role == "citizen"
        else client.authority_user_id
    )
    client.app.dependency_overrides[get_development_user_id] = lambda: user_id
    install_service_override(client, FakeLLM(text_result()), FakeVLM(image_result()))

    response = client.post(f"/api/v1/ai/analyze-report/{report_id}")

    assert response.status_code == 200, response.text
    client.app.dependency_overrides.pop(report_intelligence_service, None)


def test_invalid_development_user_uuid_is_rejected(client):
    client.app.dependency_overrides.pop(get_development_user_id, None)

    response = client.post(
        "/api/v1/ai/analyze-report/00000000-0000-0000-0000-000000000000",
        headers={"X-Development-User-Id": "not-a-uuid"},
    )

    assert response.status_code == 422


def test_repeated_analysis_updates_one_persisted_record(client):
    report_id = add_report(client)
    install_service_override(client, FakeLLM(text_result()), FakeVLM(image_result()))

    first = client.post(f"/api/v1/ai/analyze-report/{report_id}")
    second = client.post(f"/api/v1/ai/analyze-report/{report_id}")

    assert first.status_code == second.status_code == 200
    with client.testing_session_factory() as session:
        records = session.scalars(select(AIAnalysis).where(AIAnalysis.report_id == report_id)).all()
        assert len(records) == 1
