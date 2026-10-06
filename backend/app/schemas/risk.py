"""Schemas for explainable hotspot risk scoring."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RiskComponent(BaseModel):
    percent: float = Field(ge=0, le=100)
    weight: float = Field(ge=0)
    points: float = Field(ge=0)
    available: bool
    reason: str | None = None


class RiskComponents(BaseModel):
    spatial: RiskComponent
    temporal: RiskComponent
    recurrence: RiskComponent
    trend: RiskComponent
    severity: RiskComponent
    related_reports: RiskComponent


class RiskEvidenceSummary(BaseModel):
    report_count: int = Field(ge=0)
    recurrence_level: str
    trend: str
    severity_index_percent: float = Field(ge=0, le=100)
    related_reports_count: int = Field(ge=0)


class RiskResponse(BaseModel):
    hotspot_id: UUID
    risk_score: float = Field(ge=0, le=100)
    risk_level: str
    components: RiskComponents
    evidence_summary: RiskEvidenceSummary
