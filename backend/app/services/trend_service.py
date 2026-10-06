"""Read-only, explainable reporting-activity trend analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import TREND_ANALYSIS_WINDOW_DAYS, TREND_PERIOD_DAYS
from app.models.entities import Hotspot, HotspotReport, Report
from app.schemas.trend import TrendPeriod, TrendResponse, TrendWindow


class TrendPersistenceError(Exception):
    """Raised when trend source data cannot be read."""


class TrendValidationError(Exception):
    """Raised when trend parameters are invalid."""


class TrendService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze(
        self,
        hotspot_id: UUID,
        *,
        category: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        period_days: int | None = None,
        analysis_window_days: int | None = None,
    ) -> TrendResponse:
        period = period_days or TREND_PERIOD_DAYS
        window_days = analysis_window_days or TREND_ANALYSIS_WINDOW_DAYS
        if period < 1:
            raise TrendValidationError("period_days must be at least 1")
        if window_days < 1:
            raise TrendValidationError("analysis_window_days must be at least 1")
        if period > window_days:
            raise TrendValidationError(
                "period_days must not exceed analysis_window_days"
            )

        start, end, actual_days = self._window(from_, to, window_days)
        reports = self._load_reports(hotspot_id, category)
        timestamps = [
            self._to_utc(report.reported_at)
            for report in reports
            if start <= self._to_utc(report.reported_at) <= end
        ]
        observed_periods = max(1, ceil(actual_days / period))
        counts = [0] * observed_periods
        period_delta = timedelta(days=period)
        for timestamp in timestamps:
            index = min(
                observed_periods - 1,
                int((timestamp - start).total_seconds() // period_delta.total_seconds()),
            )
            counts[index] += 1

        periods = [
            TrendPeriod(
                start=start + index * period_delta,
                end=min(end, start + (index + 1) * period_delta),
                report_count=count,
            )
            for index, count in enumerate(counts)
        ]
        midpoint = observed_periods // 2
        first = counts[:midpoint]
        second = counts[midpoint:]
        first_average = sum(first) / len(first) if first else 0.0
        second_average = sum(second) / len(second) if second else 0.0
        trend_change = self._change_percent(first_average, second_average)
        trend = self._classify(observed_periods, first_average, second_average)
        return TrendResponse(
            hotspot_id=hotspot_id,
            total_reports=len(timestamps),
            observed_periods=observed_periods,
            period_days=period,
            analysis_window_days=actual_days,
            analysis_window=TrendWindow.model_validate(
                {"from": start, "to": end, "days": actual_days}
            ),
            period_counts=periods,
            first_half_average=first_average,
            second_half_average=second_average,
            trend_change_percent=trend_change,
            trend=trend,
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
            raise TrendPersistenceError("Could not retrieve trend reports") from exc

    @staticmethod
    def _window(
        from_: datetime | None, to: datetime | None, default_days: int
    ) -> tuple[datetime, datetime, int]:
        for name, value in (("from", from_), ("to", to)):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise TrendValidationError(f"{name} must include a timezone offset")
        end = TrendService._to_utc(to) if to else datetime.now(timezone.utc)
        start = TrendService._to_utc(from_) if from_ else end - timedelta(days=default_days)
        if end < start:
            raise TrendValidationError("to must be greater than or equal to from")
        actual_days = max(1, ceil((end - start).total_seconds() / 86400))
        return start, end, actual_days

    @staticmethod
    def _change_percent(first: float, second: float) -> float:
        if first <= 0:
            return 0.0
        return (second - first) / first * 100

    @staticmethod
    def _classify(periods: int, first: float, second: float) -> str:
        if periods < 2 or first <= 0:
            return "insufficient_data"
        if second > first:
            return "increasing"
        if second < first:
            return "decreasing"
        return "stable"

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
