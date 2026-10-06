"""Schemas for deterministic hotspot recurrence analysis."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecurrenceWindow(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime
    days: int = Field(ge=1)

    model_config = {"populate_by_name": True}


class RecurrencePeriod(BaseModel):
    period_start: datetime
    period_end: datetime
    report_count: int = Field(ge=0)
    active: bool


class RecurrenceResponse(BaseModel):
    hotspot_id: UUID
    analysis_window: RecurrenceWindow
    period_days: int = Field(ge=1)
    total_reports: int = Field(ge=0)
    observed_periods: int = Field(ge=0)
    active_periods: int = Field(ge=0)
    recurrence_ratio: float = Field(ge=0, le=1)
    longest_consecutive_periods: int = Field(ge=0)
    current_period_active: bool
    recurrence_level: str
    periods: list[RecurrencePeriod] = Field(default_factory=list)
