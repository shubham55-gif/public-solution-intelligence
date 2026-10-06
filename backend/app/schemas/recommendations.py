"""Schemas for deterministic hotspot recommendations."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RecommendationEvidence(BaseModel):
    risk_score: float = Field(ge=0, le=100)
    trend: str | None = None
    recurrence_level: str | None = None
    severity_index_percent: float | None = Field(default=None, ge=0, le=100)
    related_reports_count: int | None = Field(default=None, ge=0)


class RecommendationItem(BaseModel):
    action: str
    action_type: str
    priority: str
    category: str | None = None
    reason: str
    evidence: RecommendationEvidence


class RecommendationResponse(BaseModel):
    hotspot_id: UUID
    risk_score: float = Field(ge=0, le=100)
    risk_level: str
    recommendations: list[RecommendationItem] = Field(default_factory=list)
