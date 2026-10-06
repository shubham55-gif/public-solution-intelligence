"""Schemas for deterministic DBSCAN hotspot detection."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HotspotSummary(BaseModel):
    hotspot_id: UUID
    latitude: float
    longitude: float
    report_count: int = Field(ge=1)


class HotspotDetectionResponse(BaseModel):
    clusters_detected: int = Field(ge=0)
    reports_analyzed: int = Field(ge=0)
    reports_clustered: int = Field(ge=0)
    noise_reports: int = Field(ge=0)
    hotspots: list[HotspotSummary] = Field(default_factory=list)


class HotspotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hotspot_id: UUID
    latitude: float
    longitude: float
    report_count: int
