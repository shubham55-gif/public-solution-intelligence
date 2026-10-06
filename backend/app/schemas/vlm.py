"""Schemas for local VLM image validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ValidationResult = Literal["YES", "NO", "UNCERTAIN"]


class VLMImageValidationResponse(BaseModel):
    """Public response contract for visual category consistency."""

    analysis_available: bool
    issue_category: str
    image_consistent: bool
    validation_result: ValidationResult
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool
    explanation: str
