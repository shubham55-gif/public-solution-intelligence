"""Local llama.cpp-backed LLM service with strict post-inference validation."""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import (
    LLM_BASE_URL,
    LLM_ENABLED,
    LLM_MAX_TOKENS,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from app.schemas.ai import AITextAnalysisResponse

SYSTEM_PROMPT = """You are analyzing citizen-submitted descriptions of public-space issues.
Analyze only observable information explicitly supported by the supplied text.
Do not invent facts.
Do not identify individuals.
Do not infer personal traits.
Do not judge citizen reliability.
Do not accuse anyone.
Do not predict accidents, injuries, crime, flooding, or other future events.
Do not create operational recommendations.
Do not change the citizen-selected issue category.
Return only the requested structured output.
"""


def _normalized_category(value: str) -> str:
    return value.strip().casefold()


class LLMValidationError(ValueError):
    """Raised when model output cannot be trusted."""


class LLMService:
    """Interface for replaceable local LLM integrations."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def analyze_text(self, issue_category: str, description: str) -> AITextAnalysisResponse:
        raise NotImplementedError


class LocalOpenAIChatLLMService(LLMService):
    """Small adapter around an OpenAI-compatible local llama.cpp server."""

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session=session)
        self.base_url = LLM_BASE_URL.rstrip("/")
        self.model_name = LLM_MODEL_NAME
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS
        self.timeout_seconds = LLM_TIMEOUT_SECONDS

    def analyze_text(
        self,
        issue_category: str,
        description: str,
    ) -> AITextAnalysisResponse:
        if not LLM_ENABLED:
            return self._fallback(
                issue_category,
                "LLM analysis unavailable or failed validation.",
            )

        cleaned_category = (issue_category or "").strip()
        cleaned_description = (description or "").strip()
        if not cleaned_category or not cleaned_description:
            return self._fallback(
                issue_category,
                "No descriptive text was supplied for analysis.",
            )

        try:
            payload = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_prompt(cleaned_category, cleaned_description)},
                ],
            }
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, RuntimeError, ValueError):
            return self._fallback(
                cleaned_category or issue_category,
                "LLM analysis unavailable or failed validation.",
            )

        try:
            return self._validate_model_output(cleaned_category, data)
        except LLMValidationError as exc:
            return self._fallback(
                cleaned_category or issue_category,
                f"LLM analysis unavailable or failed validation: {exc}",
            )

    def _build_user_prompt(self, issue_category: str, description: str) -> str:
        return (
            f"Selected issue category: {issue_category}\n"
            f"Description: {description}\n\n"
            "Analyze the description and return only a JSON object matching this schema:\n"
            "{\n"
            '  "summary": "<concise 1-sentence factual summary of the reported issue>",\n'
            '  "keywords": ["<observable keyword 1>", "<observable keyword 2>"],\n'
            '  "category_consistent": true,\n'
            '  "urgency_indicators": ["<e.g. HIGH, MEDIUM, LOW, or specific urgency indicator>"],\n'
            '  "hazard_indicators": ["<e.g. Public hygiene, obstruction, or NONE_DETECTED>"],\n'
            '  "confidence": 0.85,\n'
            '  "needs_review": false,\n'
            '  "explanation": "<brief factual explanation of text evidence>",\n'
            f'  "issue_category": "{issue_category}"\n'
            "}\n\n"
            "Rules:\n"
            "- Use only observable information explicitly supported by the supplied text.\n"
            "- Do not invent facts or extrapolate beyond the text.\n"
            "- Never return placeholder text like 'string' or '<string>'.\n"
            "- If no urgency is indicated by the text, return [] or ['LOW'].\n"
            "- If no hazards are indicated by the text, return ['NONE_DETECTED'].\n"
            "- category_consistent: true if description matches the selected category, false if mismatched.\n"
            "- confidence: real numeric float between 0.0 and 1.0 (e.g. 0.85).\n"
            "- Do not change the citizen-selected issue category.\n"
        )

    def _validate_model_output(
        self,
        cleaned_category: str,
        response_payload: Any,
    ) -> AITextAnalysisResponse:
        if not isinstance(response_payload, dict):
            raise LLMValidationError("LLM response was not a JSON object")

        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMValidationError("LLM response did not include any choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMValidationError("LLM choice payload had an invalid structure")

        message = first_choice.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if content is None:
            content = first_choice.get("text")
        if not isinstance(content, str) or not content.strip():
            raise LLMValidationError("LLM response content was empty")

        try:
            parsed = json.loads(self._strip_code_fence(content))
        except json.JSONDecodeError as exc:
            raise LLMValidationError("LLM response was not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise LLMValidationError("LLM response JSON was not an object")

        required_keys = [
            "summary",
            "keywords",
            "category_consistent",
            "urgency_indicators",
            "hazard_indicators",
            "confidence",
            "needs_review",
            "explanation",
            "issue_category",
        ]
        missing = [key for key in required_keys if key not in parsed]
        if missing:
            raise LLMValidationError(f"missing required fields: {', '.join(missing)}")

        summary = parsed["summary"]
        if not isinstance(summary, str):
            raise LLMValidationError("summary must be a string")

        keywords = parsed["keywords"]
        if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
            raise LLMValidationError("keywords must be a list of strings")

        urgency = parsed["urgency_indicators"]
        if not isinstance(urgency, list) or not all(isinstance(item, str) for item in urgency):
            raise LLMValidationError("urgency_indicators must be a list of strings")

        hazard = parsed["hazard_indicators"]
        if not isinstance(hazard, list) or not all(isinstance(item, str) for item in hazard):
            raise LLMValidationError("hazard_indicators must be a list of strings")

        explanation = parsed["explanation"]
        if not isinstance(explanation, str):
            raise LLMValidationError("explanation must be a string")

        confidence = parsed["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise LLMValidationError("confidence must be a real numeric value in [0.0, 1.0]")
        confidence_value = float(confidence)
        if confidence_value < 0.0 or confidence_value > 1.0:
            raise LLMValidationError(
                f"confidence value {confidence!r} is outside the allowed range [0.0, 1.0]"
            )

        category_value = parsed["issue_category"]
        if not isinstance(category_value, str):
            raise LLMValidationError("issue_category must be a string")

        raw_category_consistent = parsed["category_consistent"]
        if not isinstance(raw_category_consistent, bool):
            raise LLMValidationError("category_consistent must be a boolean")

        needs_review = parsed["needs_review"]
        if not isinstance(needs_review, bool):
            raise LLMValidationError("needs_review must be a boolean")

        # Clean keywords, urgency, and hazard lists: filter out placeholder strings and blanks
        cleaned_keywords = [
            k.strip() for k in keywords 
            if isinstance(k, str) and k.strip().lower() not in {"string", "<string>", "<observable keyword 1>", "<observable keyword 2>", "<key noun or phrase>", ""}
        ]
        cleaned_urgency = [
            u.strip() for u in urgency 
            if isinstance(u, str) and u.strip().lower() not in {"string", "<string>", "<e.g. high, medium, low, or specific urgency indicator>", "<e.g. high, medium, low, or urgency factor>", ""}
        ]
        cleaned_hazard = [
            h.strip() for h in hazard 
            if isinstance(h, str) and h.strip().lower() not in {"string", "<string>", "<e.g. public hygiene, obstruction, or none_detected>", "<e.g. public hygiene, obstruction, structural risk, or none>", ""}
        ]

        if not cleaned_urgency:
            cleaned_urgency = ["UNKNOWN"]
            needs_review = True

        if not cleaned_hazard:
            cleaned_hazard = ["UNKNOWN"]
            needs_review = True

        if isinstance(summary, str) and summary.strip().lower() in {"string", "<string>", "<concise 1-sentence factual summary of the reported issue>", "<concise 1-sentence summary of the reported issue>", ""}:
            summary = "Summary unavailable"
            needs_review = True

        category_consistent = (
            _normalized_category(category_value) == _normalized_category(cleaned_category)
        )
        if not category_consistent or not raw_category_consistent:
            category_consistent = False
            needs_review = True
            explanation = (
                "Category mismatch: model returned "
                f"'{category_value}' while the citizen selected '{cleaned_category}'. "
                "Preserving the selected category and flagging for review."
            )
        elif not explanation or explanation.strip().lower() in {"string", "<string>", "<brief factual explanation of text evidence>", ""}:
            explanation = f"Text evidence is consistent with {cleaned_category}."

        return AITextAnalysisResponse(
            analysis_available=True,
            issue_category=cleaned_category,
            summary=summary,
            keywords=cleaned_keywords,
            category_consistent=category_consistent,
            urgency_indicators=cleaned_urgency,
            hazard_indicators=cleaned_hazard,
            confidence=confidence_value,
            needs_review=needs_review,
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
    def _fallback(
        issue_category: str,
        explanation: str,
    ) -> AITextAnalysisResponse:
        selected_category = issue_category.strip() if issue_category else ""
        return AITextAnalysisResponse(
            analysis_available=False,
            issue_category=selected_category,
            summary="",
            keywords=[],
            category_consistent=False,
            urgency_indicators=["UNKNOWN"],
            hazard_indicators=["UNKNOWN"],
            confidence=0.0,
            needs_review=True,
            explanation=explanation,
        )
