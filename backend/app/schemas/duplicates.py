"""Schemas for deterministic related-report analysis."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelatedReport(BaseModel):
    report_id: UUID
    distance_meters: float = Field(ge=0)
    time_difference_hours: float = Field(ge=0)
    same_category: bool
    reasons: list[str] = Field(default_factory=list)


class DuplicateCheckResponse(BaseModel):
    report_id: UUID
    related_reports: list[RelatedReport] = Field(default_factory=list)
    likely_duplicate: bool


class DuplicateAnalysisFilters(BaseModel):
    category: str | None = None
    from_: datetime | None = None
    to: datetime | None = None


class DuplicateAnalysisPage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[DuplicateCheckResponse] = Field(default_factory=list)
