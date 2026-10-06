"""Schemas for deterministic hotspot trend analysis."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TrendWindow(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime
    days: int = Field(ge=1)

    model_config = {"populate_by_name": True}


class TrendPeriod(BaseModel):
    start: datetime
    end: datetime
    report_count: int = Field(ge=0)


class TrendResponse(BaseModel):
    hotspot_id: UUID
    total_reports: int = Field(ge=0)
    observed_periods: int = Field(ge=0)
    period_days: int = Field(ge=1)
    analysis_window_days: int = Field(ge=1)
    analysis_window: TrendWindow
    period_counts: list[TrendPeriod] = Field(default_factory=list)
    first_half_average: float = Field(ge=0)
    second_half_average: float = Field(ge=0)
    trend_change_percent: float
    trend: str
