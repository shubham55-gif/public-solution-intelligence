"""Schemas for deterministic temporal report analysis."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisWindow(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime
    days: int = Field(ge=1)

    model_config = {"populate_by_name": True}


class TimeOfDayCounts(BaseModel):
    morning: int = Field(ge=0)
    afternoon: int = Field(ge=0)
    evening: int = Field(ge=0)
    night: int = Field(ge=0)


class TemporalAnalysisResponse(BaseModel):
    analysis_window: AnalysisWindow
    total_reports: int = Field(ge=0)
    reports_by_hour: dict[str, int]
    reports_by_day_of_week: dict[str, int]
    reports_by_date: dict[str, int]
    peak_hour: int | None = Field(default=None, ge=0, le=23)
    peak_day_of_week: str | None = None
    time_of_day: TimeOfDayCounts
    current_report_frequency: float = Field(ge=0)
    previous_report_frequency: float = Field(ge=0)
    frequency_change_percent: float
