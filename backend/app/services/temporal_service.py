"""Read-only, explainable temporal analysis of report timestamps."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from math import isfinite
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    TEMPORAL_AFTERNOON_START_HOUR,
    TEMPORAL_ANALYSIS_WINDOW_DAYS,
    TEMPORAL_EVENING_START_HOUR,
    TEMPORAL_MORNING_START_HOUR,
    TEMPORAL_NIGHT_START_HOUR,
)
from app.models.entities import Hotspot, HotspotReport, Report
from app.schemas.temporal import (
    AnalysisWindow,
    TemporalAnalysisResponse,
    TimeOfDayCounts,
)


class TemporalPersistenceError(Exception):
    """Raised when temporal source data cannot be read."""


class TemporalValidationError(Exception):
    """Raised when temporal analysis parameters are invalid."""


class TemporalService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze(
        self,
        *,
        hotspot_id: UUID | None = None,
        category: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        window_days: int | None = None,
    ) -> TemporalAnalysisResponse:
        days = window_days or TEMPORAL_ANALYSIS_WINDOW_DAYS
        if days < 1:
            raise TemporalValidationError("window_days must be at least 1")
        start, end, effective_days = self._analysis_window(from_, to, days)
        reports = self._load_reports(hotspot_id, category)
        current = [
            report for report in reports
            if start <= self._to_utc(report.reported_at) <= end
        ]
        previous_start = start - timedelta(days=effective_days)
        previous = [
            report for report in reports
            if previous_start <= self._to_utc(report.reported_at) < start
        ]
        return self._build_response(
            current=current,
            previous_count=len(previous),
            start=start,
            end=end,
            days=effective_days,
        )

    def _load_reports(
        self, hotspot_id: UUID | None, category: str | None
    ) -> list[Report]:
        try:
            if hotspot_id is not None:
                if self.session.get(Hotspot, hotspot_id) is None:
                    raise LookupError("Hotspot not found")
                statement = (
                    select(Report)
                    .join(HotspotReport, HotspotReport.report_id == Report.id)
                    .where(HotspotReport.hotspot_id == hotspot_id)
                )
            else:
                statement = select(Report)
            if category:
                statement = statement.where(Report.issue_category == category)
            return list(self.session.scalars(statement))
        except LookupError:
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TemporalPersistenceError("Could not retrieve temporal reports") from exc

    @staticmethod
    def _analysis_window(
        from_: datetime | None, to: datetime | None, days: int
    ) -> tuple[datetime, datetime, int]:
        if from_ is not None and from_.tzinfo is None:
            raise TemporalValidationError("from must include a timezone offset")
        if to is not None and to.tzinfo is None:
            raise TemporalValidationError("to must include a timezone offset")
        start = TemporalService._to_utc(from_) if from_ else None
        end = TemporalService._to_utc(to) if to else None
        if start is not None and end is not None:
            if end < start:
                raise TemporalValidationError("to must be greater than or equal to from")
            span_days = (end - start).total_seconds() / 86400
            if span_days == 0:
                return start, end, 1
            if span_days < 0:
                raise TemporalValidationError("to must be greater than or equal to from")
            return start, end, max(1, round(span_days))
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            start = end - timedelta(days=days)
        return start, end, days

    def _build_response(
        self,
        *,
        current: list[Report],
        previous_count: int,
        start: datetime,
        end: datetime,
        days: int,
    ) -> TemporalAnalysisResponse:
        hours = Counter({str(hour): 0 for hour in range(24)})
        weekdays = Counter({name: 0 for name in (
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        )})
        dates: Counter[str] = Counter()
        periods = Counter({"morning": 0, "afternoon": 0, "evening": 0, "night": 0})
        for report in current:
            timestamp = self._to_utc(report.reported_at)
            hours[str(timestamp.hour)] += 1
            weekdays[timestamp.strftime("%A")] += 1
            dates[timestamp.date().isoformat()] += 1
            periods[self._period(timestamp.hour)] += 1

        current_frequency = len(current) / days
        previous_frequency = previous_count / days
        change = self._percentage_change(current_frequency, previous_frequency)
        peak_hour = max(range(24), key=lambda hour: (hours[str(hour)], -hour)) if current else None
        peak_day = max(weekdays, key=lambda day: (weekdays[day], -list(weekdays).index(day))) if current else None
        return TemporalAnalysisResponse(
            analysis_window=AnalysisWindow.model_validate(
                {"from": start, "to": end, "days": days}
            ),
            total_reports=len(current),
            reports_by_hour=dict(hours),
            reports_by_day_of_week=dict(weekdays),
            reports_by_date=dict(sorted(dates.items())),
            peak_hour=peak_hour,
            peak_day_of_week=peak_day,
            time_of_day=TimeOfDayCounts(**periods),
            current_report_frequency=current_frequency,
            previous_report_frequency=previous_frequency,
            frequency_change_percent=change,
        )

    @staticmethod
    def _period(hour: int) -> str:
        if TEMPORAL_MORNING_START_HOUR <= hour < TEMPORAL_AFTERNOON_START_HOUR:
            return "morning"
        if TEMPORAL_AFTERNOON_START_HOUR <= hour < TEMPORAL_EVENING_START_HOUR:
            return "afternoon"
        if TEMPORAL_EVENING_START_HOUR <= hour < TEMPORAL_NIGHT_START_HOUR:
            return "evening"
        return "night"

    @staticmethod
    def _percentage_change(current: float, previous: float) -> float:
        if previous <= 0:
            return 0.0
        return (current - previous) / previous * 100

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
