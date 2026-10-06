"""Behavior tests for the local llama.cpp text-analysis integration."""

from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import app.services.llm_service as llm_service
from app.api.dependencies import get_development_user_id


def citizen(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def mock_llama(monkeypatch: pytest.MonkeyPatch, payload: dict, status_code: int = 200) -> None:
    monkeypatch.setattr(llm_service, "LLM_ENABLED", True)
    monkeypatch.setattr(llm_service, "LLM_BASE_URL", "http://127.0.0.1:8081/v1")
    server_response = httpx.Response(status_code, json=payload)
    server_response.request = httpx.Request(
        "POST",
        "http://127.0.0.1:8081/v1/chat/completions",
    )
    monkeypatch.setattr(llm_service.httpx, "post", Mock(return_value=server_response))


def test_valid_llm_json_is_mapped_to_public_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(
        monkeypatch,
        {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Large pothole near the bus stop.", "keywords": ["pothole", "bus stop"], "category_consistent": true, "urgency_indicators": ["large pothole"], "hazard_indicators": ["vehicles struggling to pass"], "confidence": 0.82, "needs_review": false, "explanation": "Text supports a road hazard.", "issue_category": "Road Damage"}'
                    }
                }
            ]
        },
    )

    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Large pothole near the main bus stop and vehicles are having difficulty passing."},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["analysis_available"] is True
    assert body["issue_category"] == "Road Damage"
    assert body["summary"] == "Large pothole near the bus stop."
    assert body["keywords"] == ["pothole", "bus stop"]
    assert body["category_consistent"] is True
    assert body["confidence"] == pytest.approx(0.82)
    assert body["needs_review"] is False
    assert "extra" not in body


def test_citizen_user_can_call_text_analysis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    citizen(client)
    mock_llama(
        monkeypatch,
        {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Road issue.", "keywords": ["road"], "category_consistent": true, "urgency_indicators": [], "hazard_indicators": [], "confidence": 0.5, "needs_review": false, "explanation": "Valid.", "issue_category": "Road Damage"}'
                    }
                }
            ]
        },
    )

    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Road issue."},
    )

    assert response.status_code == 200, response.text


def test_authority_user_can_call_text_analysis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(
        monkeypatch,
        {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Road issue.", "keywords": ["road"], "category_consistent": true, "urgency_indicators": [], "hazard_indicators": [], "confidence": 0.5, "needs_review": false, "explanation": "Valid.", "issue_category": "Road Damage"}'
                    }
                }
            ]
        },
    )

    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Road issue."},
    )

    assert response.status_code == 200, response.text


def test_confidence_zero_and_one_are_accepted(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    for value in (0.0, 1.0):
        mock_llama(
            monkeypatch,
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"summary": "Road issue.", "keywords": ["road"], "category_consistent": true, "urgency_indicators": ["road issue"], "hazard_indicators": ["danger"], "confidence": ' + str(value) + ', "needs_review": false, "explanation": "Valid.", "issue_category": "Road Damage"}'
                        }
                    }
                ]
            },
        )
        response = client.post(
            "/api/v1/ai/text-analyze",
            json={"issue_category": "Road Damage", "description": "Road issue."},
        )
        assert response.status_code == 200, response.text
        assert response.json()["confidence"] == value


def test_confidence_values_outside_range_are_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    for invalid in (100, -0.1, 1.1):
        mock_llama(
            monkeypatch,
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"summary": "Road issue.", "keywords": ["road"], "category_consistent": true, "urgency_indicators": ["road issue"], "hazard_indicators": ["danger"], "confidence": ' + str(invalid) + ', "needs_review": false, "explanation": "Valid.", "issue_category": "Road Damage"}'
                        }
                    }
                ]
            },
        )
        response = client.post(
            "/api/v1/ai/text-analyze",
            json={"issue_category": "Road Damage", "description": "Road issue."},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["analysis_available"] is False
        assert body["needs_review"] is True
        assert "confidence" in body["explanation"].lower() or "range" in body["explanation"].lower()


def test_missing_required_field_yields_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(
        monkeypatch,
        {
            "choices": [
                {
                    "message": {
                        "content": '{"keywords": ["pothole"], "category_consistent": true, "urgency_indicators": ["large pothole"], "hazard_indicators": ["vehicle hazard"], "confidence": 0.5, "needs_review": false, "explanation": "Missing summary.", "issue_category": "Road Damage"}'
                    }
                }
            ]
        },
    )
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Large pothole."},
    )
    body = response.json()
    assert body["analysis_available"] is False
    assert body["needs_review"] is True


def test_invalid_json_triggers_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(
        monkeypatch,
        {"choices": [{"message": {"content": "{not-json}"}}]},
    )
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Large pothole."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["analysis_available"] is False


def test_category_mismatch_sets_review_flag(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(
        monkeypatch,
        {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Large pothole.", "keywords": ["pothole"], "category_consistent": false, "urgency_indicators": ["large pothole"], "hazard_indicators": ["vehicle passage"], "confidence": 0.7, "needs_review": false, "explanation": "Model changed the category.", "issue_category": "Water Leakage"}'
                    }
                }
            ]
        },
    )
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Large pothole."},
    )
    body = response.json()
    assert body["category_consistent"] is False
    assert body["needs_review"] is True
    assert body["issue_category"] == "Road Damage"
    assert "Category mismatch" in body["explanation"]


def test_empty_description_and_disabled_llm_return_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": ""},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["analysis_available"] is False
    assert body["needs_review"] is True

    monkeypatch.setattr(llm_service, "LLM_ENABLED", False)
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Large pothole."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["analysis_available"] is False


def test_llama_server_unavailable_or_timeout_uses_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(monkeypatch, {})
    for error in (httpx.ConnectError("offline"), httpx.ReadTimeout("slow")):
        def raise_error(*args, **kwargs):
            raise error

        monkeypatch.setattr(llm_service.httpx, "post", raise_error)
        response = client.post(
            "/api/v1/ai/text-analyze",
            json={"issue_category": "Road Damage", "description": "Large pothole."},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["analysis_available"] is False
        assert body["needs_review"] is True


def test_unexpected_fields_are_not_leaked_to_public_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    mock_llama(
        monkeypatch,
        {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Road issue.", "keywords": ["road"], "category_consistent": true, "urgency_indicators": ["road issue"], "hazard_indicators": ["danger"], "confidence": 0.5, "needs_review": false, "explanation": "Valid.", "issue_category": "Road Damage", "ignored_field": "do-not-leak"}'
                    }
                }
            ]
        },
    )
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Road issue."},
    )
    body = response.json()
    assert "ignored_field" not in body
    assert body["analysis_available"] is True


def test_safety_rules_are_embedded_in_prompt(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority(client)
    assert "Do not identify individuals" in llm_service.SYSTEM_PROMPT
    assert "Do not create operational recommendations" in llm_service.SYSTEM_PROMPT
    assert "Do not change the citizen-selected issue category" in llm_service.SYSTEM_PROMPT


def test_missing_development_user_is_rejected(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = lambda: uuid4()
    response = client.post(
        "/api/v1/ai/text-analyze",
        json={"issue_category": "Road Damage", "description": "Large pothole."},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Development user does not exist"


def test_invalid_development_user_id_is_rejected(client: TestClient) -> None:
    client.app.dependency_overrides.pop(get_development_user_id)
    response = client.post(
        "/api/v1/ai/text-analyze",
        headers={"X-Development-User-Id": "not-a-uuid"},
        json={"issue_category": "Road Damage", "description": "Large pothole."},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "X-Development-User-Id must be a valid UUID"
