"""Read-only, explainable severity aggregation for persisted hotspots."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import Hotspot, HotspotReport, Report
from app.schemas.reports import ReportSeverity
from app.schemas.severity import SeverityAggregationResponse


class SeverityPersistenceError(Exception):
    """Raised when severity source data cannot be read."""


class SeverityValidationError(Exception):
    """Raised when severity filters are invalid."""


class SeverityService:
    SEVERITY_VALUES = tuple(value.value for value in ReportSeverity)
    SEVERITY_SCORES = {
        ReportSeverity.LOW.value: 1,
        ReportSeverity.MEDIUM.value: 2,
        ReportSeverity.HIGH.value: 3,
        ReportSeverity.CRITICAL.value: 4,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze(
        self,
        hotspot_id: UUID,
        *,
        category: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> SeverityAggregationResponse:
        start, end = self.validate_range(from_, to)
        reports = self._load_reports(hotspot_id, category)
        filtered = [
            report
            for report in reports
            if (start is None or start <= self._to_utc(report.reported_at))
            and (end is None or self._to_utc(report.reported_at) <= end)
        ]
        counts = {severity: 0 for severity in self.SEVERITY_VALUES}
        valid_values: list[int] = []
        invalid_count = 0
        for report in filtered:
            severity = report.severity.strip().casefold() if report.severity else None
            score = self.SEVERITY_SCORES.get(severity)
            if score is None:
                invalid_count += 1
            else:
                counts[severity] += 1
                valid_values.append(score)

        valid_count = len(valid_values)
        percentages = {
            severity: (count / valid_count * 100 if valid_count else 0.0)
            for severity, count in counts.items()
        }
        weighted_average = sum(valid_values) / valid_count if valid_count else 0.0
        index = (
            (weighted_average - 1) / (max(self.SEVERITY_SCORES.values()) - 1) * 100
            if valid_count
            else 0.0
        )
        return SeverityAggregationResponse(
            hotspot_id=hotspot_id,
            total_reports=len(filtered),
            valid_severity_reports=valid_count,
            invalid_severity_reports=invalid_count,
            severity_counts=counts,
            severity_percentages=percentages,
            weighted_severity_average=weighted_average,
            severity_index_percent=index,
        )

    def _load_reports(self, hotspot_id: UUID, category: str | None) -> list[Report]:
        try:
            if self.session.get(Hotspot, hotspot_id) is None:
                raise LookupError("Hotspot not found")
            statement = (
                select(Report)
                .join(HotspotReport, HotspotReport.report_id == Report.id)
                .where(HotspotReport.hotspot_id == hotspot_id)
            )
            reports = list(self.session.scalars(statement))
            if category is None:
                return reports
            normalized = category.strip().casefold()
            return [
                report
                for report in reports
                if report.issue_category.strip().casefold() == normalized
            ]
        except LookupError:
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise SeverityPersistenceError("Could not retrieve severity reports") from exc

    @staticmethod
    def validate_range(
        from_: datetime | None, to: datetime | None
    ) -> tuple[datetime | None, datetime | None]:
        for name, value in (("from", from_), ("to", to)):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise SeverityValidationError(f"{name} must include a timezone offset")
        start = SeverityService._to_utc(from_) if from_ else None
        end = SeverityService._to_utc(to) if to else None
        if start is not None and end is not None and end < start:
            raise SeverityValidationError("to must be greater than or equal to from")
        return start, end

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
