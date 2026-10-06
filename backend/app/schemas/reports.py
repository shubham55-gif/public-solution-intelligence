"""Pydantic request, response, and pagination schemas for report endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import Form
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.models.entities import ReportStatus


class ReportSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReportStatusUpdate(BaseModel):
    status: ReportStatus


class ReportCreate(BaseModel):
    issue_category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    reported_at: datetime
    severity: ReportSeverity

    @field_validator("issue_category", "description")
    @classmethod
    def non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("reported_at")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reported_at must include a timezone offset")
        return value

    @classmethod
    def as_form(
        cls,
        issue_category: Annotated[str, Form(...)],
        description: Annotated[str, Form(...)],
        latitude: Annotated[float, Form(...)],
        longitude: Annotated[float, Form(...)],
        reported_at: Annotated[datetime, Form(...)],
        severity: Annotated[ReportSeverity, Form(...)],
    ) -> "ReportCreate":
        """Allow the validated report payload to be documented as form data."""
        try:
            return cls(
                issue_category=issue_category,
                description=description,
                latitude=latitude,
                longitude=longitude,
                reported_at=reported_at,
                severity=severity,
            )
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc


class StatusHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    old_status: ReportStatus
    new_status: ReportStatus
    changed_by_admin_name: str | None = None
    note: str | None = None
    changed_at: datetime


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    citizen_name: str | None = None
    issue_category: str
    description: str
    latitude: float
    longitude: float
    reported_at: datetime
    severity: ReportSeverity | str | None = None
    status: ReportStatus
    image_path: str | None = None
    resolution_image_path: str | None = None
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    assigned_admin_id: UUID | None = None
    assigned_admin_name: str | None = None
    resolved_by_admin_id: UUID | None = None
    resolved_by_admin_name: str | None = None
    has_ai_analysis: bool = False
    status_history: list[StatusHistoryItem] = []
    created_at: datetime
    updated_at: datetime


class ReportPage(BaseModel):
    items: list[ReportResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)

    @classmethod
    def create(cls, *, items: list[ReportResponse], page: int, page_size: int, total: int) -> "ReportPage":
        return cls(items=items, page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size) if total else 0)
