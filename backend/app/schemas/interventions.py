"""Request and response schemas for authority intervention management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.entities import InterventionStatus


def require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamps must include a timezone offset")
    return value


class InterventionStatusValue(str, Enum):
    PLANNED = InterventionStatus.PLANNED.value
    IN_PROGRESS = InterventionStatus.IN_PROGRESS.value
    COMPLETED = InterventionStatus.COMPLETED.value


class InterventionCreate(BaseModel):
    hotspot_id: UUID
    action_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    assigned_unit: str | None = Field(default=None, max_length=255)
    status: InterventionStatusValue = InterventionStatusValue.PLANNED
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        self.started_at = require_timezone(self.started_at)
        self.completed_at = require_timezone(self.completed_at)
        return self


class InterventionUpdate(BaseModel):
    action_type: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1)
    assigned_unit: str | None = Field(default=None, max_length=255)
    status: InterventionStatusValue | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        self.started_at = require_timezone(self.started_at)
        self.completed_at = require_timezone(self.completed_at)
        return self


class InterventionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hotspot_id: UUID
    action_type: str
    description: str
    assigned_unit: str | None
    status: InterventionStatus
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InterventionPage(BaseModel):
    items: list[InterventionResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
