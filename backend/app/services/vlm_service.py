"""Local llama.cpp-backed VLM image validation service."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import (
    VLM_BASE_URL,
    VLM_ENABLED,
    VLM_MAX_TOKENS,
    VLM_MODEL_NAME,
    VLM_TEMPERATURE,
    VLM_TIMEOUT_SECONDS,
)
from app.schemas.vlm import VLMImageValidationResponse


VLM_SYSTEM_PROMPT = """You are validating whether a citizen-provided public-space image appears visually consistent with a citizen-selected issue category.

Analyze only visible evidence in the image.

Do not identify people.
Do not recognize faces.
Do not infer identity.
Do not infer personal traits.
Do not judge citizens.
Do not determine citizen honesty.
Do not determine who caused an issue.
Do not accuse anyone.
Do not claim that a reported event is true or false.
Do not make operational recommendations.
Do not predict future events.

Your only task is to classify visual consistency with the selected public-space issue category as YES, NO, or UNCERTAIN.
Prefer UNCERTAIN when the image is blurry, dark, obstructed, ambiguous, or otherwise insufficient to determine consistency confidently.
Return only the requested structured output.
"""


class VLMValidationError(ValueError):
    """Raised when VLM output cannot be trusted."""


class VLMService:
    """Interface for replaceable local VLM integrations."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def validate_image(
        self,
        issue_category: str,
        image_bytes: bytes,
        media_type: str,
    ) -> VLMImageValidationResponse:
        raise NotImplementedError


class LocalOpenAIMultimodalVLMService(VLMService):
    """Adapter around an OpenAI-compatible local llama.cpp multimodal server."""

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session=session)
        self.base_url = VLM_BASE_URL.rstrip("/")
        self.model_name = VLM_MODEL_NAME
        self.temperature = VLM_TEMPERATURE
        self.max_tokens = VLM_MAX_TOKENS
        self.timeout_seconds = VLM_TIMEOUT_SECONDS

    def validate_image(
        self,
        issue_category: str,
        image_bytes: bytes,
        media_type: str,
    ) -> VLMImageValidationResponse:
        selected_category = (issue_category or "").strip()
        if not VLM_ENABLED:
            return self._fallback(
                selected_category,
                "VLM analysis unavailable or failed validation.",
            )
        if not selected_category or not image_bytes:
            return self._fallback(
                selected_category,
                "VLM analysis unavailable or failed validation.",
            )

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=self._request_payload(
                    selected_category,
                    image_bytes,
                    media_type,
                ),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json()
        except (httpx.HTTPError, RuntimeError, ValueError):
            return self._fallback(
                selected_category,
                "VLM analysis unavailable or failed validation.",
            )

        try:
            return self._validate_response(selected_category, response_payload)
        except VLMValidationError as exc:
            return self._fallback(
                selected_category,
                f"VLM analysis unavailable or failed validation: {exc}",
            )

    def _request_payload(
        self,
        issue_category: str,
        image_bytes: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        return {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": VLM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._build_user_prompt(issue_category),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{encoded_image}"
                            },
                        },
                    ],
                },
            ],
        }

    @staticmethod
    def _build_user_prompt(issue_category: str) -> str:
        return (
            f"Selected issue category: {issue_category}\n\n"
            "Inspect the supplied image and return only a JSON object with this schema:\n"
            "{\n"
            f'  "issue_category": "{issue_category}",\n'
            '  "image_consistent": true,\n'
            '  "validation_result": "YES",\n'
            '  "confidence": 0.85,\n'
            '  "needs_review": false,\n'
            '  "explanation": "<concise description of visible evidence in image>"\n'
            "}\n\n"
            "Classification rules:\n"
            "- YES: the image visibly contains evidence consistent with the selected category.\n"
            "- NO: the image appears visibly inconsistent with the selected category.\n"
            "- UNCERTAIN: the image is too blurry, dark, obstructed, ambiguous, or otherwise insufficient.\n"
            "- Never replace the selected issue category.\n"
            "- Never return placeholder text like 'string' or '<string>'.\n"
            "- confidence must be a real numeric value between 0.0 and 1.0 inclusive (e.g. 0.85).\n"
        )

    @staticmethod
    def _validate_response(
        selected_category: str,
        response_payload: Any,
    ) -> VLMImageValidationResponse:
        if not isinstance(response_payload, dict):
            raise VLMValidationError("VLM response was not a JSON object")

        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise VLMValidationError("VLM response did not include any choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise VLMValidationError("VLM choice payload had an invalid structure")

        message = first_choice.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if content is None:
            content = first_choice.get("text")
        if not isinstance(content, str) or not content.strip():
            raise VLMValidationError("VLM response content was empty")

        try:
            parsed = json.loads(LocalOpenAIMultimodalVLMService._strip_code_fence(content))
        except json.JSONDecodeError as exc:
            raise VLMValidationError("VLM response was not valid JSON") from exc

        required_keys = {
            "issue_category",
            "image_consistent",
            "validation_result",
            "confidence",
            "needs_review",
            "explanation",
        }
        missing = sorted(required_keys - parsed.keys()) if isinstance(parsed, dict) else sorted(required_keys)
        if missing:
            raise VLMValidationError(f"missing required fields: {', '.join(missing)}")
        if not isinstance(parsed, dict):
            raise VLMValidationError("VLM response JSON was not an object")

        returned_category = parsed["issue_category"]
        if not isinstance(returned_category, str):
            raise VLMValidationError("issue_category must be a string")
        if returned_category.strip().casefold() != selected_category.casefold():
            raise VLMValidationError("model changed the selected issue category")

        image_consistent = parsed["image_consistent"]
        if not isinstance(image_consistent, bool):
            raise VLMValidationError("image_consistent must be a boolean")

        validation_result = parsed["validation_result"]
        if validation_result not in {"YES", "NO", "UNCERTAIN"}:
            raise VLMValidationError("validation_result must be YES, NO, or UNCERTAIN")

        confidence = parsed["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise VLMValidationError("confidence must be a real numeric value in [0.0, 1.0]")
        confidence_value = float(confidence)
        if confidence_value < 0.0 or confidence_value > 1.0:
            raise VLMValidationError(
                f"confidence value {confidence!r} is outside the allowed range [0.0, 1.0]"
            )

        needs_review = parsed["needs_review"]
        if not isinstance(needs_review, bool):
            raise VLMValidationError("needs_review must be a boolean")

        explanation = parsed["explanation"]
        if not isinstance(explanation, str):
            raise VLMValidationError("explanation must be a string")

        if explanation.strip().lower() in {"string", "<string>", "<concise description of visible evidence in image>", ""}:
            if validation_result == "YES":
                explanation = f"Visible evidence in the image is consistent with {selected_category}."
            elif validation_result == "NO":
                explanation = f"Visible evidence in the image is inconsistent with {selected_category}."
            else:
                explanation = f"Image evidence is uncertain or ambiguous for {selected_category}."

        return VLMImageValidationResponse(
            analysis_available=True,
            issue_category=selected_category,
            image_consistent=image_consistent,
            validation_result=validation_result,
            confidence=confidence_value,
            needs_review=needs_review or validation_result == "UNCERTAIN",
            explanation=explanation,
        )

    @staticmethod
    def _strip_code_fence(value: str) -> str:
        text = value.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        return text

    @staticmethod
    def _fallback(issue_category: str, explanation: str) -> VLMImageValidationResponse:
        return VLMImageValidationResponse(
            analysis_available=False,
            issue_category=issue_category,
            image_consistent=False,
            validation_result="UNCERTAIN",
            confidence=0.0,
            needs_review=True,
            explanation=explanation,
        )
