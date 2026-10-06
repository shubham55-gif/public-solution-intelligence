"""Schemas for transparent hotspot impact snapshots and measurements."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def timezone_required(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamp must include a timezone offset")
    return value


class ImpactSnapshotRequest(BaseModel):
    measured_at: datetime | None = None

    _validate_measured_at = field_validator("measured_at")(timezone_required)


class ImpactSnapshotResponse(BaseModel):
    hotspot_id: UUID
    measured_at: datetime
    window_days: int
    risk_score: float
    report_frequency: float
    recurrence_level: str
    report_count: int


class ImpactMeasureRequest(BaseModel):
    intervention_id: UUID
    before_measured_at: datetime | None = None
    after_measured_at: datetime | None = None

    _validate_before = field_validator("before_measured_at")(timezone_required)
    _validate_after = field_validator("after_measured_at")(timezone_required)


class ImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hotspot_id: UUID
    intervention_id: UUID
    before_risk_score: float
    after_risk_score: float
    before_report_frequency: float
    after_report_frequency: float
    before_recurrence_level: str | None
    after_recurrence_level: str | None
    risk_reduction_percent: float
    report_reduction_percent: float
    measured_at: datetime


class ImpactPage(BaseModel):
    items: list[ImpactResponse] = Field(default_factory=list)
