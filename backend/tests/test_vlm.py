"""Behavior tests for local VLM image validation."""

from __future__ import annotations

import json
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import app.services.vlm_service as vlm_service
from app.api.dependencies import get_development_user_id


IMAGE_BYTES = b"test-image-bytes"


def citizen(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def mock_vlm(
    monkeypatch: pytest.MonkeyPatch,
    result: dict,
    status_code: int = 200,
) -> None:
    monkeypatch.setattr(vlm_service, "VLM_ENABLED", True)
    monkeypatch.setattr(vlm_service, "VLM_BASE_URL", "http://127.0.0.1:8082/v1")
    response = httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": json.dumps(result)}}]},
        request=httpx.Request("POST", "http://127.0.0.1:8082/v1/chat/completions"),
    )
    monkeypatch.setattr(vlm_service.httpx, "post", Mock(return_value=response))


def valid_result(
    *,
    validation_result: str = "YES",
    confidence: float | int = 0.8,
    category: str = "Road Damage",
    image_consistent: bool = True,
    needs_review: bool = False,
) -> dict:
    return {
        "issue_category": category,
        "image_consistent": image_consistent,
        "validation_result": validation_result,
        "confidence": confidence,
        "needs_review": needs_review,
        "explanation": "The visible image evidence is consistent with the selected category.",
    }


def post_image(client: TestClient, *, filename: str = "issue.jpg", content_type: str = "image/jpeg"):
    return client.post(
        "/api/v1/ai/image-validate",
        data={"issue_category": "Road Damage"},
        files={"image": (filename, IMAGE_BYTES, content_type)},
    )


def test_valid_yes_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    citizen(client)
    mock_vlm(monkeypatch, valid_result(validation_result="YES"))

    response = post_image(client)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "analysis_available": True,
        "issue_category": "Road Damage",
        "image_consistent": True,
        "validation_result": "YES",
        "confidence": 0.8,
        "needs_review": False,
        "explanation": "The visible image evidence is consistent with the selected category.",
    }


def test_valid_no_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    citizen(client)
    mock_vlm(
        monkeypatch,
        valid_result(validation_result="NO", image_consistent=False),
    )

    response = post_image(client)

    assert response.status_code == 200
    assert response.json()["validation_result"] == "NO"
    assert response.json()["image_consistent"] is False
    assert response.json()["needs_review"] is False


def test_uncertain_response_requires_review(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    citizen(client)
    mock_vlm(
        monkeypatch,
        valid_result(
            validation_result="UNCERTAIN",
            image_consistent=False,
            needs_review=False,
        ),
    )

    response = post_image(client)

    assert response.status_code == 200
    assert response.json()["validation_result"] == "UNCERTAIN"
    assert response.json()["needs_review"] is True


def test_confidence_boundaries_are_accepted(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    citizen(client)
    for confidence in (0.0, 1.0):
        mock_vlm(monkeypatch, valid_result(confidence=confidence))
        response = post_image(client)
        assert response.status_code == 200
        assert response.json()["confidence"] == confidence


def test_invalid_confidence_values_use_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    citizen(client)
    for confidence in (-0.1, 1.1, 100):
        mock_vlm(monkeypatch, valid_result(confidence=confidence))
        response = post_image(client)
        assert response.status_code == 200
        body = response.json()
        assert body["analysis_available"] is False
        assert body["validation_result"] == "UNCERTAIN"
        assert body["needs_review"] is True
        assert "confidence" in body["explanation"].lower()


def test_invalid_result_missing_fields_and_malformed_json_use_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    citizen(client)
    for result in (
        valid_result(validation_result="MAYBE"),
        {"issue_category": "Road Damage"},
    ):
        mock_vlm(monkeypatch, result)
        response = post_image(client)
        assert response.status_code == 200
        assert response.json()["analysis_available"] is False

    monkeypatch.setattr(vlm_service, "VLM_ENABLED", True)
    malformed = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "{not-json}"}}]},
        request=httpx.Request("POST", "http://127.0.0.1:8082/v1/chat/completions"),
    )
    monkeypatch.setattr(vlm_service.httpx, "post", Mock(return_value=malformed))
    response = post_image(client)
    assert response.status_code == 200
    assert response.json()["analysis_available"] is False


def test_category_is_preserved_and_unexpected_fields_do_not_leak(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    citizen(client)
    result = valid_result(category="water leakage")
    result["unexpected"] = "ignored"
    mock_vlm(monkeypatch, result)

    response = post_image(client)

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_available"] is False
    assert body["issue_category"] == "Road Damage"
    assert "unexpected" not in body


def test_server_unavailable_timeout_and_disabled_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    citizen(client)
    monkeypatch.setattr(vlm_service, "VLM_ENABLED", False)
    response = post_image(client)
    assert response.status_code == 200
    assert response.json()["analysis_available"] is False

    monkeypatch.setattr(vlm_service, "VLM_ENABLED", True)
    for error in (httpx.ConnectError("offline"), httpx.ReadTimeout("slow")):
        def raise_error(*args, **kwargs):
            raise error

        monkeypatch.setattr(vlm_service.httpx, "post", raise_error)
        response = post_image(client)
        assert response.status_code == 200
        assert response.json()["analysis_available"] is False


def test_invalid_and_empty_images_are_rejected(client: TestClient) -> None:
    citizen(client)
    invalid = client.post(
        "/api/v1/ai/image-validate",
        data={"issue_category": "Road Damage"},
        files={"image": ("issue.txt", IMAGE_BYTES, "text/plain")},
    )
    assert invalid.status_code == 422

    empty = client.post(
        "/api/v1/ai/image-validate",
        data={"issue_category": "Road Damage"},
        files={"image": ("issue.jpg", b"", "image/jpeg")},
    )
    assert empty.status_code == 422


def test_citizen_and_authority_users_can_call_vlm(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_vlm(monkeypatch, valid_result())
    citizen(client)
    assert post_image(client).status_code == 200

    authority(client)
    assert post_image(client).status_code == 200


def test_missing_user_is_rejected(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = lambda: uuid4()

    response = post_image(client)

    assert response.status_code == 404


def test_safety_rules_are_in_prompt(client: TestClient) -> None:
    assert "Do not identify people" in vlm_service.VLM_SYSTEM_PROMPT
    assert "Do not recognize faces" in vlm_service.VLM_SYSTEM_PROMPT
    assert "Prefer UNCERTAIN" in vlm_service.VLM_SYSTEM_PROMPT
    assert "Do not make operational recommendations" in vlm_service.VLM_SYSTEM_PROMPT
