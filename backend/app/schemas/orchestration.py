"""Schemas for unified, validated report intelligence."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ValidationResult = Literal["YES", "NO", "UNCERTAIN"]
ConsistencyStatus = Literal["CONSISTENT", "INCONSISTENT", "UNCERTAIN"]
SeverityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
PriorityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
TrendType = Literal["INCREASING", "STABLE", "DECREASING", "UNKNOWN"]


class UnifiedTextAnalysis(BaseModel):
    available: bool
    summary: str
    keywords: list[str] = Field(default_factory=list)
    category_consistent: bool
    urgency_indicators: list[str] = Field(default_factory=list)
    hazard_indicators: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool
    explanation: str


class UnifiedImageAnalysis(BaseModel):
    available: bool
    validation_result: ValidationResult
    image_consistent: bool
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool
    explanation: str


class EvidenceConsistency(BaseModel):
    text_category_consistent: bool
    image_category_consistent: bool | None
    agreement: bool | None
    consistency_status: ConsistencyStatus = "UNCERTAIN"


class DuplicateIntelligence(BaseModel):
    is_duplicate: bool = False
    duplicate_report_id: UUID | None = None
    duplicate_reason: str | None = None
    duplicate_distance: float | None = None
    duplicate_time_difference: float | None = None


class SpatialClusterIntelligence(BaseModel):
    cluster_id: UUID | None = None
    cluster_size: int | None = None
    cluster_center_latitude: float | None = None
    cluster_center_longitude: float | None = None
    cluster_radius_meters: float | None = None
    is_hotspot: bool = False


class TemporalIntelligence(BaseModel):
    recent_report_count: int = 0
    time_window: str = "30d"
    recent_activity: str = "NORMAL"
    temporal_concentration: str = "NORMAL"


class RecurrenceIntelligence(BaseModel):
    is_recurring: bool = False
    recurrence_count: int = 0
    recurrence_window: str = "30d"
    recurrence_reason: str | None = None


class TrendIntelligence(BaseModel):
    trend: TrendType = "UNKNOWN"
    current_count: int = 0
    baseline_count: int = 0


class RiskIntelligence(BaseModel):
    risk_score: float = Field(ge=0.0, le=100.0, default=0.0)
    risk_level: RiskLevel = "LOW"
    risk_factors: list[str] = Field(default_factory=list)


class PriorityIntelligence(BaseModel):
    priority: PriorityLevel = "LOW"
    priority_reasons: list[str] = Field(default_factory=list)


class RecommendationIntelligence(BaseModel):
    recommended_action: str = "Recommendation unavailable — insufficient evidence."
    action_type: str = "inspect"
    reason: str = "Recommendation unavailable — insufficient evidence."
    is_available: bool = False


class UnifiedReportIntelligenceResponse(BaseModel):
    report_id: UUID
    issue_category: str = ""
    analysis_available: bool
    text_analysis: UnifiedTextAnalysis
    image_analysis: UnifiedImageAnalysis
    overall_needs_review: bool
    evidence_consistency: EvidenceConsistency
    explanation: str
    duplicate: DuplicateIntelligence = Field(default_factory=DuplicateIntelligence)
    spatial: SpatialClusterIntelligence = Field(default_factory=SpatialClusterIntelligence)
    temporal: TemporalIntelligence = Field(default_factory=TemporalIntelligence)
    recurrence: RecurrenceIntelligence = Field(default_factory=RecurrenceIntelligence)
    trend: TrendIntelligence = Field(default_factory=TrendIntelligence)
    severity: SeverityLevel = "LOW"
    risk: RiskIntelligence = Field(default_factory=RiskIntelligence)
    priority: PriorityLevel = "LOW"
    priority_reasons: list[str] = Field(default_factory=list)
    recommendation: RecommendationIntelligence = Field(default_factory=RecommendationIntelligence)
