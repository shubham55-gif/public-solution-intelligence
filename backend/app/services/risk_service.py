"""Deterministic, read-only, explainable hotspot risk scoring."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    RISK_DUPLICATE_COUNT_CAP,
    RISK_DUPLICATE_WEIGHT,
    RISK_RECURRENCE_WEIGHT,
    RISK_SEVERITY_WEIGHT,
    RISK_SPATIAL_REPORT_COUNT_CAP,
    RISK_SPATIAL_WEIGHT,
    RISK_TEMPORAL_FREQUENCY_CAP,
    RISK_TEMPORAL_WEIGHT,
    RISK_TREND_WEIGHT,
)
from app.models.entities import Hotspot, HotspotReport, Report
from app.schemas.risk import (
    RiskComponent,
    RiskComponents,
    RiskEvidenceSummary,
    RiskResponse,
)
from app.services.duplicate_service import DuplicateService
from app.services.recurrence_service import RecurrenceService
from app.services.severity_service import SeverityService
from app.services.temporal_service import TemporalService
from app.services.trend_service import TrendService


class RiskPersistenceError(Exception):
    """Raised when risk source data cannot be read."""


class RiskValidationError(Exception):
    """Raised when risk filters or configuration are invalid."""


class RiskService:
    WEIGHTS = {
        "spatial": RISK_SPATIAL_WEIGHT,
        "temporal": RISK_TEMPORAL_WEIGHT,
        "recurrence": RISK_RECURRENCE_WEIGHT,
        "trend": RISK_TREND_WEIGHT,
        "severity": RISK_SEVERITY_WEIGHT,
        "related_reports": RISK_DUPLICATE_WEIGHT,
    }
    CAPS = {
        "spatial_report_count": RISK_SPATIAL_REPORT_COUNT_CAP,
        "temporal_frequency": RISK_TEMPORAL_FREQUENCY_CAP,
        "duplicate_count": RISK_DUPLICATE_COUNT_CAP,
    }

    def __init__(self, session: Session) -> None:
        self.session = session
        self.validate_configuration()

    @classmethod
    def validate_configuration(
        cls,
        weights: dict[str, float] | None = None,
        caps: dict[str, float] | None = None,
    ) -> None:
        configured_weights = weights or cls.WEIGHTS
        configured_caps = caps or cls.CAPS
        if not all(isfinite(value) and value >= 0 for value in configured_weights.values()):
            raise RiskValidationError("risk weights must be finite and non-negative")
        if round(sum(configured_weights.values()), 6) != 100:
            raise RiskValidationError("risk weights must sum to exactly 100")
        if not all(isfinite(value) and value > 0 for value in configured_caps.values()):
            raise RiskValidationError("risk normalization caps must be positive and finite")

    def analyze(
        self,
        hotspot_id: UUID,
        *,
        category: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> RiskResponse:
        self._validate_range(from_, to)
        hotspot, reports = self._load_hotspot_reports(hotspot_id, category, from_, to)
        temporal = TemporalService(self.session).analyze(
            hotspot_id=hotspot_id, from_=from_, to=to
        )
        recurrence = RecurrenceService(self.session).analyze(
            hotspot_id, category=category, from_=from_, to=to
        )
        trend = TrendService(self.session).analyze(
            hotspot_id, category=category, from_=from_, to=to
        )
        severity = SeverityService(self.session).analyze(
            hotspot_id, category=category, from_=from_, to=to
        )
        related_count = self._related_report_count(reports)
        temporal_report_count = temporal.total_reports if category is None else len(reports)
        temporal_frequency = (
            temporal.current_report_frequency
            if category is None
            else len(reports) / temporal.analysis_window.days
        )

        components = RiskComponents(
            spatial=self._component(
                min(len(reports) / self.CAPS["spatial_report_count"] * 100, 100),
                "spatial",
                bool(reports),
                "No reports matched the selected filters" if not reports else None,
            ),
            temporal=self._component(
                min(
                    temporal_frequency
                    / self.CAPS["temporal_frequency"]
                    * 100,
                    100,
                ),
                "temporal",
                temporal_report_count > 0,
                "No temporal reports matched the selected filters"
                if temporal_report_count == 0
                else None,
            ),
            recurrence=self._component(
                {"none": 0, "low": 33.33, "moderate": 66.67, "high": 100}.get(
                    recurrence.recurrence_level, 0
                ),
                "recurrence",
                recurrence.total_reports > 0,
                "No recurrence evidence was available"
                if recurrence.total_reports == 0
                else None,
            ),
            trend=self._component(
                {
                    "increasing": 100,
                    "stable": 50,
                    "decreasing": 0,
                    "insufficient_data": 0,
                }.get(trend.trend, 0),
                "trend",
                trend.trend != "insufficient_data",
                "Insufficient observations for trend classification"
                if trend.trend == "insufficient_data"
                else None,
            ),
            severity=self._component(
                severity.severity_index_percent,
                "severity",
                severity.valid_severity_reports > 0,
                "No valid severity evidence was available"
                if severity.valid_severity_reports == 0
                else None,
            ),
            related_reports=self._component(
                min(related_count / self.CAPS["duplicate_count"] * 100, 100),
                "related_reports",
                bool(reports),
                "No reports matched the selected filters" if not reports else None,
            ),
        )
        score = round(
            sum(
                component.points
                for component in (
                    components.spatial,
                    components.temporal,
                    components.recurrence,
                    components.trend,
                    components.severity,
                    components.related_reports,
                )
            ),
            2,
        )
        score = min(100.0, max(0.0, score))
        return RiskResponse(
            hotspot_id=hotspot.id,
            risk_score=score,
            risk_level=self._risk_level(score),
            components=components,
            evidence_summary=RiskEvidenceSummary(
                report_count=len(reports),
                recurrence_level=recurrence.recurrence_level,
                trend=trend.trend,
                severity_index_percent=severity.severity_index_percent,
                related_reports_count=related_count,
            ),
        )

    def _component(
        self, percent: float, name: str, available: bool, reason: str | None
    ) -> RiskComponent:
        bounded = min(100.0, max(0.0, percent))
        return RiskComponent(
            percent=round(bounded, 2),
            weight=self.WEIGHTS[name],
            points=round(bounded * self.WEIGHTS[name] / 100, 2),
            available=available,
            reason=reason,
        )

    def _load_hotspot_reports(
        self,
        hotspot_id: UUID,
        category: str | None,
        from_: datetime | None,
        to: datetime | None,
    ) -> tuple[Hotspot, list[Report]]:
        try:
            hotspot = self.session.get(Hotspot, hotspot_id)
            if hotspot is None:
                raise LookupError("Hotspot not found")
            reports = list(
                self.session.scalars(
                    select(Report)
                    .join(HotspotReport, HotspotReport.report_id == Report.id)
                    .where(HotspotReport.hotspot_id == hotspot_id)
                )
            )
            normalized_category = category.strip().casefold() if category else None
            start = self._to_utc(from_) if from_ else None
            end = self._to_utc(to) if to else None
            return hotspot, [
                report
                for report in reports
                if (normalized_category is None
                    or report.issue_category.strip().casefold() == normalized_category)
                and (start is None or start <= self._to_utc(report.reported_at))
                and (end is None or self._to_utc(report.reported_at) <= end)
            ]
        except LookupError:
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RiskPersistenceError("Could not retrieve risk reports") from exc

    def _related_report_count(self, reports: list[Report]) -> int:
        report_ids = {report.id for report in reports}
        related_ids: set[UUID] = set()
        duplicate_service = DuplicateService(self.session)
        for report in reports:
            analysis = duplicate_service._analyze(
                report, [candidate for candidate in reports if candidate.id != report.id]
            )
            related_ids.update(
                related.report_id
                for related in analysis.related_reports
                if related.report_id in report_ids
            )
        return len(related_ids)

    @staticmethod
    def _validate_range(from_: datetime | None, to: datetime | None) -> None:
        if from_ is not None and (from_.tzinfo is None or from_.utcoffset() is None):
            raise RiskValidationError("from must include a timezone offset")
        if to is not None and (to.tzinfo is None or to.utcoffset() is None):
            raise RiskValidationError("to must include a timezone offset")
        if from_ and to and RiskService._to_utc(to) < RiskService._to_utc(from_):
            raise RiskValidationError("to must be greater than or equal to from")

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _risk_level(score: float) -> str:
        if score < 25:
            return "low"
        if score < 50:
            return "moderate"
        if score < 75:
            return "high"
        return "critical"
