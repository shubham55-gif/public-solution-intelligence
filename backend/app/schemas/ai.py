"""Schemas for local LLM text analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AITextAnalysisRequest(BaseModel):
    """Citizen-selected category and description delivered to the local model."""

    issue_category: str
    description: str


class AITextAnalysisResponse(BaseModel):
    """Public response contract for explainable text analysis."""

    analysis_available: bool
    issue_category: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    category_consistent: bool
    urgency_indicators: list[str] = Field(default_factory=list)
    hazard_indicators: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool
    explanation: str
