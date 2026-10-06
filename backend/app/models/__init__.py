"""SQLAlchemy ORM model exports used by Alembic metadata discovery."""

from app.models.entities import (
    AIAnalysis,
    Hotspot,
    HotspotReport,
    ImpactMetric,
    Intervention,
    Report,
    ReportStatusHistory,
    User,
)

__all__ = [
    "AIAnalysis",
    "Hotspot",
    "HotspotReport",
    "ImpactMetric",
    "Intervention",
    "Report",
    "ReportStatusHistory",
    "User",
]
