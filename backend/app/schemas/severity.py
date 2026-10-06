"""Schemas for deterministic hotspot severity aggregation."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SeverityAggregationResponse(BaseModel):
    hotspot_id: UUID
    total_reports: int = Field(ge=0)
    valid_severity_reports: int = Field(ge=0)
    invalid_severity_reports: int = Field(ge=0)
    severity_counts: dict[str, int]
    severity_percentages: dict[str, float]
    weighted_severity_average: float = Field(ge=0)
    severity_index_percent: float = Field(ge=0, le=100)
