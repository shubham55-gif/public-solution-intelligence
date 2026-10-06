"""Read-only, explainable recurrence analysis for persisted hotspots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import RECURRENCE_ANALYSIS_WINDOW_DAYS, RECURRENCE_PERIOD_DAYS
from app.models.entities import Hotspot, HotspotReport, Report
from app.schemas.recurrence import (
    RecurrencePeriod,
    RecurrenceResponse,
    RecurrenceWindow,
)


class RecurrencePersistenceError(Exception):
    """Raised when recurrence source data cannot be read."""


class RecurrenceValidationError(Exception):
    """Raised when recurrence parameters are invalid."""


class RecurrenceService:
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
    ) -> RecurrenceResponse:
        period = period_days or RECURRENCE_PERIOD_DAYS
        window_days = analysis_window_days or RECURRENCE_ANALYSIS_WINDOW_DAYS
        if period < 1:
            raise RecurrenceValidationError("period_days must be at least 1")
        if window_days < 1:
            raise RecurrenceValidationError("analysis_window_days must be at least 1")
        if period > window_days:
            raise RecurrenceValidationError(
                "period_days must not exceed analysis_window_days"
            )

        start, end, actual_days = self._window(from_, to, window_days)
        reports = self._load_reports(hotspot_id, category)
        timestamps = [
            self._to_utc(report.reported_at)
            for report in reports
            if start <= self._to_utc(report.reported_at) <= end
        ]

        period_count = max(1, ceil(actual_days / period))
        buckets = [0] * period_count
        period_delta = timedelta(days=period)
        for timestamp in timestamps:
            index = min(
                period_count - 1,
                int((timestamp - start).total_seconds() // period_delta.total_seconds()),
            )
            buckets[index] += 1

        periods = []
        for index, count in enumerate(buckets):
            period_start = start + index * period_delta
            period_end = min(end, period_start + period_delta)
            periods.append(
                RecurrencePeriod(
                    period_start=period_start,
                    period_end=period_end,
                    report_count=count,
                    active=count > 0,
                )
            )
        active_flags = [count > 0 for count in buckets]
        active_periods = sum(active_flags)
        ratio = active_periods / period_count if period_count else 0.0
        return RecurrenceResponse(
            hotspot_id=hotspot_id,
            analysis_window=RecurrenceWindow.model_validate(
                {"from": start, "to": end, "days": actual_days}
            ),
            period_days=period,
            total_reports=len(timestamps),
            observed_periods=period_count,
            active_periods=active_periods,
            recurrence_ratio=ratio,
            longest_consecutive_periods=self._longest_streak(active_flags),
            current_period_active=active_flags[-1],
            recurrence_level=self._level(active_periods),
            periods=periods,
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
            raise RecurrencePersistenceError("Could not retrieve recurrence reports") from exc

    @staticmethod
    def _window(
        from_: datetime | None, to: datetime | None, default_days: int
    ) -> tuple[datetime, datetime, int]:
        if from_ is not None and (from_.tzinfo is None or from_.utcoffset() is None):
            raise RecurrenceValidationError("from must include a timezone offset")
        if to is not None and (to.tzinfo is None or to.utcoffset() is None):
            raise RecurrenceValidationError("to must include a timezone offset")
        end = RecurrenceService._to_utc(to) if to else datetime.now(timezone.utc)
        start = (
            RecurrenceService._to_utc(from_)
            if from_
            else end - timedelta(days=default_days)
        )
        if end < start:
            raise RecurrenceValidationError("to must be greater than or equal to from")
        actual_days = max(1, ceil((end - start).total_seconds() / 86400))
        return start, end, actual_days

    @staticmethod
    def _longest_streak(active_flags: list[bool]) -> int:
        longest = current = 0
        for active in active_flags:
            current = current + 1 if active else 0
            longest = max(longest, current)
        return longest

    @staticmethod
    def _level(active_periods: int) -> str:
        if active_periods == 0:
            return "none"
        if active_periods == 1:
            return "low"
        if active_periods == 2:
            return "moderate"
        return "high"

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
